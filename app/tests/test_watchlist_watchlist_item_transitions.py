"""[GENERATED] WatchlistItem 전이 매트릭스 테스트 — §9-① (전이 거부). 스펙에서 생성."""

import unittest

from contexts.watchlist.domain.watchlist_item import WatchlistItem
from contexts.watchlist.domain.exceptions import IllegalTransition
from contexts.watchlist.domain.watchlist_item_state import ALLOWED, WatchlistItemState


class WatchlistItemTransitions(unittest.TestCase):
    def test_full_matrix(self):
        for frm in WatchlistItemState:
            for to in WatchlistItemState:
                agg = WatchlistItem(state=frm)
                if to in ALLOWED[frm]:
                    agg._transition(to)
                    self.assertEqual(agg.state, to)
                else:
                    with self.assertRaises(IllegalTransition):
                        agg._transition(to)


if __name__ == "__main__":
    unittest.main()
