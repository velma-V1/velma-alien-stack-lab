import json
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from alien_lab.ollama import OllamaClient
from alien_lab.records import RunRecord, append_jsonl, stable_hash


class _Handler(BaseHTTPRequestHandler):
    last_body = None
    delay = 0.0

    def do_POST(self):
        length = int(self.headers["Content-Length"])
        type(self).last_body = json.loads(self.rfile.read(length))
        if type(self).delay:
            time.sleep(type(self).delay)
        payload = {
            "response": "B",
            "thinking": "short trace",
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 101,
            "prompt_eval_duration": 1_000_000_000,
            "eval_count": 20,
            "eval_duration": 2_000_000_000,
            "total_duration": 4_000_000_000,
            "load_duration": 500_000_000,
        }
        body = json.dumps(payload).encode()
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except BrokenPipeError:
            pass

    def do_GET(self):
        payload = {
            "models": [
                {
                    "name": "qwen3.5:9b-q8_0",
                    "model": "qwen3.5:9b-q8_0",
                    "digest": "abc123",
                    "size": 9700000000,
                    "details": {"quantization_level": "Q8_0"}
                }
            ]
        }
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        return


class RecordTests(unittest.TestCase):
    def setUp(self):
        _Handler.delay = 0.0
        self.server = HTTPServer(("127.0.0.1", 0), _Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.client = OllamaClient(f"http://127.0.0.1:{self.server.server_port}")

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=1)

    def test_ollama_payload_and_metric_extraction(self):
        result = self.client.generate(
            model="qwen3.5:9b-q8_0",
            prompt="test",
            num_ctx=25600,
            num_predict=128,
            temperature=0,
            seed=42,
            timeout_seconds=2,
        )
        body = _Handler.last_body
        self.assertEqual(body["model"], "qwen3.5:9b-q8_0")
        self.assertEqual(body["options"]["num_ctx"], 25600)
        self.assertEqual(body["options"]["num_predict"], 128)
        self.assertTrue(body["think"])
        self.assertEqual(result.eval_tokens, 20)
        self.assertEqual(result.total_ns, 4_000_000_000)
        self.assertEqual(result.load_ns, 500_000_000)
        self.assertAlmostEqual(result.tokens_per_second, 10.0)
        self.assertFalse(result.hit_ceiling)
        self.assertEqual(result.status, "OK")


    def test_model_metadata_captures_digest_and_quantization(self):
        meta = self.client.model_metadata("qwen3.5:9b-q8_0", timeout_seconds=2)
        self.assertEqual(meta["digest"], "abc123")
        self.assertEqual(meta["details"]["quantization_level"], "Q8_0")

    def test_ceiling_detection(self):
        result = self.client.generate(
            model="m", prompt="x", num_ctx=10, num_predict=20,
            temperature=0, seed=1, timeout_seconds=2,
        )
        self.assertTrue(result.hit_ceiling)

    def test_timeout_is_classified_separately(self):
        _Handler.delay = 0.2
        result = self.client.generate(
            model="m", prompt="x", num_ctx=10, num_predict=20,
            temperature=0, seed=1, timeout_seconds=0.03,
        )
        self.assertEqual(result.status, "TIME_BUDGET_ABORT")
        self.assertIsNone(result.response)

    def test_append_jsonl_is_append_only(self):
        row = RunRecord(run_id="r1", task_id="t1", status="OK")
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "runs.jsonl"
            append_jsonl(path, row)
            append_jsonl(path, RunRecord(run_id="r2", task_id="t2", status="OK"))
            lines = path.read_text().splitlines()
            self.assertEqual(len(lines), 2)
            self.assertEqual(json.loads(lines[0])["run_id"], "r1")
            self.assertEqual(json.loads(lines[1])["run_id"], "r2")

    def test_stable_hash_is_order_independent_for_dict_keys(self):
        self.assertEqual(stable_hash({"a": 1, "b": 2}), stable_hash({"b": 2, "a": 1}))


if __name__ == "__main__":
    unittest.main()
