from __future__ import annotations

from unittest import TestCase

from app.domain.subscription import parse_subscription_payload


class SubscriptionDomainTests(TestCase):
    def test_parse_valid_payload(self) -> None:
        plan_type, user_id = parse_subscription_payload("sub:month:123")
        self.assertEqual(plan_type, "month")
        self.assertEqual(user_id, 123)

    def test_parse_invalid_payload(self) -> None:
        with self.assertRaises(ValueError):
            parse_subscription_payload("bad")

        with self.assertRaises(ValueError):
            parse_subscription_payload("sub:unknown:123")
