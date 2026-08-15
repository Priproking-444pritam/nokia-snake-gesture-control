"""Playable snake types with distinct stats and abilities."""

from dataclasses import dataclass
from typing import Tuple


Color = Tuple[int, int, int]


@dataclass(frozen=True)
class SnakeType:
    id: str
    name: str
    tagline: str
    description: str
    head: Color
    body: Color
    dark: Color
    accent: Color
    base_speed: float
    boost_speed: float
    score_mult: float
    wrap_edges: bool
    pass_self: bool
    wall_breaker: bool
    start_length: int


SNAKE_TYPES = [
    SnakeType(
        id="classic",
        name="Classic",
        tagline="Nokia original",
        description="Balanced speed. Dies on walls and itself. The authentic run.",
        head=(204, 255, 51),
        body=(155, 188, 15),
        dark=(90, 120, 12),
        accent=(180, 220, 40),
        base_speed=8.0,
        boost_speed=14.0,
        score_mult=1.0,
        wrap_edges=False,
        pass_self=False,
        wall_breaker=False,
        start_length=3,
    ),
    SnakeType(
        id="shadow",
        name="Shadow",
        tagline="Phase the rim",
        description="Wraps through outer edges. Inner maze walls still kill.",
        head=(210, 170, 255),
        body=(122, 78, 196),
        dark=(62, 32, 110),
        accent=(186, 140, 255),
        base_speed=7.5,
        boost_speed=13.0,
        score_mult=1.1,
        wrap_edges=True,
        pass_self=False,
        wall_breaker=False,
        start_length=3,
    ),
    SnakeType(
        id="ember",
        name="Ember",
        tagline="High risk heat",
        description="Faster and scores more. One mistake ends the run.",
        head=(255, 190, 90),
        body=(232, 92, 42),
        dark=(140, 40, 18),
        accent=(255, 140, 60),
        base_speed=11.0,
        boost_speed=18.0,
        score_mult=1.4,
        wrap_edges=False,
        pass_self=False,
        wall_breaker=False,
        start_length=4,
    ),
    SnakeType(
        id="titan",
        name="Titan",
        tagline="Break the maze",
        description="Slow tank. Pinch-boost into a maze wall to smash that block.",
        head=(180, 220, 255),
        body=(70, 120, 176),
        dark=(28, 56, 92),
        accent=(120, 190, 255),
        base_speed=6.0,
        boost_speed=10.0,
        score_mult=1.0,
        wrap_edges=False,
        pass_self=False,
        wall_breaker=True,
        start_length=3,
    ),
    SnakeType(
        id="specter",
        name="Specter",
        tagline="No self-bite",
        description="Glides through its own body. Walls and maze still end the game.",
        head=(140, 255, 230),
        body=(32, 168, 168),
        dark=(12, 78, 82),
        accent=(90, 230, 210),
        base_speed=8.5,
        boost_speed=15.0,
        score_mult=0.9,
        wrap_edges=False,
        pass_self=True,
        wall_breaker=False,
        start_length=5,
    ),
]


def get_snake_type(type_id: str) -> SnakeType:
    for snake_type in SNAKE_TYPES:
        if snake_type.id == type_id:
            return snake_type
    return SNAKE_TYPES[0]
