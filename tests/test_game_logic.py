"""Logic tests that do not need a camera or a display."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from levels import LEVELS, empty_cells, get_level
from snake_game import Direction, SnakeGame
from snake_types import SNAKE_TYPES, get_snake_type


class LevelTests(unittest.TestCase):
    def test_eight_levels(self):
        self.assertEqual(len(LEVELS), 8)
        self.assertEqual(get_level(1).name, "Open Field")
        self.assertEqual(get_level(99).number, 8)

    def test_spawn_corridor_is_open(self):
        for level in LEVELS:
            cx, cy = 16, 12
            self.assertNotIn((cx, cy), level.walls, msg=level.name)
            self.assertNotIn((cx - 1, cy), level.walls, msg=level.name)

    def test_empty_cells_excludes_walls(self):
        walls = {(0, 0), (1, 1)}
        cells = empty_cells(walls, {(2, 2)})
        self.assertNotIn((0, 0), cells)
        self.assertNotIn((2, 2), cells)
        self.assertIn((3, 3), cells)


class SnakeTypeTests(unittest.TestCase):
    def test_five_types(self):
        self.assertEqual(len(SNAKE_TYPES), 5)
        self.assertTrue(get_snake_type("shadow").wrap_edges)
        self.assertTrue(get_snake_type("titan").wall_breaker)
        self.assertTrue(get_snake_type("specter").pass_self)
        self.assertEqual(get_snake_type("missing").id, "classic")


class EngineTests(unittest.TestCase):
    def test_moves_forward(self):
        game = SnakeGame(get_snake_type("classic"), 1)
        head = game.snake[0]
        game.update()
        self.assertEqual(game.snake[0], (head[0] + 1, head[1]))
        self.assertFalse(game.game_over)

    def test_no_instant_reverse(self):
        game = SnakeGame(get_snake_type("classic"), 1)
        game.change_direction("LEFT")
        self.assertEqual(game.next_direction, Direction.RIGHT)

    def test_wall_kills_classic(self):
        game = SnakeGame(get_snake_type("classic"), 1)
        game.snake = [(0, 5)]
        game.direction = Direction.LEFT
        game.next_direction = Direction.LEFT
        game.update()
        self.assertTrue(game.game_over)

    def test_shadow_wraps(self):
        game = SnakeGame(get_snake_type("shadow"), 1)
        game.snake = [(0, 5), (1, 5), (2, 5)]
        game.direction = Direction.LEFT
        game.next_direction = Direction.LEFT
        game.update()
        self.assertFalse(game.game_over)
        self.assertEqual(game.snake[0][0], 31)

    def test_tail_cell_is_safe(self):
        game = SnakeGame(get_snake_type("classic"), 1)
        game.snake = [(5, 5), (4, 5), (4, 6), (5, 6)]
        game.fruit = (0, 0)
        game.direction = Direction.DOWN
        game.next_direction = Direction.DOWN
        game.update()
        self.assertFalse(game.game_over)
        self.assertEqual(game.snake[0], (5, 6))

    def test_self_hit_kills(self):
        game = SnakeGame(get_snake_type("classic"), 1)
        game.snake = [(5, 5), (4, 5), (4, 6), (5, 6), (6, 6)]
        game.fruit = (0, 0)
        game.direction = Direction.DOWN
        game.next_direction = Direction.DOWN
        game.update()
        self.assertTrue(game.game_over)

    def test_specter_passes_self(self):
        game = SnakeGame(get_snake_type("specter"), 1)
        game.snake = [(5, 5), (4, 5), (4, 6), (5, 6), (6, 6)]
        game.fruit = (0, 0)
        game.direction = Direction.DOWN
        game.next_direction = Direction.DOWN
        game.update()
        self.assertFalse(game.game_over)

    def test_hand_wall_limit_and_block(self):
        game = SnakeGame(get_snake_type("classic"), 1)
        self.assertTrue(game.try_drop_hand_wall((2, 2)))
        self.assertFalse(game.try_drop_hand_wall((2, 2)))
        for i in range(5):
            self.assertTrue(game.try_drop_hand_wall((3 + i, 2)))
        self.assertFalse(game.try_drop_hand_wall((10, 2)))

    def test_titan_breaks_wall_on_boost(self):
        game = SnakeGame(get_snake_type("titan"), 2)
        if not game.maze_walls:
            self.skipTest("level 2 should have walls")
        wall = next(iter(game.maze_walls))
        game.snake = [(wall[0] - 1, wall[1])]
        game.direction = Direction.RIGHT
        game.next_direction = Direction.RIGHT
        game.speed_boost = True
        game.update()
        self.assertFalse(game.game_over)
        self.assertNotIn(wall, game.maze_walls)

    def test_eat_increases_length(self):
        game = SnakeGame(get_snake_type("classic"), 1)
        length = len(game.snake)
        hx, hy = game.snake[0]
        game.fruit = (hx + 1, hy)
        game.update()
        self.assertEqual(len(game.snake), length + 1)
        self.assertGreater(game.score, 0)

    def test_level_clear_on_goal(self):
        game = SnakeGame(get_snake_type("classic"), 1)
        game.fruits_eaten = game.level.fruit_goal - 1
        hx, hy = game.snake[0]
        game.fruit = (hx + 1, hy)
        game.update()
        self.assertTrue(game.won_level)


if __name__ == "__main__":
    unittest.main()
