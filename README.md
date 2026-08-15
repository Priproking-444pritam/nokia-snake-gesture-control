# Viper — Gesture Snake

Hand-controlled snake with campaign levels, five snake types, maze walls, and placeable **hand-walls**.

## Run

```bash
python setup.py
python main.py
```

Or:

```bash
pip install -r requirements.txt
python main.py
```

Needs Python 3.9+, a webcam (optional — keyboard still works), and the packages in `requirements.txt`.

## Website (play in the browser)

The playable site lives in `docs/` (static HTML/CSS/JS + MediaPipe Hands). No build step.

### 1. Run it on your machine

From the repo root:

```bash
python -m http.server 8000 --directory docs
```

Open [http://localhost:8000](http://localhost:8000). Allow the camera when the browser asks. You can also use arrows if you deny the camera.

Do not open `docs/index.html` as a `file://` URL — the camera and MediaPipe modules need a local server (or HTTPS).

### 2. Put it on the internet with GitHub Pages (free)

1. Push this repo to GitHub.
2. Repo **Settings → Pages**.
3. **Source:** Deploy from a branch.
4. **Branch:** `main` (or this PR branch), folder **`/docs`**.
5. Save. After a minute the game is at:

`https://<your-username>.github.io/<repo-name>/`

The site must be **HTTPS** (GitHub Pages already is) so `getUserMedia` can use the webcam.

### 3. What the site is made of

| File | Role |
|---|---|
| `docs/index.html` | Page shell and camera `<video>` |
| `docs/styles.css` | Layout, cards, HUD |
| `docs/app.js` | Menus, 8 levels, 5 snake types, canvas game, MediaPipe gestures |

Hands run in the browser via `@mediapipe/tasks-vision` (CDN). Progress is stored in `localStorage` (`viper-progress`). Same rules as the Python game: point to steer, pinch to boost, peace sign drops a hand-wall.

## Play

### Hand
| Gesture | Action |
|---|---|
| Point index finger | Steer (up / down / left / right) |
| Pinch thumb + index | Speed boost |
| Peace sign (index + middle) | Drop a hand-wall on the cell under your palm |

### Keyboard
Arrows or WASD to steer, Shift to boost, **F** to drop a wall in front of the head, **Esc** pause / back, **Enter** confirm, **R** retry.

## Snake types

| Type | Trait |
|---|---|
| **Classic** | Balanced. Walls and self kill. |
| **Shadow** | Wraps around the outer edge. Inner maze still kills. |
| **Ember** | Faster, higher score, no safety net. |
| **Titan** | Slow. Pinch-boost into a maze block to smash it. |
| **Specter** | Passes through its own body. Walls still kill. |

## Levels

Eight maps: open field → pillars → crossroads → courtyards → corridors → arena → labyrinth → gauntlet. Eat the fruit quota to unlock the next. Progress is stored in `progress.json`.

Hand-walls are extra blocks you drop (max 6). The snake can smash those by running into them. Maze walls kill unless you are Titan on boost.

## Layout

```
config.py               window, grid, colors
snake_types.py          the five breeds
levels.py               maze layouts
gesture_controller.py   MediaPipe pointing / pinch / peace
snake_game.py           movement, collisions, drawing
main.py                 menus + camera + game loop
tests/test_game_logic.py
docs/                    browser game (GitHub Pages)
```

The camera is read on the **same thread** as Pygame so OpenCV windows are not opened from a worker thread.

## Tests

```bash
python -m unittest tests.test_game_logic -v
```
