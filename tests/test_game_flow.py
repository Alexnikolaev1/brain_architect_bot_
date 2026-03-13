from __future__ import annotations

from unittest import TestCase

from app.services.game_flow import calculate_round_result


class GameFlowTests(TestCase):
    def test_calculate_round_result_defaults(self) -> None:
        result = calculate_round_result(is_correct=False, started_at=None, difficulty=None)
        self.assertEqual(result.score, 0)
        self.assertEqual(result.difficulty, 1)

    def test_calculate_round_result_uses_difficulty(self) -> None:
        fast = calculate_round_result(is_correct=True, started_at=0, difficulty=5)
        slow = calculate_round_result(is_correct=True, started_at=1, difficulty=1)
        self.assertGreaterEqual(fast.score, slow.score)
