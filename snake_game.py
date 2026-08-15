"""Nokia-inspired snake engine with levels, types, maze walls, and hand-walls."""

from __future__ import annotations

import math
import random
from enum import Enum
from typing import List, Optional, Set, Tuple

import pygame

from config import (
    APPLE,
    APPLE_LEAF,
    CELL_SIZE,
    DANGER,
    GOLD,
    GRID_COLS,
    GRID_LINE,
    GRID_ROWS,
    HAND_WALL,
    HAND_WALL_GLOW,
    MAX_HAND_WALLS,
    MUTED,
    PANEL,
    PLAY_HEIGHT,
    PLAY_WIDTH,
    PLAY_X,
    PLAY_Y,
    RED,
    WALL,
    WALL_EDGE,
    WHITE,
)
from levels import Level, empty_cells, get_level
from snake_types import SnakeType


class Direction(Enum):
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)


OPPOSITE = {
    Direction.UP: Direction.DOWN,
    Direction.DOWN: Direction.UP,
    Direction.LEFT: Direction.RIGHT,
    Direction.RIGHT: Direction.LEFT,
}

DIR_FROM_NAME = {
    "UP": Direction.UP,
    "DOWN": Direction.DOWN,
    "LEFT": Direction.LEFT,
    "RIGHT": Direction.RIGHT,
}


