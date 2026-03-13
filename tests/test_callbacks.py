from __future__ import annotations

from unittest import TestCase

from app.services.callbacks import parse_game_callback, parse_menu_callback, parse_subscription_callback


class CallbackParsingTests(TestCase):
    def test_parse_game_callback(self) -> None:
        parsed = parse_game_callback("game:double_strike:start:0")
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.game_id, "double_strike")
        self.assertEqual(parsed.action, "start")

    def test_parse_game_callback_rejects_invalid(self) -> None:
        self.assertIsNone(parse_game_callback("game:unknown:start:0"))
        self.assertIsNone(parse_game_callback("menu:main"))

    def test_parse_menu_callback(self) -> None:
        parsed = parse_menu_callback("menu:main")
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.action, "main")

    def test_parse_subscription_buy_callback(self) -> None:
        parsed = parse_subscription_callback("sub:buy:month:299")
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.action, "buy")
        self.assertEqual(parsed.plan_type, "month")
        self.assertEqual(parsed.stars, 299)
