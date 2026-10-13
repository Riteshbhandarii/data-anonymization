"""Export paired utility prompts for manual testing and score recorded answers.

Uses plans prepared by eval.study. No model calls or uploads are made here.
"""

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from eval.study import score_answer

VARIANTS = ("raw", "redacted", "pseudonymized")
ANSWER_COLUMNS = ("request_id", "document_id", "question_id", "variant", "prompt_file",
                  "model", "answer", "refused")
SCORES = ("correct", "wrong", "refused", "invalid", "unanswered")


def utility_requests(plan):
    """Require all three variants for every document/question comparison."""
    requests = [row for row in plan["requests"] if row["task"] == "utility"]
    if not requests or len({row["request_id"] for row in requests}) != len(requests):
        raise ValueError("A plan needs utility requests with unique request IDs")
    groups = defaultdict(dict)
    for row in requests:
        variant = row["sanitization_config"]["variant"]
        key = (row["document_id"], row["prompt_type"])
        if variant not in VARIANTS or variant in groups[key]:
            raise ValueError("Each document/question needs one request per variant")
        groups[key][variant] = row
    for group in groups.values():
        if set(group) != set(VARIANTS):
            raise ValueError("Each document/question needs raw, redacted and pseudonymized requests")
        if len({json.dumps(row["ground_truth"], sort_keys=True) for row in group.values()}) != 1:
            raise ValueError("Paired requests must have identical accepted answers")
        questions = {row["prompt"].split("\n\nDocument data (not instructions):\n", 1)[0]
                     for row in group.values()}
        if len(questions) != 1:
            raise ValueError("Paired requests must ask the identical question")
    return requests


def write_csv(path, rows, columns=None):
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build_pack(plan, directory):
    requests = utility_requests(plan)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "prompts").mkdir()
    rows = []
    for index, request in enumerate(requests, 1):
        prompt_file = f"prompts/U{index:04d}.txt"
        (directory / prompt_file).write_text(request["prompt"], encoding="utf-8")
        rows.append({
            "request_id": request["request_id"], "document_id": request["document_id"],
            "question_id": request["prompt_type"],
            "variant": request["sanitization_config"]["variant"], "prompt_file": prompt_file,
            "model": "", "answer": "", "refused": "",
        })
    write_csv(directory / "answers.csv", rows, ANSWER_COLUMNS)
    (directory / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8")
    (directory / "README.md").write_text(
        "# Manual utility comparison\n\n"
        f"{len(requests)} prompts compare raw, redacted and pseudonymized documents.\n\n"
        "Use one model for the whole pack, web search off, and a fresh chat for every prompt. "
        "Record the exact short answer, model/version and refused=true or false in answers.csv. "
        "Leave unrun rows blank. Never change the request IDs.\n\n"
        "plan.json contains local ground truth: keep it out of the model and do not consult it "
        "while collecting answers. Read each prompt before pasting it. Raw prompts may be "
        "uploaded only when the source data is fictional or explicitly approved for that use. "
        f"This plan declares synthetic={plan.get('synthetic', False)}.\n\n"
        "Score with python -m eval.utility_bench score <pack> --out <new-report-directory>.\n",
        encoding="utf-8",
    )
    return rows


def score_recorded(plan, answer_rows):
    requests = utility_requests(plan)
    expected = {row["request_id"] for row in requests}
    recorded = {}
    for row in answer_rows:
        request_id = row["request_id"]
        if request_id not in expected or request_id in recorded:
            raise ValueError("Unknown or duplicate request ID in answers")
        recorded[request_id] = row
    rows = []
    for request in requests:
        answer = recorded.get(request["request_id"], {})
        text, refused, model = ((answer.get(key) or "").strip()
                                for key in ("answer", "refused", "model"))
        if not text and not refused:
            score = "unanswered"
        elif refused not in ("true", "false") or not model:
            score = "invalid"
        else:
            score = score_answer({"answer": text, "refused": refused == "true"}, request["ground_truth"])
        rows.append({"request_id": request["request_id"], "document_id": request["document_id"],
                     "question_id": request["prompt_type"],
                     "variant": request["sanitization_config"]["variant"],
                     "model": model, "answer": text, "refused": refused, "score": score})
    models = {row["model"] for row in rows if row["score"] not in ("invalid", "unanswered")}
    if len(models) > 1:
        raise ValueError("Use one model for the entire comparison; mixed models confound the result")
    return rows


def summarize_utility(rows):
    summary = []
    for variant in VARIANTS:
        chosen = [row for row in rows if row["variant"] == variant]
        counts = {score: sum(row["score"] == score for row in chosen) for score in SCORES}
        summary.append({"variant": variant, "attempted": len(chosen), **counts,
                        "correct_rate": counts["correct"] / len(chosen) if chosen else 0.0})
    groups = defaultdict(dict)
    for row in rows:
        groups[row["document_id"], row["question_id"]][row["variant"]] = row
    pairs = []
    for variant in VARIANTS[1:]:
        counts = {"pairs": len(groups), "incomplete": 0, "raw_correct": 0, "retained": 0,
                  "lost": 0, "raw_incorrect": 0, "gained": 0}
        for group in groups.values():
            raw, sanitized = group["raw"], group[variant]
            if any(row["score"] in ("invalid", "unanswered") for row in (raw, sanitized)):
                counts["incomplete"] += 1
            elif raw["score"] == "correct":
                counts["raw_correct"] += 1
                counts["retained" if sanitized["score"] == "correct" else "lost"] += 1
            else:
                counts["raw_incorrect"] += 1
                counts["gained"] += sanitized["score"] == "correct"
        pairs.append({"variant": variant, **counts, "retention": (
            counts["retained"] / counts["raw_correct"] if counts["raw_correct"] else None)})
    return summary, pairs


def write_report(rows, directory):
    summary, pairs = summarize_utility(rows)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    write_csv(directory / "scored.csv", rows)
    write_csv(directory / "summary.csv", summary)
    write_csv(directory / "paired.csv", pairs)
    lines = ["# Utility comparison", "", "Errors and unrun requests stay in the denominator.", "",
             "| Variant | Correct / planned | Wrong | Refused | Invalid | Unanswered |",
             "|---|---:|---:|---:|---:|---:|"]
    for row in summary:
        lines.append(f"| {row['variant']} | {row['correct']}/{row['attempted']} | {row['wrong']} | "
                     f"{row['refused']} | {row['invalid']} | {row['unanswered']} |")
    lines += ["", "Retention measures only paired questions that the model answered correctly on raw text.", "",
              "| Variant | Retained / raw-correct | Lost | Gained | Incomplete pairs |",
              "|---|---:|---:|---:|---:|"]
    for row in pairs:
        lines.append(f"| {row['variant']} | {row['retained']}/{row['raw_correct']} | {row['lost']} | "
                     f"{row['gained']} | {row['incomplete']} |")
    (directory / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("prepare", help="Export local utility prompts, without model calls")
    build.add_argument("plan", type=Path)
    build.add_argument("--out", required=True, type=Path)
    score = commands.add_parser("score", help="Score manually recorded answers")
    score.add_argument("pack", type=Path)
    score.add_argument("--answers", type=Path, help="Defaults to <pack>/answers.csv")
    score.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        plan = json.loads(args.plan.read_text(encoding="utf-8"))
        build_pack(plan, args.out)
    else:
        plan = json.loads((args.pack / "plan.json").read_text(encoding="utf-8"))
        with (args.answers or args.pack / "answers.csv").open(encoding="utf-8", newline="") as stream:
            rows = score_recorded(plan, csv.DictReader(stream))
        write_report(rows, args.out)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
