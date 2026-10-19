"""Draw the README result charts from the saved aggregates in eval/baselines/.

Run from the repository root (needs matplotlib):

    python docs/figures/make_figures.py

Writes a light and a dark SVG per chart into docs/figures/.
"""
import collections
import json
from pathlib import Path

import matplotlib

matplotlib.use("svg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "eval" / "baselines"
OUT = ROOT / "docs" / "figures"

# Reference data-viz palette: two categorical slots, validated for CVD and
# contrast on each surface.
THEMES = {
    "light": {"surface": "#fcfcfb", "text": "#0b0b0b", "muted": "#52514e",
              "grid": "#e4e3df", "s1": "#2a78d6", "s2": "#eb6834"},
    "dark": {"surface": "#1a1a19", "text": "#f0efec", "muted": "#c3c2b7",
             "grid": "#34332f", "s1": "#3987e5", "s2": "#d95926"},
}

plt.rcParams.update({
    "svg.fonttype": "none",
    "svg.hashsalt": "data-anonymization",
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 10,
})


def load(name):
    return json.loads((BASE / name).read_text(encoding="utf-8"))


def style(ax, t):
    ax.set_facecolor(t["surface"])
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(t["grid"])
    ax.tick_params(colors=t["muted"], length=0)
    ax.xaxis.grid(True, color=t["grid"], linewidth=0.8)
    ax.set_axisbelow(True)


def save(fig, name, theme):
    path = OUT / f"{name}-{theme}.svg"
    fig.savefig(path, facecolor=fig.get_facecolor(), bbox_inches="tight", pad_inches=0.15,
                metadata={"Date": None})
    plt.close(fig)
    print("->", path.relative_to(ROOT))


def recall_rows():
    """Whole-value recall of basic Presidio and combined per labelled dataset."""
    agg = collections.defaultdict(lambda: [0, 0])
    for r in load("dataset-audit-matrix.json")["results"]:
        lang = r["language"] if r["dataset"] == "ai4privacy" else ""
        agg[(r["method"], r["dataset"], lang)][0] += r["covered"]
        agg[(r["method"], r["dataset"], lang)][1] += r["planted"]
    labels = [("fake", "", "Synthetic EN + FI"), ("tab", "", "TAB, English"),
              ("turku", "", "Turku NER, Finnish"), ("ai4privacy", "en", "ai4privacy, English"),
              ("ai4privacy", "fi", "ai4privacy, Finnish")]
    return [(label, agg[("basic", d, lang)], agg[("combined", d, lang)]) for d, lang, label in labels]


def chart_recall(theme):
    t = THEMES[theme]
    rows = recall_rows()[::-1]
    fig, ax = plt.subplots(figsize=(7.2, 3.6), facecolor=t["surface"])
    style(ax, t)
    h = 0.36
    for i, (label, basic, comb) in enumerate(rows):
        b, c = 100 * basic[0] / basic[1], 100 * comb[0] / comb[1]
        ax.barh(i + h / 2 + 0.02, c, height=h, color=t["s1"])
        ax.barh(i - h / 2 - 0.02, b, height=h, color=t["s2"])
        ax.text(c + 1, i + h / 2 + 0.02, f"{c:.1f}%", va="center", fontsize=8.5, color=t["text"])
        ax.text(b + 1, i - h / 2 - 0.02, f"{b:.1f}%", va="center", fontsize=8.5, color=t["muted"])
    ax.set_yticks(range(len(rows)), [r[0] for r in rows], color=t["text"])
    ax.set_xlim(0, 108)
    ax.set_xticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"])
    ax.set_title("Identifiers found, whole values only", loc="left", color=t["text"],
                 fontsize=11.5, fontweight="bold", pad=22)
    ax.text(0, 1.03, "combined vs. out-of-the-box Presidio (basic); each dataset has its own denominator",
            transform=ax.transAxes, fontsize=8.5, color=t["muted"])
    handles = [plt.Rectangle((0, 0), 1, 1, color=t["s1"]), plt.Rectangle((0, 0), 1, 1, color=t["s2"])]
    leg = ax.legend(handles, ["combined", "basic"], loc="upper center", bbox_to_anchor=(0.5, -0.12),
                    ncol=2, frameon=False, fontsize=8.5, handlelength=1.2)
    for txt in leg.get_texts():
        txt.set_color(t["text"])
    save(fig, "rq2-recall", theme)


def reid_rows():
    rows = load("public-ai-results-2026-10-19.json")["rows"]

    def count(pred, ok="yes"):
        sel = [r for r in rows if pred(r)]
        return sum(r["score"] == ok for r in sel), len(sel)

    return [
        ("Named from anonymized text", count(lambda r: r["group"] in (
            "anonymized fictional / naming", "anonymized real-public / naming"))),
        ("Named a real organisation", count(lambda r: r["group"] == "anonymized real-public / naming")),
        ("Named from raw text (ceiling)", count(lambda r: r["group"] == "raw fictional ceiling / naming")),
        ("Guessed on unrelated input", count(lambda r: r["group"] == "unrelated control", ok="no")),
        ("Linked documents correctly", count(lambda r: r["group"] == "linkage")),
    ]


def chart_reid(theme):
    t = THEMES[theme]
    rows = reid_rows()[::-1]
    fig, ax = plt.subplots(figsize=(7.2, 3.2), facecolor=t["surface"])
    style(ax, t)
    for i, (label, (k, n)) in enumerate(rows):
        ax.barh(i, 100 * k / n, height=0.5, color=t["s1"])
        ax.text(100 * k / n + 1.5, i, f"{k} of {n}", va="center", fontsize=8.5, color=t["text"])
    ax.set_yticks(range(len(rows)), [r[0] for r in rows], color=t["text"])
    ax.set_xlim(0, 112)
    ax.set_xticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"])
    ax.set_title("What ChatGPT Free could tell", loc="left", color=t["text"],
                 fontsize=11.5, fontweight="bold", pad=22)
    ax.text(0, 1.03, "71 prompts, one fresh chat each; the one anonymized hit was a name the detector missed",
            transform=ax.transAxes, fontsize=8.5, color=t["muted"])
    save(fig, "rq3-reidentification", theme)


def utility_counts(lang):
    """Exact-answer and evidence-supported correct counts per variant.

    Sanitized text holds no hour values and redaction makes every contact the
    same [PERSON], so only pseudonymized same-contact answers are supported
    (see docs/utility-impact.md#evidence-supported-answers).
    """
    rows = load(f"final-evidence-utility-{lang}-combined.json")["rows"]
    out = {}
    for v in ("raw", "redacted", "pseudonymized"):
        sel = [r for r in rows if r["variant"] == v]
        exact = sum(r["score"] == "correct" for r in sel)
        if v == "raw":
            supported = exact
        else:
            supported = sum(r["score"] == "correct" and v == "pseudonymized"
                            and r["question_id"] == "same_contact" for r in sel)
        out[v] = (exact, supported, len(sel))
    return out


def chart_utility(theme):
    t = THEMES[theme]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), sharey=True, facecolor=t["surface"])
    names = ["raw", "redacted", "pseudonymized"]
    for ax, (lang, title) in zip(axes, (("en", "English"), ("fi", "Finnish"))):
        style(ax, t)
        ax.xaxis.grid(False)
        ax.yaxis.grid(True, color=t["grid"], linewidth=0.8)
        counts = utility_counts(lang)
        w = 0.36
        for i, v in enumerate(names):
            exact, sup, _ = counts[v]
            ax.bar(i - w / 2 - 0.02, exact, width=w, color=t["s2"])
            ax.bar(i + w / 2 + 0.02, sup, width=w, color=t["s1"])
            ax.text(i - w / 2 - 0.02, exact + 0.2, str(exact), ha="center", fontsize=8.5, color=t["muted"])
            ax.text(i + w / 2 + 0.02, sup + 0.2, str(sup), ha="center", fontsize=8.5, color=t["text"])
        ax.set_xticks(range(3), ["Raw", "Redacted", "Pseudonyms"], color=t["text"])
        ax.set_ylim(0, 10)
        ax.set_yticks([0, 3, 6, 9])
        ax.set_title(title, loc="left", color=t["text"], fontsize=10, fontweight="bold")
    fig.subplots_adjust(top=0.78)
    fig.suptitle("Questions answered correctly, out of 9", x=0.06, ha="left", y=1.02,
                 color=t["text"], fontsize=11.5, fontweight="bold")
    fig.text(0.06, 0.91, "exact-answer score vs. answers the sanitized text can actually support",
             fontsize=8.5, color=t["muted"])
    handles = [plt.Rectangle((0, 0), 1, 1, color=t["s2"]), plt.Rectangle((0, 0), 1, 1, color=t["s1"])]
    leg = fig.legend(handles, ["exact answer", "supported"], loc="upper right", bbox_to_anchor=(0.98, 1.0),
                     ncol=2, frameon=False, fontsize=8.5, handlelength=1.2)
    for txt in leg.get_texts():
        txt.set_color(t["text"])
    save(fig, "rq4-usefulness", theme)


if __name__ == "__main__":
    for theme in THEMES:
        chart_recall(theme)
        chart_reid(theme)
        chart_utility(theme)
