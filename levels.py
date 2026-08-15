"""Level definitions: maze walls, speed scaling, fruit goals."""

from typing import List, Set, Tuple

from config import GRID_COLS, GRID_ROWS, LEVEL_FRUIT_GOAL

Cell = Tuple[int, int]


def _rect(x0: int, y0: int, x1: int, y1: int) -> Set[Cell]:
    cells: Set[Cell] = set()
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            cells.add((x, y))
    return cells


def _hline(y: int, x0: int, x1: int) -> Set[Cell]:
    return {(x, y) for x in range(x0, x1 + 1)}


def _vline(x: int, y0: int, y1: int) -> Set[Cell]:
    return {(x, y) for y in range(y0, y1 + 1)}


def _safe_spawn_clear(walls: Set[Cell]) -> Set[Cell]:
    """Keep the center-left start corridor open for the snake."""
    cx, cy = GRID_COLS // 2, GRID_ROWS // 2
    keep_open = {(cx - i, cy) for i in range(0, 6)}
    keep_open |= {(cx + i, cy) for i in range(1, 3)}
    return walls - keep_open


class Level:
    def __init__(self, number: int, name: str, blurb: str, walls: Set[Cell], speed_bonus: float, fruit_goal: int):
        self.number = number
        self.name = name
        self.blurb = blurb
        self.walls = walls
        self.speed_bonus = speed_bonus
        self.fruit_goal = fruit_goal


def _level_open() -> Set[Cell]:
    return set()


def _level_pillars() -> Set[Cell]:
    walls: Set[Cell] = set()
    for x in (8, 23):
        for y in (6, 17):
            walls |= _rect(x, y, x + 1, y + 1)
    return _safe_spawn_clear(walls)


def _level_cross() -> Set[Cell]:
    walls = _hline(GRID_ROWS // 2, 4, 12) | _hline(GRID_ROWS // 2, 19, 27)
    walls |= _vline(GRID_COLS // 2, 3, 8) | _vline(GRID_COLS // 2, 15, 20)
    return _safe_spawn_clear(walls)


def _level_boxes() -> Set[Cell]:
    walls = _rect(3, 3, 10, 8) - _rect(4, 4, 9, 7)
    walls |= _rect(21, 3, 28, 8) - _rect(22, 4, 27, 7)
    walls |= _rect(3, 15, 10, 20) - _rect(4, 16, 9, 19)
    walls |= _rect(21, 15, 28, 20) - _rect(22, 16, 27, 19)
    return _safe_spawn_clear(walls)


def _level_corridors() -> Set[Cell]:
    walls: Set[Cell] = set()
    for i, y in enumerate((4, 9, 14, 19)):
        if i % 2 == 0:
            walls |= _hline(y, 2, 24)
        else:
            walls |= _hline(y, 7, 29)
    return _safe_spawn_clear(walls)


def _level_arena() -> Set[Cell]:
    walls = _rect(6, 4, 25, 19) - _rect(7, 5, 24, 18)
    walls |= _vline(GRID_COLS // 2, 4, 9)
    walls |= _vline(GRID_COLS // 2, 14, 19)
    return _safe_spawn_clear(walls)


def _level_labyrinth() -> Set[Cell]:
    walls: Set[Cell] = set()
    walls |= _hline(3, 2, 14) | _hline(3, 18, 29)
    walls |= _vline(14, 3, 10) | _vline(18, 3, 10)
    walls |= _hline(10, 2, 8) | _hline(10, 23, 29)
    walls |= _vline(8, 10, 16) | _vline(23, 10, 16)
    walls |= _hline(16, 8, 23)
    walls |= _vline(4, 16, 21) | _vline(27, 16, 21)
    walls |= _hline(21, 4, 12) | _hline(21, 19, 27)
    return _safe_spawn_clear(walls)


def _level_gauntlet() -> Set[Cell]:
    walls: Set[Cell] = set()
    for x in range(3, 29, 4):
        gap = 5 + (x // 4) % 4
        walls |= _vline(x, 2, GRID_ROWS - 3) - {(x, gap), (x, gap + 1), (x, gap + 2)}
    return _safe_spawn_clear(walls)


LEVELS: List[Level] = [
    Level(1, "Open Field", "Learn the gestures. No inner walls.", _level_open(), 0.0, LEVEL_FRUIT_GOAL),
    Level(2, "Pillars", "Four blocks to weave around.", _level_pillars(), 0.4, LEVEL_FRUIT_GOAL),
    Level(3, "Crossroads", "Broken cross in the middle.", _level_cross(), 0.8, LEVEL_FRUIT_GOAL),
    Level(4, "Courtyards", "Four rooms, thin doorways.", _level_boxes(), 1.1, LEVEL_FRUIT_GOAL + 1),
    Level(5, "Corridors", "Horizontal lanes. Plan the turn.", _level_corridors(), 1.5, LEVEL_FRUIT_GOAL + 1),
    Level(6, "Arena", "Ring wall with a split gate.", _level_arena(), 1.8, LEVEL_FRUIT_GOAL + 2),
    Level(7, "Labyrinth", "Tight maze, tight timing.", _level_labyrinth(), 2.2, LEVEL_FRUIT_GOAL + 2),
    Level(8, "Gauntlet", "Vertical gates. Finish the campaign.", _level_gauntlet(), 2.6, LEVEL_FRUIT_GOAL + 3),
]


def get_level(number: int) -> Level:
    index = max(1, min(number, len(LEVELS))) - 1
    return LEVELS[index]


def empty_cells(walls: Set[Cell], occupied: Set[Cell]) -> List[Cell]:
    cells: List[Cell] = []
    for x in range(GRID_COLS):
        for y in range(GRID_ROWS):
            cell = (x, y)
            if cell not in walls and cell not in occupied:
                cells.append(cell)
    return cells
