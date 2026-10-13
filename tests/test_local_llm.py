"""Loopback HTTP fixtures exercise the real adapter without models or credentials."""

import json
import os
import threading
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError

from detect.local_llm import FinalPassDetector, LocalLLMDetector, local_endpoint, pieces


@contextmanager
def server(content, *, finish="stop", redirect=None):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            requests.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            if redirect:
                self.send_response(302)
                self.send_header("Location", redirect)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"choices": [{"finish_reason": finish,
                "message": {"content": content}}]}).encode())

        def log_message(self, *args):
            pass

    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}/v1", requests
    finally:
        httpd.shutdown()
        thread.join()
        httpd.server_close()


class LocalLLMTests(unittest.TestCase):
    def test_loopback_only(self):
        for url in ["https://127.0.0.1/v1", "http://example.com/v1", "http://192.168.1.1/v1",
                    "http://127.0.0.1.evil.test/v1", "http://user@127.0.0.1/v1",
                    "http://127.0.0.1/v1?secret=1", "http://127.0.0.1/v1#frag",
                    "http://127.0.0.1:bad/v1", "http://0.0.0.0/v1", "http://[::]/v1"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                local_endpoint(url)
        self.assertEqual("http://127.0.0.1:1234/v1/chat/completions",
                         local_endpoint("http://localhost:1234/v1/"))
        self.assertEqual("http://[::1]:1234/v1/chat/completions",
                         local_endpoint("http://[::1]:1234/v1"))

    def test_exact_repeated_unicode_spans_and_payload(self):
        content = json.dumps({"entities": [{"text": "Ääni Oy", "entity_type": "ORGANIZATION"}]})
        with server(content) as (url, requests), patch.dict(os.environ, {"http_proxy": "http://unreachable.invalid:9"}):
            spans = LocalLLMDetector("chosen-model", base_url=url).detect("Ääni Oy; Ääni Oy", "fi")
        self.assertEqual([(0, 7), (9, 16)], [(s.start, s.end) for s in spans])
        self.assertEqual("chosen-model", requests[0]["model"])
        self.assertEqual(0, requests[0]["temperature"])
        self.assertEqual("none", requests[0]["reasoning_effort"])
        self.assertFalse(requests[0]["chat_template_kwargs"]["enable_thinking"])
        self.assertEqual("json_schema", requests[0]["response_format"]["type"])
        self.assertNotIn("tools", requests[0])

    def test_redirect_is_rejected_before_following(self):
        with server("", redirect="http://remote.invalid/collect") as (url, requests), self.assertRaises(HTTPError):
            LocalLLMDetector("local", base_url=url).detect("private")
        self.assertEqual(1, len(requests))

    def test_invalid_or_hallucinated_entities_fail(self):
        bad = ["", "not json", "[]", '{"entities": {}}', '{"entities": [], "extra": 1}',
               '{"entities": [null]}', '{"entities": [{"text": "", "entity_type": "PERSON"}]}',
               '{"entities": [{"text": "missing", "entity_type": "PERSON"}]}',
               '{"entities": [{"text": "name", "entity_type": "UNKNOWN"}]}',
               '{"entities": [{"text": 3, "entity_type": "PERSON"}]}']
        for content in bad:
            with self.subTest(content=content), server(content) as (url, _), self.assertRaises(ValueError):
                LocalLLMDetector("local", base_url=url).detect("name")

    def test_truncated_output_is_error(self):
        with server('{"entities": []}', finish="length") as (url, _), self.assertRaises(ValueError):
            LocalLLMDetector("local", base_url=url).detect("name")

    def test_empty_input_never_requests(self):
        with server("") as (url, requests):
            self.assertEqual([], LocalLLMDetector("local", base_url=url).detect(""))
        self.assertEqual([], requests)

    def test_config_validation(self):
        for model in [None, "", " "]:
            with self.assertRaises(ValueError):
                LocalLLMDetector(model)
        for timeout in [0, -1, float("inf"), float("nan")]:
            with self.assertRaises(ValueError):
                LocalLLMDetector("local", timeout=timeout)
        with self.assertRaises(TypeError):
            LocalLLMDetector("local").detect(None)

    def test_overlapping_windows_deduplicate(self):
        text = "x" * 3800 + "Aino" + "x" * 800
        content = '{"entities": [{"text": "Aino", "entity_type": "PERSON"}]}'
        with server(content) as (url, requests):
            spans = LocalLLMDetector("local", base_url=url).detect(text)
        self.assertEqual(2, len(requests))
        self.assertEqual([(3800, 3804)], [(s.start, s.end) for s in spans])
        self.assertEqual([(0, text[:4000]), (3600, text[3600:])], list(pieces(text)))

    def test_final_pass_hides_identifiers_and_preserves_offsets(self):
        base_span = SimpleNamespace(start=0, end=4, entity_type="PERSON", score=0.9)
        final_span = SimpleNamespace(start=9, end=17, entity_type="QUASI_IDENTIFIER", score=1)
        base = SimpleNamespace(detect=lambda text, language: [base_span])
        seen = []
        final = SimpleNamespace(detect=lambda text, language: seen.append((text, language)) or [final_span])
        spans = FinalPassDetector(base, final).detect("Aino\njob Tampere", "fi")
        self.assertEqual([("████\njob Tampere", "fi")], seen)
        self.assertEqual([base_span, final_span], spans)


class LocalBenchmarkTests(unittest.TestCase):
    def test_failed_documents_stay_in_recall_denominator(self):
        import hashlib
        import tempfile
        from pathlib import Path

        from eval.local_llm_bench import benchmark

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "labels").mkdir()
            (root / "text").mkdir()
            (root / "index.csv").write_text("file\na.md\n", encoding="utf-8")
            label = json.dumps({"language": "fi", "entities": [
                {"type": "PERSON", "value": "Aino", "location": "body"}]})
            (root / "labels/a.json").write_text(label, encoding="utf-8")
            (root / "text/a.txt").write_text("Aino", encoding="utf-8")
            digest = hashlib.sha256(label.encode() + b"Aino").hexdigest()
            (root / "corpus.json").write_text(json.dumps({"corpus_sha256": digest}), encoding="utf-8")

            class BrokenDetector:
                def detect(self, text, language):
                    raise ValueError("Provider echoed private text")

            report = benchmark(root, BrokenDetector())
            self.assertEqual(1, report["failed_documents"])
            self.assertEqual([{"language": "fi", "entity_type": "PERSON", "planted": 1,
                               "covered": 0, "partial": 0}], report["recall"])
            self.assertNotIn("private", json.dumps(report))
            (root / "text/a.txt").write_text("changed", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "digest"):
                benchmark(root, BrokenDetector())


if __name__ == "__main__":
    unittest.main()
