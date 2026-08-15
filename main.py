"""
Gesture Snake — menu, levels, snake types, webcam + keyboard control.

Fixes vs the original:
- OpenCV UI no longer runs on a background thread
- Tail-cell collision no longer false-kills
- Fruit spawn cannot infinite-loop when the board is full
- Gestures are pointing-based; keyboard always works if the camera fails
"""

from __future__ import annotations

import json
import os
import sys
from typing import Optional

import cv2
import numpy as np
import pygame

from config import (
    BG,
    FPS,
    GOLD,
    HAND_WALL,
    HUD_BG,
    HUD_HEIGHT,
    MAX_HAND_WALLS,
    MUTED,
    PANEL,
    PANEL_EDGE,
    PLAY_HEIGHT,
    PLAY_WIDTH,
    PLAY_X,
    PLAY_Y,
    PROGRESS_FILE,
    RED,
    SIDEBAR_WIDTH,
    SIDEBAR_X,
    WHITE,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from gesture_controller import GestureController
from levels import LEVELS
from snake_game import SnakeGame
from snake_types import SNAKE_TYPES, SnakeType, get_snake_type


def load_progress() -> dict:
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return {
                "unlocked": int(data.get("unlocked", 1)),
                "best": int(data.get("best", 0)),
                "last_type": data.get("last_type", "classic"),
            }
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass
    return {"unlocked": 1, "best": 0, "last_type": "classic"}


def save_progress(progress: dict):
    try:
        with open(PROGRESS_FILE, "w", encoding="utf-8") as handle:
            json.dump(progress, handle)
    except OSError:
        pass


def cv2_to_surface(frame: np.ndarray) -> pygame.Surface:
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    surface = pygame.image.frombuffer(rgb.tobytes(), (rgb.shape[1], rgb.shape[0]), "RGB")
    return surface.convert()


def rounded_panel(surface, rect, fill=PANEL, border=PANEL_EDGE, radius=14):
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    pygame.draw.rect(surface, border, rect, 1, border_radius=radius)


class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Viper — Gesture Snake")
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.fonts = {
            "hero": pygame.font.SysFont("georgia", 54, bold=True),
            "title": pygame.font.SysFont("georgia", 36, bold=True),
            "body": pygame.font.SysFont("verdana", 20),
            "small": pygame.font.SysFont("verdana", 15),
            "tiny": pygame.font.SysFont("verdana", 13),
        }

        self.progress = load_progress()
        self.state = "menu"
        self.selected_type = get_snake_type(self.progress.get("last_type", "classic"))
        self.selected_level = 1
        self.type_index = next((i for i, t in enumerate(SNAKE_TYPES) if t.id == self.selected_type.id), 0)
        self.hover = None

        self.game: Optional[SnakeGame] = None
        self.controller = GestureController()
        self.cap = cv2.VideoCapture(0)
        self.camera_ok = bool(self.cap.isOpened())
        if self.camera_ok:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.camera_surface: Optional[pygame.Surface] = None
        self.has_hand = False
        self.last_tick = pygame.time.get_ticks()
        self.running = True
        self.toast = ""
        self.toast_until = 0

    def show_toast(self, text: str, ms: int = 1400):
        self.toast = text
        self.toast_until = pygame.time.get_ticks() + ms

    def quit(self):
        self.running = False
        self.controller.close()
        if self.cap is not None:
            self.cap.release()
        pygame.quit()

    def start_run(self, level_number: int):
        self.selected_level = level_number
        self.game = SnakeGame(self.selected_type, level_number)
        self.controller.reset()
        self.state = "play"
        self.last_tick = pygame.time.get_ticks()
        self.progress["last_type"] = self.selected_type.id
        save_progress(self.progress)

    def poll_camera(self) -> dict:
        result = {
            "direction": None,
            "pinch": False,
            "drop_wall": False,
            "grid_cell": None,
            "has_hand": False,
        }
        if not self.camera_ok:
            return result
        ok, frame = self.cap.read()
        if not ok:
            return result
        frame = cv2.flip(frame, 1)
        detected = self.controller.detect(frame)
        self.camera_surface = cv2_to_surface(detected["annotated"])
        self.has_hand = detected["has_hand"]
        return detected

    def handle_menu_click(self, pos, buttons):
        for name, rect in buttons.items():
            if rect.collidepoint(pos):
                return name
        return None

    def run(self):
        while self.running:
            self.clock.tick(FPS)
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.quit()
                    return
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    if self.state == "play":
                        if self.game and not self.game.game_over and not self.game.won_level:
                            self.state = "paused"
                        else:
                            self.state = "menu"
                    elif self.state == "paused":
                        self.state = "play"
                        self.last_tick = pygame.time.get_ticks()
                    elif self.state == "menu":
                        self.quit()
                        return
                    else:
                        self.state = "menu"

            if self.state == "menu":
                self.draw_menu(events)
            elif self.state == "howto":
                self.draw_howto(events)
            elif self.state == "types":
                self.draw_types(events)
            elif self.state == "levels":
                self.draw_levels(events)
            elif self.state == "paused":
                self.draw_paused(events)
            else:
                self.tick_play(events)

            pygame.display.flip()

        self.quit()

    def _bg(self):
        self.screen.fill(BG)
        pygame.draw.rect(self.screen, HUD_BG, (0, 0, WINDOW_WIDTH, HUD_HEIGHT))
        pygame.draw.line(self.screen, PANEL_EDGE, (0, HUD_HEIGHT), (WINDOW_WIDTH, HUD_HEIGHT))

    def _header(self, title: str, subtitle: str = ""):
        self.screen.blit(self.fonts["title"].render(title, True, WHITE), (24, 16))
        if subtitle:
            self.screen.blit(self.fonts["small"].render(subtitle, True, MUTED), (24, 48))
        best = self.fonts["small"].render(f"best  {self.progress['best']}", True, GOLD)
        self.screen.blit(best, (WINDOW_WIDTH - 160, 28))

    def _button(self, rect, label, accent=GOLD):
        hover = rect.collidepoint(pygame.mouse.get_pos())
        fill = (28, 42, 62) if hover else PANEL
        rounded_panel(self.screen, rect, fill, accent if hover else PANEL_EDGE)
        text = self.fonts["body"].render(label, True, WHITE)
        self.screen.blit(text, text.get_rect(center=rect.center))

    def draw_menu(self, events):
        self._bg()
        self._header("VIPER", "Hand-guided snake  ·  maze walls  ·  five breeds")
        hero = self.fonts["hero"].render("Play with your hand.", True, WHITE)
        self.screen.blit(hero, (60, 140))
        blurb = self.fonts["body"].render(
            "Point to steer. Pinch to boost. Peace sign drops a hand-wall. Arrows always work.",
            True,
            MUTED,
        )
        self.screen.blit(blurb, (60, 210))

        play = pygame.Rect(60, 300, 280, 56)
        types = pygame.Rect(60, 372, 280, 56)
        howto = pygame.Rect(60, 444, 280, 56)
        quit_b = pygame.Rect(60, 516, 280, 56)
        self._button(play, "Play")
        self._button(types, "Snake types")
        self._button(howto, "How to play")
        self._button(quit_b, "Quit", RED)

        preview = pygame.Rect(420, 280, 720, 300)
        rounded_panel(self.screen, preview)
        lines = [
            f"Selected  {self.selected_type.name}  —  {self.selected_type.tagline}",
            self.selected_type.description,
            f"Campaign  level {min(self.progress['unlocked'], len(LEVELS))} of {len(LEVELS)} unlocked",
            "Camera  " + ("live" if self.camera_ok else "not found — keyboard mode"),
        ]
        for i, line in enumerate(lines):
            self.screen.blit(self.fonts["body"].render(line, True, WHITE if i == 0 else MUTED), (448, 310 + i * 42))

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if play.collidepoint(event.pos):
                    self.state = "levels"
                elif types.collidepoint(event.pos):
                    self.state = "types"
                elif howto.collidepoint(event.pos):
                    self.state = "howto"
                elif quit_b.collidepoint(event.pos):
                    self.running = False
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.state = "levels"

    def draw_howto(self, events):
        self._bg()
        self._header("How to play", "Esc returns to the menu")
        cards = [
            ("Point", "Aim index finger up, down, left, or right. The snake follows that heading."),
            ("Pinch", "Thumb + index together is a speed boost. Titan uses this to smash maze walls."),
            ("Peace", "Index + middle up drops a hand-wall on the cell under your palm (max 6)."),
            ("Keyboard", "Arrows / WASD to steer, Shift boost, F drop a wall at the snake head's next cell."),
            ("Levels", "Eat the fruit quota to clear. Inner maze walls kill unless your type can break them."),
            ("Edges", "Classic / Ember / Titan / Specter die on the rim. Shadow wraps around."),
        ]
        for i, (title, body) in enumerate(cards):
            col, row = i % 2, i // 2
            rect = pygame.Rect(40 + col * 570, 110 + row * 180, 540, 160)
            rounded_panel(self.screen, rect)
            self.screen.blit(self.fonts["title"].render(title, True, GOLD), (rect.x + 24, rect.y + 22))
            self._blit_wrap(body, self.fonts["body"], MUTED, pygame.Rect(rect.x + 24, rect.y + 72, 490, 70))
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                self.state = "menu"

    def _blit_wrap(self, text, font, color, rect):
        words = text.split()
        lines, current = [], ""
        for word in words:
            trial = (current + " " + word).strip()
            if font.size(trial)[0] <= rect.width:
                current = trial
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        y = rect.y
        for line in lines[:4]:
            self.screen.blit(font.render(line, True, color), (rect.x, y))
            y += font.get_height() + 4

    def draw_types(self, events):
        self._bg()
        self._header("Snake types", "Click a card, then Continue")
        cards = []
        for i, st in enumerate(SNAKE_TYPES):
            rect = pygame.Rect(28 + i * 232, 120, 220, 430)
            cards.append((st, rect))
            selected = i == self.type_index
            rounded_panel(self.screen, rect, (24, 36, 54) if selected else PANEL, st.accent if selected else PANEL_EDGE)
            swatch = pygame.Rect(rect.x + 24, rect.y + 24, rect.width - 48, 72)
            pygame.draw.rect(self.screen, st.body, swatch, border_radius=10)
            pygame.draw.rect(self.screen, st.head, (swatch.x + 12, swatch.y + 18, 48, 36), border_radius=8)
            self.screen.blit(self.fonts["title"].render(st.name, True, WHITE), (rect.x + 16, rect.y + 112))
            self.screen.blit(self.fonts["small"].render(st.tagline, True, st.accent), (rect.x + 16, rect.y + 156))
            self._blit_wrap(st.description, self.fonts["small"], MUTED, pygame.Rect(rect.x + 16, rect.y + 190, 188, 140))
            stats = f"spd {st.base_speed:.0f}/{st.boost_speed:.0f}   x{st.score_mult}"
            self.screen.blit(self.fonts["tiny"].render(stats, True, GOLD), (rect.x + 16, rect.y + 390))

        cont = pygame.Rect(WINDOW_WIDTH - 280, WINDOW_HEIGHT - 78, 240, 50)
        self._button(cont, "Continue")

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, (st, rect) in enumerate(cards):
                    if rect.collidepoint(event.pos):
                        self.type_index = i
                        self.selected_type = st
                if cont.collidepoint(event.pos):
                    self.selected_type = SNAKE_TYPES[self.type_index]
                    self.state = "levels"
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.type_index = (self.type_index + 1) % len(SNAKE_TYPES)
                    self.selected_type = SNAKE_TYPES[self.type_index]
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    self.type_index = (self.type_index - 1) % len(SNAKE_TYPES)
                    self.selected_type = SNAKE_TYPES[self.type_index]
                elif event.key == pygame.K_RETURN:
                    self.selected_type = SNAKE_TYPES[self.type_index]
                    self.state = "levels"

    def draw_levels(self, events):
        self._bg()
        self._header("Campaign", f"Playing as {self.selected_type.name}")
        buttons = []
        for i, level in enumerate(LEVELS):
            col, row = i % 4, i // 4
            rect = pygame.Rect(40 + col * 290, 130 + row * 240, 270, 210)
            unlocked = level.number <= self.progress["unlocked"]
            buttons.append((level, rect, unlocked))
            edge = self.selected_type.accent if unlocked else (50, 60, 72)
            rounded_panel(self.screen, rect, PANEL if unlocked else (12, 16, 22), edge)
            title_color = WHITE if unlocked else MUTED
            self.screen.blit(self.fonts["title"].render(f"{level.number}  {level.name}", True, title_color), (rect.x + 18, rect.y + 22))
            self._blit_wrap(level.blurb if unlocked else "Clear the previous level to unlock.", self.fonts["small"], MUTED, pygame.Rect(rect.x + 18, rect.y + 80, 234, 70))
            meta = f"{level.fruit_goal} fruit   +{level.speed_bonus:.1f} speed"
            self.screen.blit(self.fonts["tiny"].render(meta, True, GOLD if unlocked else MUTED), (rect.x + 18, rect.y + 170))

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for level, rect, unlocked in buttons:
                    if rect.collidepoint(event.pos) and unlocked:
                        self.start_run(level.number)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                self.start_run(min(self.progress["unlocked"], len(LEVELS)))

    def draw_paused(self, events):
        if self.game:
            self._draw_playfield_frame()
        dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 150))
        self.screen.blit(dim, (0, 0))
        label = self.fonts["hero"].render("Paused", True, WHITE)
        hint = self.fonts["body"].render("Esc resume    M menu", True, MUTED)
        self.screen.blit(label, label.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 20)))
        self.screen.blit(hint, hint.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 40)))
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                self.state = "menu"
                self.game = None

    def tick_play(self, events):
        assert self.game is not None
        gesture = self.poll_camera()
        keys = pygame.key.get_pressed()

        key_dir = None
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            key_dir = "UP"
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            key_dir = "DOWN"
        elif keys[pygame.K_LEFT] or keys[pygame.K_a]:
            key_dir = "LEFT"
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            key_dir = "RIGHT"

        if not self.game.game_over and not self.game.won_level:
            self.game.change_direction(key_dir or gesture.get("direction"))
            boosting = bool(gesture.get("pinch") or keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])
            self.game.set_speed_boost(boosting)
            self.game.set_ghost_cell(gesture.get("grid_cell"))

            if gesture.get("drop_wall"):
                if self.game.try_drop_hand_wall(gesture.get("grid_cell")):
                    self.show_toast("Hand-wall placed")
                else:
                    self.show_toast("Can't place wall")

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_f and not self.game.game_over:
                    hx, hy = self.game.snake[0]
                    dx, dy = self.game.direction.value
                    cell = (hx + dx, hy + dy)
                    if self.game.snake_type.wrap_edges:
                        cell = self.game._wrap(*cell)
                    if self.game.try_drop_hand_wall(cell):
                        self.show_toast("Hand-wall placed")
                if event.key == pygame.K_r:
                    self.game.score = 0
                    self.game.fruits_eaten = 0
                    self.game.reset_round()
                    self.last_tick = pygame.time.get_ticks()
                if event.key == pygame.K_RETURN:
                    if self.game.won_level:
                        self._advance_or_finish()
                    elif self.game.game_over:
                        self.game.reset_round()
                        self.game.score = 0
                        self.game.fruits_eaten = 0
                        self.last_tick = pygame.time.get_ticks()

        now = pygame.time.get_ticks()
        interval = 1000.0 / max(3.0, self.game.current_speed())
        if now - self.last_tick >= interval and not self.game.game_over and not self.game.won_level:
            self.game.update()
            self.last_tick = now
            if self.game.score > self.progress["best"]:
                self.progress["best"] = self.game.score
                save_progress(self.progress)
            if self.game.won_level:
                nxt = self.game.level.number + 1
                if nxt > self.progress["unlocked"]:
                    self.progress["unlocked"] = min(nxt, len(LEVELS) + 1)
                    save_progress(self.progress)

        self._draw_playfield_frame()

    def _advance_or_finish(self):
        assert self.game is not None
        nxt = self.game.level.number + 1
        if nxt <= len(LEVELS):
            self.start_run(nxt)
        else:
            self.show_toast("Campaign complete")
            self.state = "menu"
            self.game = None

    def _draw_playfield_frame(self):
        assert self.game is not None
        self._bg()
        g = self.game
        title = f"Lv {g.level.number}  {g.level.name}"
        self._header(title, f"{g.snake_type.name}  ·  {g.level.blurb}")
        g.draw_board(self.screen)
        g.overlay_status(self.screen, self.fonts)
        self._draw_sidebar(g)
        if pygame.time.get_ticks() < self.toast_until and self.toast:
            chip = self.fonts["small"].render(self.toast, True, BG)
            rect = pygame.Rect(0, 0, chip.get_width() + 28, 34)
            rect.center = (PLAY_X + PLAY_WIDTH // 2, PLAY_Y + 24)
            pygame.draw.rect(self.screen, GOLD, rect, border_radius=16)
            self.screen.blit(chip, chip.get_rect(center=rect.center))

    def _draw_sidebar(self, game: SnakeGame):
        panel = pygame.Rect(SIDEBAR_X, PLAY_Y, SIDEBAR_WIDTH, PLAY_HEIGHT)
        rounded_panel(self.screen, panel)

        y = panel.y + 18
        stats = [
            ("score", str(game.score)),
            ("fruit", f"{game.fruits_eaten}/{game.level.fruit_goal}"),
            ("hand-walls", f"{len(game.hand_walls)}/{MAX_HAND_WALLS}"),
            ("speed", f"{game.current_speed():.1f}"),
        ]
        for label, value in stats:
            self.screen.blit(self.fonts["tiny"].render(label.upper(), True, MUTED), (panel.x + 20, y))
            self.screen.blit(self.fonts["title"].render(value, True, WHITE), (panel.x + 20, y + 16))
            y += 70

        cam_h = 168
        cam_rect = pygame.Rect(panel.x + 16, panel.bottom - cam_h - 58, panel.width - 32, cam_h)
        rounded_panel(self.screen, cam_rect, (6, 8, 12), PANEL_EDGE, 10)
        if self.camera_surface is not None:
            fitted = pygame.transform.smoothscale(self.camera_surface, (cam_rect.width - 8, cam_rect.height - 8))
            self.screen.blit(fitted, (cam_rect.x + 4, cam_rect.y + 4))
        else:
            msg = self.fonts["small"].render("No camera — use keyboard", True, MUTED)
            self.screen.blit(msg, msg.get_rect(center=cam_rect.center))

        hand = "HAND LOCKED" if self.has_hand else "SHOW YOUR HAND"
        color = HAND_WALL if self.has_hand else MUTED
        self.screen.blit(self.fonts["small"].render(hand, True, color), (panel.x + 20, panel.bottom - 42))
        self.screen.blit(self.fonts["tiny"].render("Shift boost  F wall  Esc pause", True, MUTED), (panel.x + 20, panel.bottom - 22))


def main():
    try:
        App().run()
    except KeyboardInterrupt:
        print("\nClosed.")
    except Exception as exc:
        print(f"An error occurred: {exc}")
        import traceback

        traceback.print_exc()
        pygame.quit()
        sys.exit(1)


if __name__ == "__main__":
    main()
