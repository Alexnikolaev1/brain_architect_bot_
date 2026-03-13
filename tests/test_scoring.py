from __future__ import annotations

from unittest import TestCase

from app.services.scoring import compute_score


class ScoringTests(TestCase):
    def test_wrong_answer_gives_zero(self) -> None:
        self.assertEqual(compute_score(False, 1_000, 3), 0)

    def test_fast_answer_gets_speed_bonus(self) -> None:
        fast = compute_score(True, 1_000, 2)
        slow = compute_score(True, 25_000, 2)
        self.assertGreater(fast, slow)

    def test_very_slow_answer_has_no_bonus(self) -> None:
        score = compute_score(True, 60_000, 2)
        self.assertEqual(score, 200)