class SnakeGame:
    def __init__(self, snake_type: SnakeType, level_number: int = 1):
        self.snake_type = snake_type
        self.level: Level = get_level(level_number)
        self.maze_walls: Set[Tuple[int, int]] = set(self.level.walls)
        self.hand_walls: Set[Tuple[int, int]] = set()
        self.ghost_cell: Optional[Tuple[int, int]] = None
        self.snake: List[Tuple[int, int]] = []
        self.direction = Direction.RIGHT
        self.next_direction = Direction.RIGHT
        self.fruit: Tuple[int, int] = (0, 0)
        self.score = 0
        self.fruits_eaten = 0
        self.game_over = False
        self.won_level = False
        self.speed_boost = False
        self.particles: List[dict] = []
        self.break_cooldown = 0
        self.reset_round()

    def reset_round(self):
        cx, cy = GRID_COLS // 2, GRID_ROWS // 2
        length = max(2, self.snake_type.start_length)
        self.snake = [(cx - i, cy) for i in range(length)]
        self.direction = Direction.RIGHT
        self.next_direction = Direction.RIGHT
        self.game_over = False
        self.won_level = False
        self.speed_boost = False
        self.particles = []
        self.break_cooldown = 0
        self.hand_walls.clear()
        self.ghost_cell = None
        self.spawn_fruit()

    def occupied(self) -> Set[Tuple[int, int]]:
        return set(self.snake) | self.maze_walls | self.hand_walls

    def spawn_fruit(self) -> bool:
        cells = empty_cells(self.maze_walls | self.hand_walls, set(self.snake))
        if not cells:
            return False
        self.fruit = random.choice(cells)
        return True

    def change_direction(self, name: Optional[str]):
        if self.game_over or self.won_level or not name:
            return
        new_dir = DIR_FROM_NAME.get(name)
        if new_dir and new_dir != OPPOSITE.get(self.direction):
            self.next_direction = new_dir

    def set_speed_boost(self, boost: bool):
        self.speed_boost = bool(boost)

    def set_ghost_cell(self, cell: Optional[Tuple[int, int]]):
        self.ghost_cell = cell

    def try_drop_hand_wall(self, cell: Optional[Tuple[int, int]]) -> bool:
        if self.game_over or self.won_level or cell is None:
            return False
        x, y = cell
        if x < 0 or y < 0 or x >= GRID_COLS or y >= GRID_ROWS:
            return False
        if len(self.hand_walls) >= MAX_HAND_WALLS:
            return False
        if cell in self.occupied() or cell == self.fruit:
            return False
        self.hand_walls.add(cell)
        return True

    def current_speed(self) -> float:
        base = self.snake_type.base_speed + self.level.speed_bonus
        boost = self.snake_type.boost_speed + self.level.speed_bonus
        return boost if self.speed_boost else base

    def _wrap(self, x: int, y: int) -> Tuple[int, int]:
        return x % GRID_COLS, y % GRID_ROWS

    def _out_of_bounds(self, x: int, y: int) -> bool:
        return x < 0 or y < 0 or x >= GRID_COLS or y >= GRID_ROWS

    def update(self):
        if self.game_over or self.won_level:
            return
        if self.break_cooldown > 0:
            self.break_cooldown -= 1

        self.direction = self.next_direction
        hx, hy = self.snake[0]
        dx, dy = self.direction.value
        nx, ny = hx + dx, hy + dy

        if self.snake_type.wrap_edges:
            nx, ny = self._wrap(nx, ny)
        elif self._out_of_bounds(nx, ny):
            self.game_over = True
            return

        new_head = (nx, ny)

        if new_head in self.maze_walls:
            if self.snake_type.wall_breaker and self.speed_boost and self.break_cooldown == 0:
                self.maze_walls.discard(new_head)
                self.break_cooldown = 18
                self._burst(new_head, WALL_EDGE)
            else:
                self.game_over = True
                return

        if new_head in self.hand_walls:
            self.hand_walls.discard(new_head)
            self._burst(new_head, HAND_WALL_GLOW)

        eating = new_head == self.fruit
        body = self.snake if eating else self.snake[:-1]
        if not self.snake_type.pass_self and new_head in body:
            self.game_over = True
            return

        self.snake.insert(0, new_head)
        if eating:
            gained = int(10 * self.snake_type.score_mult * (1 + self.level.number * 0.08))
            self.score += gained
            self.fruits_eaten += 1
            self._burst(new_head, APPLE)
            if self.fruits_eaten >= self.level.fruit_goal:
                self.won_level = True
            elif not self.spawn_fruit():
                self.won_level = True
        else:
            self.snake.pop()

        self._update_particles()

    def _burst(self, cell: Tuple[int, int], color: Tuple[int, int, int]):
        px = cell[0] * CELL_SIZE + CELL_SIZE // 2
        py = cell[1] * CELL_SIZE + CELL_SIZE // 2
        for _ in range(10):
            self.particles.append(
                {
                    "x": px,
                    "y": py,
                    "vx": random.uniform(-3.2, 3.2),
                    "vy": random.uniform(-3.2, 3.2),
                    "life": 22,
                    "max": 22,
                    "color": color,
                }
            )

    def _update_particles(self):
        alive = []
        for particle in self.particles:
            particle["x"] += particle["vx"]
            particle["y"] += particle["vy"]
            particle["life"] -= 1
            if particle["life"] > 0:
                alive.append(particle)
        self.particles = alive

    def draw_board(self, surface: pygame.Surface):
        board = pygame.Surface((PLAY_WIDTH, PLAY_HEIGHT))
        board.fill((6, 10, 16))

        for x in range(GRID_COLS + 1):
            pygame.draw.line(board, GRID_LINE, (x * CELL_SIZE, 0), (x * CELL_SIZE, PLAY_HEIGHT))
        for y in range(GRID_ROWS + 1):
            pygame.draw.line(board, GRID_LINE, (0, y * CELL_SIZE), (PLAY_WIDTH, y * CELL_SIZE))

        pygame.draw.rect(board, (36, 54, 78), board.get_rect(), 2)

        for x, y in self.maze_walls:
            self._draw_block(board, x, y, WALL, WALL_EDGE)

        for x, y in self.hand_walls:
            self._draw_block(board, x, y, HAND_WALL, HAND_WALL_GLOW)

        if self.ghost_cell and self.ghost_cell not in self.occupied() and self.ghost_cell != self.fruit:
            gx, gy = self.ghost_cell
            rect = pygame.Rect(gx * CELL_SIZE + 3, gy * CELL_SIZE + 3, CELL_SIZE - 6, CELL_SIZE - 6)
            pygame.draw.rect(board, HAND_WALL_GLOW, rect, 2, border_radius=4)

        if not self.game_over:
            self._draw_fruit(board)
            for i, segment in enumerate(self.snake):
                self._draw_segment(board, segment[0], segment[1], i == 0)
            self._draw_particles(board)

        surface.blit(board, (PLAY_X, PLAY_Y))

    def _draw_block(self, surface: pygame.Surface, x: int, y: int, fill, edge):
        rect = pygame.Rect(x * CELL_SIZE + 1, y * CELL_SIZE + 1, CELL_SIZE - 2, CELL_SIZE - 2)
        pygame.draw.rect(surface, fill, rect, border_radius=4)
        pygame.draw.rect(surface, edge, rect, 1, border_radius=4)

    def _draw_segment(self, surface: pygame.Surface, x: int, y: int, is_head: bool):
        st = self.snake_type
        rect = pygame.Rect(x * CELL_SIZE + 2, y * CELL_SIZE + 2, CELL_SIZE - 4, CELL_SIZE - 4)
        color = st.head if is_head else st.body
        pygame.draw.rect(surface, color, rect, border_radius=7)
        pygame.draw.rect(surface, st.dark, rect, 1, border_radius=7)
        if is_head:
            self._draw_eyes(surface, x, y)

    def _draw_eyes(self, surface: pygame.Surface, x: int, y: int):
        px, py = x * CELL_SIZE, y * CELL_SIZE
        if self.direction == Direction.RIGHT:
            eyes = [(px + 14, py + 7), (px + 14, py + 15)]
        elif self.direction == Direction.LEFT:
            eyes = [(px + 7, py + 7), (px + 7, py + 15)]
        elif self.direction == Direction.UP:
            eyes = [(px + 7, py + 7), (px + 15, py + 7)]
        else:
            eyes = [(px + 7, py + 14), (px + 15, py + 14)]
        for ex, ey in eyes:
            pygame.draw.circle(surface, (12, 14, 18), (ex, ey), 3)
            pygame.draw.circle(surface, WHITE, (ex + 1, ey - 1), 1)

    def _draw_fruit(self, surface: pygame.Surface):
        x, y = self.fruit
        cx = x * CELL_SIZE + CELL_SIZE // 2
        cy = y * CELL_SIZE + CELL_SIZE // 2 + 1
        pulse = 1.0 + 0.12 * math.sin(pygame.time.get_ticks() / 180)
        radius = int((CELL_SIZE // 2 - 4) * pulse)
        pygame.draw.circle(surface, APPLE, (cx, cy), radius)
        pygame.draw.circle(surface, WHITE, (cx - 3, cy - 3), 2)
        pygame.draw.ellipse(surface, APPLE_LEAF, (cx + 1, cy - radius - 2, 8, 5))

    def _draw_particles(self, surface: pygame.Surface):
        for particle in self.particles:
            t = particle["life"] / particle["max"]
            size = max(1, int(4 * t))
            color = particle["color"]
            pygame.draw.circle(surface, color, (int(particle["x"]), int(particle["y"])), size)

    def overlay_status(self, surface: pygame.Surface, fonts: dict):
        if not (self.game_over or self.won_level):
            return
        overlay = pygame.Surface((PLAY_WIDTH, PLAY_HEIGHT), pygame.SRCALPHA)
        overlay.fill((6, 8, 14, 170))
        surface.blit(overlay, (PLAY_X, PLAY_Y))
        title = "LEVEL CLEAR" if self.won_level else "GAME OVER"
        color = GOLD if self.won_level else DANGER
        text = fonts["title"].render(title, True, color)
        sub = fonts["body"].render(f"Score {self.score}   fruit {self.fruits_eaten}/{self.level.fruit_goal}", True, WHITE)
        hint = fonts["small"].render("Enter  continue    R  retry    Esc  menu", True, MUTED)
        cx = PLAY_X + PLAY_WIDTH // 2
        cy = PLAY_Y + PLAY_HEIGHT // 2
        surface.blit(text, text.get_rect(center=(cx, cy - 28)))
        surface.blit(sub, sub.get_rect(center=(cx, cy + 10)))
        surface.blit(hint, hint.get_rect(center=(cx, cy + 44)))
