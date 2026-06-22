"""[GENERATED] CollectionJob 전이 매트릭스 테스트 — §9-① (전이 거부). 스펙에서 생성."""

import unittest

from contexts.market_data.domain.collection_job import CollectionJob
from contexts.market_data.domain.exceptions import IllegalTransition
from contexts.market_data.domain.collection_job_state import ALLOWED, CollectionJobState


class CollectionJobTransitions(unittest.TestCase):
    def test_full_matrix(self):
        for frm in CollectionJobState:
            for to in CollectionJobState:
                agg = CollectionJob(state=frm)
                if to in ALLOWED[frm]:
                    agg._transition(to)
                    self.assertEqual(agg.state, to)
                else:
                    with self.assertRaises(IllegalTransition):
                        agg._transition(to)


if __name__ == "__main__":
    unittest.main()
