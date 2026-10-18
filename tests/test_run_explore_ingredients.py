"""The ingredients of a Goal of exploration are drawn by the run and the Goal's number (bench.run_explore)."""
from pathlib import Path

from bench.run_explore import ingredients_for


def test_a_goal_taken_up_again_in_its_run_draws_the_same_ingredients():
    assert ingredients_for(Path('/x/explore16'), 3) == ingredients_for(Path('/y/explore16'), 3)


def test_another_run_draws_others():
    # Explorations 13 to 16 (2026-10-17, 18) drew by the number alone, and each began with the area of grass or of
    # monuments in Shinjuku and Toshima, which ran out of steps every time.
    assert ingredients_for(Path('/x/explore16'), 1) != ingredients_for(Path('/x/explore17'), 1)
