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

from detect.local_llm import (
    FinalPassDetector,
    LocalLLMDetector,
    list_models,
    local_endpoint,
    pieces,
)


@contextmanager
def server(content, *, finish="stop", redirect=None, models=()):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(self.path)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"data": [{"id": name} for name in models]}).encode())

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

    def test_model_list_skips_embeddings_and_stays_on_loopback(self):
        with server("", models=["qwen/qwen3.5-9b", "text-embedding-nomic-embed-text-v1.5",
                                "google/gemma-4-e4b"]) as (url, requests):
            self.assertEqual(["google/gemma-4-e4b", "qwen/qwen3.5-9b"], list_models(url))
        self.assertEqual(["/v1/models"], requests)
        with self.assertRaises(ValueError):
            list_models("http://example.com/v1")

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


class ContextualPromptTests(unittest.TestCase):
    def test_default_payload_keeps_the_identifier_prompt(self):
        from detect.local_llm import ENTITY_TYPES, SYSTEM
        with server(json.dumps({"entities": []})) as (url, requests):
            LocalLLMDetector("local", base_url=url).detect("text")
        self.assertEqual(SYSTEM, requests[0]["messages"][0]["content"])
        enum = requests[0]["response_format"]["json_schema"]["schema"]["properties"]["entities"]["items"]
        self.assertEqual(ENTITY_TYPES, enum["properties"]["entity_type"]["enum"])

    def test_contextual_prompt_and_types(self):
        from detect.local_llm import CONTEXT_TYPES, SYSTEM_CONTEXTUAL
        content = json.dumps({"entities": [{"text": "LU-77/2021", "entity_type": "IDENTIFIER_CODE"}]})
        with server(content) as (url, requests):
            spans = LocalLLMDetector("local", base_url=url, prompt="contextual").detect("Permit LU-77/2021.")
        self.assertEqual(SYSTEM_CONTEXTUAL, requests[0]["messages"][0]["content"])
        enum = requests[0]["response_format"]["json_schema"]["schema"]["properties"]["entities"]["items"]
        self.assertEqual(CONTEXT_TYPES, enum["properties"]["entity_type"]["enum"])
        self.assertEqual([(7, 17, "IDENTIFIER_CODE")], [(s.start, s.end, s.entity_type) for s in spans])

    def test_identifier_types_are_rejected_in_contextual_mode(self):
        content = json.dumps({"entities": [{"text": "x", "entity_type": "IBAN_CODE"}]})
        with server(content) as (url, _), self.assertRaises(ValueError):
            LocalLLMDetector("local", base_url=url, prompt="contextual").detect("x")

    def test_non_strict_drops_and_counts_absent_text(self):
        content = json.dumps({"entities": [{"text": "not here", "entity_type": "PERSON"},
                                           {"text": "Kestrel", "entity_type": "PROJECT_OR_PRODUCT"}]})
        with server(content) as (url, _):
            detector = LocalLLMDetector("local", base_url=url, prompt="contextual", strict=False)
            spans = detector.detect("Project Kestrel")
        self.assertEqual([(8, 15)], [(s.start, s.end) for s in spans])
        self.assertEqual(1, detector.dropped)
        with server(content) as (url, _), self.assertRaises(ValueError):
            LocalLLMDetector("local", base_url=url, prompt="contextual").detect("Project Kestrel")

    def test_original_contextual_prompt_and_types(self):
        from detect.local_llm import (
            CONTEXT_TYPES,
            SYSTEM_ORIGINAL_CONTEXTUAL,
        )

        content = json.dumps({
            "entities": [
                {
                    "text": "UK-839201",
                    "entity_type": "IDENTIFIER_CODE",
                }
            ]
        })

        with server(content) as (url, requests):
            detector = LocalLLMDetector(
                "local",
                base_url=url,
                prompt="original_contextual",
            )
            spans = detector.detect(
                "Licence number UK-839201 belongs to John Smith.",
                "en",
            )

        self.assertEqual(
            SYSTEM_ORIGINAL_CONTEXTUAL,
            requests[0]["messages"][0]["content"],
        )

        schema = requests[0]["response_format"]["json_schema"]["schema"]
        entity_types = schema["properties"]["entities"]["items"]["properties"]["entity_type"]["enum"]

        self.assertEqual(CONTEXT_TYPES, entity_types)
        self.assertIn("original, unmasked", SYSTEM_ORIGINAL_CONTEXTUAL)
        self.assertNotIn("already hidden", SYSTEM_ORIGINAL_CONTEXTUAL)

        self.assertEqual(
            [(15, 24, "IDENTIFIER_CODE")],
            [(s.start, s.end, s.entity_type) for s in spans],
        )

    def test_unknown_prompt_is_rejected(self):
        with self.assertRaises(ValueError):
            LocalLLMDetector("local", prompt="other")


class UnionDetectorTests(unittest.TestCase):
    def test_model_sees_the_original_text_and_spans_are_kept(self):
        from detect.local_llm import UnionDetector
        seen = []

        class Fixed:
            def __init__(self, spans):
                self.spans = spans

            def detect(self, text, language="en"):
                seen.append(text)
                return self.spans

        base = Fixed([SimpleNamespace(start=0, end=4, entity_type="PERSON", score=1.0)])
        model = Fixed([SimpleNamespace(start=11, end=16, entity_type="ORGANIZATION", score=1.0)])
        spans = UnionDetector(base, model).detect("Aino works Lehto", "fi")
        self.assertEqual(["Aino works Lehto", "Aino works Lehto"], seen)
        self.assertEqual([(0, 4), (11, 16)], [(s.start, s.end) for s in spans])


if __name__ == "__main__":
    unittest.main()
