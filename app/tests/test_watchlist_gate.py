"""매물 게이트(WL-G01/G02) 도메인 테스트 — 살 붙인 가드 검증.

매물 카운트가 0이면 잠김, 1 이상이면 해제. 잘못된 전이는 방어선 A가 막는다.
"""

import unittest

from contexts.watchlist.domain.watchlist_item import WatchlistItem
from contexts.watchlist.domain.watchlist_item_state import WatchlistItemState
from contexts.watchlist.domain.exceptions import IllegalTransition, InvariantViolation


class WatchlistGate(unittest.TestCase):
    def test_create_starts_watching(self):
        item = WatchlistItem.create(user_id=1, complex_id=42)
        self.assertEqual(item.state, WatchlistItemState.WATCHING)
        self.assertFalse(item.is_locked)
        self.assertEqual(item.complex_id, 42)

    def test_gate_locks_when_no_listings(self):
        item = WatchlistItem.create(1, 42)
        item.evaluate_gate(listing_count=0)          # WL-G01
        self.assertEqual(item.state, WatchlistItemState.GATE_LOCKED)
        self.assertTrue(item.is_locked)

    def test_gate_unlocks_when_listing_returns(self):
        item = WatchlistItem.create(1, 42)
        item.evaluate_gate(0)                         # → GATE_LOCKED
        item.evaluate_gate(3)                         # WL-G02 → WATCHING
        self.assertEqual(item.state, WatchlistItemState.WATCHING)

    def test_no_transition_when_state_already_matches(self):
        item = WatchlistItem.create(1, 42)
        item.evaluate_gate(5)                         # WATCHING + 매물 있음 → 그대로
        self.assertEqual(item.state, WatchlistItemState.WATCHING)

    def test_negative_listing_count_rejected(self):
        item = WatchlistItem.create(1, 42)
        with self.assertRaises(InvariantViolation):
            item.evaluate_gate(-1)

    def test_illegal_direct_transition_blocked(self):
        # 방어선 A: WATCHING→WATCHING 같은 자기전이는 ALLOWED에 없어 막힌다.
        item = WatchlistItem.create(1, 42)
        with self.assertRaises(IllegalTransition):
            item._transition(WatchlistItemState.WATCHING)


if __name__ == "__main__":
    unittest.main()
