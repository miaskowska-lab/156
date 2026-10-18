"""Draw the pipeline diagram -> figures/pipeline.png (matplotlib only, no graphviz needed)."""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

STEPS = [
    ("Forum scrape", "logged in with my\nsession cookie, scraped\n152 submissions (2023-26)\nand 136 PDFs"),
    ("PyMuPDF parse", "spans, font sizes,\nsuperscript flags per page"),
    ("Footnote linker", "superscript n <-> footnote n\n'#tag: justification'\ncontext = last 3 sentences"),
    ("Labelling", "tag -> cornerstone family\n(usage rule + handbook)\nname redaction, masking"),
    ("Features", "bag of words counts /\nTF-IDF (1-2 grams)"),
    ("Models", "Naive Bayes, LogReg\nDecision tree, Linear SVM\nmajority baseline"),
    ("Evaluation", "5-fold CV grouped\nby assignment\naccuracy, macro-F1, hit@3\nfamily consistency"),
]
fig, ax = plt.subplots(figsize=(19, 3.4)); ax.set_xlim(0, 19); ax.set_ylim(0, 3.2); ax.axis("off")
w, gap = 2.45, 0.25
for i, (title, body) in enumerate(STEPS):
    x = 0.15 + i * (w + gap)
    ax.add_patch(FancyBboxPatch((x, 0.5), w, 2.2, boxstyle="round,pad=0.05", fc="#eef3fb" if i % 2 == 0 else "#f7f1e6", ec="#333"))
    ax.text(x + w / 2, 2.45, title, ha="center", va="center", fontsize=11.5, weight="bold")
    ax.text(x + w / 2, 1.45, body, ha="center", va="center", fontsize=8.6)
    if i < len(STEPS) - 1:
        ax.add_patch(FancyArrowPatch((x + w + 0.02, 1.6), (x + w + gap - 0.02, 1.6), arrowstyle="-|>", mutation_scale=14, color="#333"))
ax.text(9.5, 0.15, "Comparison conditions: text view (justification / context / both) x label granularity (family / fine tag) x model x masking x +mentions",
        ha="center", fontsize=9.5, style="italic")
fig.savefig("figures/pipeline.png", dpi=180, bbox_inches="tight"); print("saved figures/pipeline.png")
