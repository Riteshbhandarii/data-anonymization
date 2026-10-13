"""OpenAI Privacy Filter as a local detector, same interface as PresidioDetector.

openai/privacy-filter (Apache 2.0) is a token classifier: a 1.5B-parameter
mixture of experts with about 50M parameters active per token. It tags every
token with BIOES labels over eight categories, mapped here to Presidio entity
names. Spans come from the constrained Viterbi decode the model card
describes, with its shipped default of all-zero transition biases; a plain
argmax per token splits phone numbers and addresses into fragments. On 23
sample texts this gave the same spans as the official opf package in 22; the
other differed by one character. The project's three patterns are added as for
GLiNER.

Needs transformers 5.6 or newer and a one-time download of about 2.8 GB of
weights. Only weights are fetched; no document text leaves the machine.
"""

import math
from types import SimpleNamespace

from detect.gliner_detector import pattern_spans, windows

MODEL = "openai/privacy-filter"

# Privacy Filter category -> Presidio entity name. account_number covers bank
# accounts and card numbers alike, so it gets its own name.
LABELS = {
    "private_person": "PERSON",
    "private_address": "LOCATION",
    "private_email": "EMAIL_ADDRESS",
    "private_phone": "PHONE_NUMBER",
    "private_date": "DATE_TIME",
    "private_url": "URL",
    "account_number": "ACCOUNT_NUMBER",
    "secret": "SECRET",
}

# Characters per forward pass. The model accepts 128k tokens, but the
# transformers port builds a full attention mask, so long text goes in windows.
# Each layer sees 128 tokens either side, so eight layers see about 1000 tokens,
# roughly this many characters.
WINDOW = 4000


def allowed_previous(labels):
    """For each tag, the tags that may come right before it under BIOES."""
    parts = [("O", None) if t == "O" else tuple(t.split("-", 1)) for t in labels]
    previous = []
    for prefix, category in parts:
        if prefix in ("I", "E"):
            previous.append([i for i, (p, c) in enumerate(parts) if p in ("B", "I") and c == category])
        else:
            previous.append([i for i, (p, _) in enumerate(parts) if p in ("O", "E", "S")])
    return previous


def viterbi(log_probs, labels):
    """The most likely tag sequence that is valid BIOES, one tag per row."""
    previous = allowed_previous(labels)
    outside = {i for i, t in enumerate(labels) if t == "O" or t[0] in "ES"}
    score = [lp if t == "O" or t[0] in "BS" else float("-inf")
             for lp, t in zip(log_probs[0], labels, strict=True)]
    back = []
    for row in log_probs[1:]:
        best = [max(options, key=score.__getitem__) for options in previous]
        score = [score[b] + lp for b, lp in zip(best, row, strict=True)]
        back.append(best)
    path = [max(outside, key=score.__getitem__)]
    for best in reversed(back):
        path.append(best[path[-1]])
    return [labels[i] for i in reversed(path)]


def merge_tags(tags, offsets, scores):
    """Turn per-token BIOES tags into (start, end, category, score) spans.

    A span starts at B or S, or wherever the category changes, and runs over
    the following tokens of the same category until E, S or O. Its score is
    the lowest token probability in it. Tokens with an empty offset (special
    tokens) are skipped.
    """
    spans, current = [], None
    for tag, (start, end), score in zip(tags, offsets, scores, strict=True):
        if start == end:
            continue
        if tag == "O":
            current = None
            continue
        prefix, category = tag.split("-", 1)
        if current and current[2] == category and prefix in ("I", "E"):
            current[1], current[3] = end, min(current[3], score)
        else:
            current = [start, end, category, score]
            spans.append(current)
        if prefix in ("E", "S"):
            current = None
    return [tuple(s) for s in spans]


class PrivacyFilterDetector:
    # CPU in float32 was faster than MPS on an M-series Mac (2.0 s against
    # 3.0 s for 20 000 characters), since only 50M parameters run per token.
    def __init__(self, model: str = MODEL, device: str = "cpu"):
        self.model_name = model
        self.device = device
        self._model = self._tokenizer = None

    def _load(self):
        import torch
        from transformers import AutoModelForTokenClassification, AutoTokenizer
        self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self._model = AutoModelForTokenClassification.from_pretrained(
            self.model_name, dtype=torch.float32)
        self._model.to(self.device).eval()

    def detect(self, text: str, language: str = "en") -> list:
        if not isinstance(text, str):
            raise TypeError("The detector input must be a string")
        if self._model is None:
            self._load()
        import torch

        spans = []
        id2label = self._model.config.id2label
        labels = [id2label[i] for i in range(len(id2label))]
        for offset, piece in windows(text, WINDOW):
            encoded = self._tokenizer(piece, return_offsets_mapping=True, return_tensors="pt")
            offsets = encoded.pop("offset_mapping")[0].tolist()
            with torch.no_grad():
                logits = self._model(**encoded.to(self.device)).logits[0]
            log_probs = logits.float().log_softmax(dim=-1).tolist()
            tags = viterbi(log_probs, labels)
            scores = [math.exp(row[labels.index(t)]) for row, t in zip(log_probs, tags, strict=True)]
            for start, end, category, score in merge_tags(tags, offsets, scores):
                # Token offsets include the spaces around a word piece.
                while start < end and piece[start].isspace():
                    start += 1
                while end > start and piece[end - 1].isspace():
                    end -= 1
                spans.append(SimpleNamespace(start=offset + start, end=offset + end,
                                             entity_type=LABELS[category], score=score))
        return spans + pattern_spans(text)
