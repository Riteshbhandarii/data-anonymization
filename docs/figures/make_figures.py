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
              "grid": "#e4e3df", "s1": "#2a78d6", "s2": "#eb6834", "s3": "#1baf7a",
              "badge_rule": "#e4e3df"},
    "dark": {"surface": "#1a1a19", "text": "#f0efec", "muted": "#c3c2b7",
             "grid": "#34332f", "s1": "#3987e5", "s2": "#d95926", "s3": "#199e70",
             "badge_rule": "#d6d5d0"},
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


LLM_CONFIGS = [  # (configuration in the diagnosis aggregate, label, logo, group)
    ("combined", "combined", "combined", "No LLM"),
    ("qwen-alone", "Qwen 3.5 9B", "qwen", "LLM alone"),
    ("gemma-alone", "Gemma 4 E4B", "gemma", "LLM alone"),
    ("combined + qwen final pass", "combined → Qwen", "qwen", "LLM on the masked text"),
    ("combined + gemma final pass", "combined → Gemma", "gemma", "LLM on the masked text"),
    ("combined ∪ qwen-alone", "combined + Qwen", "qwen", "Both on the original text, merged"),
    ("combined ∪ gemma-alone", "combined + Gemma", "gemma", "Both on the original text, merged"),
]


def llm_rows():
    """Values hidden by any span, per language, for each local configuration."""
    data = {c["configuration"]: c for c in load("contextual-llm-diagnosis-2026-10-20.json")["configurations"]}
    out = []
    for key, label, logo, group in LLM_CONFIGS:
        any_type = data[key]["any_type"]
        per = {lang: (any_type[lang]["covered"], any_type[lang]["planted"]) for lang in ("en", "fi")}
        out.append((label, logo, group, per))
    return out


