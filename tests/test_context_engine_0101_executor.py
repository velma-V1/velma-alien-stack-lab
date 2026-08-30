from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from alien_lab.context_engine_adapters import FixtureContextAdapter
from alien_lab.context_engine_corpus import build_context_corpus
from alien_lab.context_engine_executor import (
    FixtureAnswerProvider,
    FixtureVelmaAnswerAdapter,
    run_pipeline_with_components,
)
from alien_lab.context_engine_types import ADVANCED_SYSTEMS, RETRIEVAL_ARMS


class ContextEngine0101ExecutorTests(unittest.TestCase):
    def test_full_credential_free_pipeline_preserves_all_stage_and_freshness_counts(self) -> None:
        corpus = build_context_corpus(seed=20261001)
        retrieval_adapters = {
            **{system_id: FixtureContextAdapter(system_id=system_id) for system_id in ADVANCED_SYSTEMS},
            "DENSE_VECTOR_RAG": FixtureContextAdapter(system_id="DENSE_VECTOR_RAG"),
        }
        provider = FixtureAnswerProvider()
        velma = FixtureVelmaAnswerAdapter()
        with tempfile.TemporaryDirectory() as tmp:
            result = run_pipeline_with_components(
                corpus=corpus,
                retrieval_adapters=retrieval_adapters,
                answer_provider=provider,
                velma_adapter=velma,
                output_dir=Path(tmp),
                fixture_mode=True,
            )
            self.assertEqual(result["conclusion"], "NON_LIVE_FIXTURE_RUN")
            self.assertFalse(result["live_model_evidence"])
            self.assertEqual(result["stage_a_base_cells"], 792)
            self.assertEqual(result["stage_b_base_observations"], 648)
            self.assertEqual(result["discovery_topologies"], 156)
            self.assertEqual(result["stage_c1_base_cells"], 144)
            self.assertEqual(result["stage_d_base_cells"], 120)
            self.assertEqual(result["stage_a_freshness_v2_cells"], 99)
            self.assertEqual(result["stage_b_freshness_v2_observations"], 81)
            self.assertEqual(result["stage_c1_freshness_v2_cells"], 18)
            self.assertEqual(result["stage_d_freshness_v2_cells"], 15)
            self.assertEqual(len(result["selected_topology_ids"]), 6)
            self.assertEqual(len(set(result["selected_topology_ids"])), 6)
            self.assertIn(result["best_standalone_context"], RETRIEVAL_ARMS)
            self.assertIn(result["best_confirmed_composition"], result["selected_topology_ids"])
            self.assertEqual(result["pretransfer_document_count"], 288)
            self.assertEqual(result["full_document_count"], 384)
            self.assertTrue((Path(tmp) / "pipeline-summary.json").exists())
            self.assertTrue((Path(tmp) / "selection.json").exists())

    def test_pipeline_replay_is_deterministic_in_fixture_mode(self) -> None:
        corpus = build_context_corpus(seed=20261001)
        def components():
            return (
                {
                    **{system_id: FixtureContextAdapter(system_id=system_id) for system_id in ADVANCED_SYSTEMS},
                    "DENSE_VECTOR_RAG": FixtureContextAdapter(system_id="DENSE_VECTOR_RAG"),
                },
                FixtureAnswerProvider(),
                FixtureVelmaAnswerAdapter(),
            )
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            adapters_a, provider_a, velma_a = components()
            adapters_b, provider_b, velma_b = components()
            first = run_pipeline_with_components(corpus=corpus, retrieval_adapters=adapters_a, answer_provider=provider_a, velma_adapter=velma_a, output_dir=Path(a), fixture_mode=True)
            second = run_pipeline_with_components(corpus=corpus, retrieval_adapters=adapters_b, answer_provider=provider_b, velma_adapter=velma_b, output_dir=Path(b), fixture_mode=True)
            self.assertEqual(first["pipeline_fingerprint"], second["pipeline_fingerprint"])
            self.assertEqual(first["selected_topology_ids"], second["selected_topology_ids"])
            self.assertEqual(first["best_standalone_context"], second["best_standalone_context"])
            self.assertEqual(first["best_confirmed_composition"], second["best_confirmed_composition"])


if __name__ == "__main__":
    unittest.main()
