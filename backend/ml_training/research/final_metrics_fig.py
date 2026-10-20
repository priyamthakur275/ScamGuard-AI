"""Bar chart of the classifier, the deployed system and learned fusion on the real test set."""
import json, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = pathlib.Path(__file__).parent
plt.rcParams.update({"font.family": "serif", "font.serif": ["Liberation Serif", "Times New Roman", "TeX Gyre Termes", "DejaVu Serif"], "font.size": 10})
r = json.load(open(HERE / "results.json"))["E5_fusion"]["real_test"]
systems = [("Classifier only", r["classifier"], "#9AA0A6"), ("Deployed system", r["hand_fusion"], "#1F2A44"), ("Learned fusion", r["learned_fusion"], "#C0392B")]
metrics = [("Accuracy", "accuracy"), ("Precision", "precision"), ("Recall", "recall"), ("F1-score", "f1")]
fig, ax = plt.subplots(figsize=(6.4, 3.2))
w = 0.26
for k, (name, m, col) in enumerate(systems):
    xs = [i + (k - 1) * w for i in range(len(metrics))]
    vals = [100 * m[key] for _, key in metrics]
    ax.bar(xs, vals, w, label=name, color=col)
    for x, v in zip(xs, vals):
        ax.text(x, v + 0.08, f"{v:.1f}", ha="center", va="bottom", fontsize=7)
ax.set_xticks(range(len(metrics)))
ax.set_xticklabels([m for m, _ in metrics])
ax.set_ylim(95, 99.6)
ax.set_ylabel("%")
ax.legend(loc="upper center", ncol=3, frameon=False, fontsize=8, bbox_to_anchor=(0.5, 1.15))
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
for ext in ("pdf", "png"):
    fig.savefig(HERE / "figures" / f"final_metrics.{ext}", dpi=220, bbox_inches="tight")
print("ok")