def badge(name, t):
    """A logo centred on a white rounded tile with a hairline border."""
    from PIL import Image, ImageDraw
    size, inner = 192, 150
    tile = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(tile).rounded_rectangle((2, 2, size - 3, size - 3), radius=40, fill="#ffffff",
                                           outline=t["badge_rule"], width=3)
    logo = Image.open(OUT / "logos" / f"{name}.png").convert("RGBA")
    logo.thumbnail((inner, inner), Image.LANCZOS)
    tile.alpha_composite(logo, ((size - logo.width) // 2, (size - logo.height) // 2))
    return tile


def rounded_barh(ax, y, width, height, color, aspect):
    from matplotlib.patches import FancyBboxPatch
    if width <= 0:
        return
    # Rounding is given in x units; mutation_aspect maps it onto y so corners stay circular.
    radius = min(0.45 * height / aspect, width / 2)
    ax.add_patch(FancyBboxPatch((0, y - height / 2), width, height, linewidth=0, facecolor=color,
                                boxstyle=f"round,pad=0,rounding_size={radius}",
                                mutation_aspect=aspect))


def chart_llm(theme):
    from matplotlib.offsetbox import AnnotationBbox, OffsetImage
    t = THEMES[theme]
    rows = llm_rows()
    fig, ax = plt.subplots(figsize=(7.6, 5.6), facecolor=t["surface"])
    style(ax, t)
    ax.set_yticks([])
    # Layout top to bottom: a group heading, then its rows.
    y, ys, heads, prev = 0.0, [], [], None
    for _, _, group, _ in rows:
        if group != prev:
            y -= 0.55 if prev is None else 0.95
            heads.append((y, group))
            y -= 0.75
            prev = group
        else:
            y -= 1.0
        ys.append(y)
    ymin, ymax = min(ys) - 0.7, 0.3
    ax.set_ylim(ymin, ymax)
    ax.set_xlim(0, 112)
    fig.canvas.draw()
    bbox = ax.get_window_extent()
    aspect = ((ymax - ymin) / bbox.height) / (112 / bbox.width)  # y units per x unit, in pixels
    h = 0.3
    for (label, logo, _, per), yc in zip(rows, ys):
        for lang, off, color, ink in (("en", h / 2 + 0.03, t["s1"], t["text"]),
                                      ("fi", -h / 2 - 0.03, t["s2"], t["muted"])):
            k, n = per[lang]
            rounded_barh(ax, yc + off, 100 * k / n, h, color, aspect)
            ax.text(100 * k / n + 1.2, yc + off, f"{k}/{n}", va="center", fontsize=8, color=ink)
        img = OffsetImage(badge(logo, t), zoom=0.13, resample=True)
        ax.add_artist(AnnotationBbox(img, (-0.335, yc), xycoords=("axes fraction", "data"),
                                     frameon=False, annotation_clip=False))
        ax.text(-0.29, yc, label, transform=ax.get_yaxis_transform(), va="center", ha="left",
                fontsize=9.5, color=t["text"], fontweight="bold" if logo == "combined" else "normal")
    for yh, group in heads:
        ax.text(-0.36, yh, group.upper(), transform=ax.get_yaxis_transform(), va="center",
                fontsize=7, color=t["muted"], fontweight="bold")
        ax.axhline(yh - 0.32, xmin=0, xmax=1, color=t["grid"], linewidth=0.6, clip_on=False)
    ax.set_xticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"])
    ax.set_title("Local LLMs as detectors", loc="left", x=-0.36, color=t["text"],
                 fontsize=12, fontweight="bold", pad=24)
    ax.text(-0.36, 1.035, "identifiers hidden by any detection, same 14 documents, 73 per language",
            transform=ax.transAxes, fontsize=8.5, color=t["muted"])
    handles = [plt.Rectangle((0, 0), 1, 1, color=t["s1"]), plt.Rectangle((0, 0), 1, 1, color=t["s2"])]
    leg = ax.legend(handles, ["English", "Finnish"], loc="lower right", bbox_to_anchor=(1.0, 1.0),
                    ncol=2, frameon=False, fontsize=8.5, handlelength=1.0, borderaxespad=0.3)
    for txt in leg.get_texts():
        txt.set_color(t["text"])
    fig.text(0.142, -0.02, "Earlier scoring also required the right label, which undercounted the LLMs: "
             "Qwen alone scored 94/146 typed, 144/146 here.", fontsize=7.5, color=t["muted"], style="italic")
    fig.subplots_adjust(left=0.38, right=0.97)
    save(fig, "rq2-local-llm", theme)


CTX_CATEGORIES = [("LICENCE", "Licence / permit no."), ("CONTRACT", "Contract / order no."),
                  ("BUSINESS_ID", "Business ID / VAT"), ("PROJECT", "Project code name"),
                  ("SYSTEM", "Internal system name"), ("QUASI", "Job + place clue"),
                  ("HIDDEN", "Detail in notes"), ("STANDARD", "Names, emails, phones")]
CTX_CONFIGS = [("combined", "combined"), ("qwen alone, contextual prompt", "Qwen, contextual prompt"),
               ("combined ∪ qwen alone, contextual prompt", "combined + Qwen, merged")]


def chart_contextual(theme):
    t = THEMES[theme]
    data = {c["configuration"]: c["score"]["test"] for c in load("contextual-llm-2026-10-20.json")["configurations"]}
    colors = [t["s2"], t["s1"], t["s3"]]
    fig, ax = plt.subplots(figsize=(7.6, 5.2), facecolor=t["surface"])
    style(ax, t)
    h, gap = 0.24, 0.03
    rows = CTX_CATEGORIES[::-1]
    for i, (key, _) in enumerate(rows):
        for j, (conf, _) in enumerate(CTX_CONFIGS):
            cat = data[conf]["categories"][key]
            y = i + (1 - j) * (h + gap)
            share = 100 * cat["covered"] / cat["planted"]
            ax.barh(y, share, height=h, color=colors[j])
            ax.text(share + 1, y, f"{cat['covered']}/{cat['planted']}", va="center", fontsize=7.5,
                    color=t["text"] if j == 2 else t["muted"])
    ax.set_yticks(range(len(rows)), [label for _, label in rows], color=t["text"])
    ax.set_xlim(0, 112)
    ax.set_xticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"])
    ax.set_title("What rules miss and a local LLM catches", loc="left", color=t["text"],
                 fontsize=12, fontweight="bold", pad=24)
    ax.text(0, 1.035, "items fully hidden, 18 held-out fictional documents in English and Finnish",
            transform=ax.transAxes, fontsize=8.5, color=t["muted"])
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in colors]
    leg = ax.legend(handles, [label for _, label in CTX_CONFIGS], loc="upper center",
                    bbox_to_anchor=(0.45, -0.08), ncol=3, frameon=False, fontsize=8.5, handlelength=1.0)
    for txt in leg.get_texts():
        txt.set_color(t["text"])
    d = [data[c]["decoys"] for c, _ in CTX_CONFIGS]
    wrong = ", ".join(f"{name} {x['masked']}/{x['total']}" for name, x in zip(("combined", "Qwen", "merged"), d))
    fig.text(0.02, -0.04, f"Look-alikes wrongly hidden (decoys): {wrong}. Same team wrote the corpus and the prompt.",
             fontsize=7.5, color=t["muted"], style="italic")
    save(fig, "rq2-contextual-llm", theme)


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
        chart_llm(theme)
        chart_contextual(theme)
        chart_reid(theme)
        chart_utility(theme)
