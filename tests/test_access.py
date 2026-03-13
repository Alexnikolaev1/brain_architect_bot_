from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest import TestCase

from app.services.access import effective_plan, is_pro_active, is_trial_active


class AccessServiceTests(TestCase):
    def test_trial_is_active_with_recent_start(self) -> None:
        user = {"plan": "trial", "trial_start": datetime.now(timezone.utc) - timedelta(days=2)}
        self.assertTrue(is_trial_active(user))
        self.assertEqual(effective_plan(user), "trial")

    def test_trial_is_expired_after_seven_days(self) -> None:
        user = {"plan": "trial", "trial_start": datetime.now(timezone.utc) - timedelta(days=8)}
        self.assertFalse(is_trial_active(user))
        self.assertEqual(effective_plan(user), "free")

    def test_pro_is_active_only_before_expiration(self) -> None:
        active_user = {"plan": "pro", "sub_expires": datetime.now(timezone.utc) + timedelta(days=3)}
        expired_user = {"plan": "pro", "sub_expires": datetime.now(timezone.utc) - timedelta(days=1)}
        self.assertTrue(is_pro_active(active_user))
        self.assertFalse(is_pro_active(expired_user))
        self.assertEqual(effective_plan(expired_user), "free")

    def test_vip_is_always_active(self) -> None:
        user = {"plan": "vip"}
        self.assertTrue(is_pro_active(user))
        self.assertEqual(effective_plan(user), "vip")
