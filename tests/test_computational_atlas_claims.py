from __future__ import annotations

import unittest

from alien_lab.computational_atlas_report import build_discovery_report
from alien_lab.computational_atlas_worlds import build_worlds


class ComputationalAtlasClaimTests(unittest.TestCase):
    def test_multi_engine_corequirement_is_not_reported_as_measured_synergy(self) -> None:
        report = build_discovery_report(
            worlds=build_worlds(seed=20260829, count=192),
            phase_maps={"minimum_basis": {}, "leave_one_out": {}, "computational_coverage": {}},
        )
        synergy = report["maps"]["synergy_matrix"]
        self.assertEqual(synergy["evidence_kind"], "CAPABILITY_COREQUIREMENT_CANDIDATES")
        self.assertFalse(synergy["measured_synergy"])
        self.assertEqual(synergy["status"], "PENDING_TYPED_DATAFLOW_EVIDENCE")
        self.assertTrue(synergy["candidate_pairs"])


if __name__ == "__main__":
    unittest.main()
