from __future__ import annotations

import unittest
from pathlib import Path

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

    def test_g_h_i_remain_definition_only_until_explicit_evidence_gate(self) -> None:
        import alien_lab.computational_atlas_accumulation as accumulation
        import alien_lab.computational_atlas_frontier as frontier
        import alien_lab.computational_atlas_horizon as horizon
        import alien_lab.computational_atlas_live_runner as live_runner
        from alien_lab.computational_atlas_live_ledger import build_phase_g_ledger, build_phase_h_ledger, build_phase_i_ledger

        # Frozen exam definitions remain available.
        self.assertEqual(len(build_phase_g_ledger()), 864)
        self.assertEqual(len(build_phase_h_ledger()), 120)
        self.assertEqual(len(build_phase_i_ledger()), 288)

        # Runtime/system mechanisms stay absent until the explicit post-evidence gate.
        for name in ("run_phase_g_cell", "run_phase_h_cell", "run_phase_i_cell", "CapabilityRuntimeState"):
            self.assertFalse(hasattr(live_runner, name), name)
        for name in ("CapabilityPackage", "create_capability_package"):
            self.assertFalse(hasattr(accumulation, name), name)
        self.assertFalse(hasattr(horizon, "execute_horizon_job"))
        self.assertFalse(hasattr(frontier, "run_generic_tool_agent"))

        workflow = Path(".github/workflows/010-smoke.yml").read_text(encoding="utf-8")
        self.assertNotIn("tests.test_computational_atlas_live_g_i", workflow)


if __name__ == "__main__":
    unittest.main()
