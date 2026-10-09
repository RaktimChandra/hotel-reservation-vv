"""True V-model figure (matplotlib)."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch

for f in font_manager.findSystemFonts():
    if "Inter" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = "Inter"
OUT = Path(__file__).resolve().parents[1] / "docs" / "figures"
BLUE, LBLUE, AQUA, LAQUA, ORANGE, INK, INK2 = "#2a78d6", "#e3eefb", "#1baf7a", "#dcf3ea", "#eb6834", "#0b0b0b", "#52514e"
left = [("Requirements (SRS)", "FR-01..15 · 17 NFRs · RV-01..07"), ("System design", "API contract · state machine"),
        ("Architecture", "layers · SQLite · gateway"), ("Module design", "domain functions")]
right = [("Acceptance testing", "BDD / Gherkin UAT · 4 cases"), ("System testing", "API · security · perf · E2E · 71 cases"),
         ("Integration testing", "service ↔ DB ↔ gateway stub · 31"), ("Unit testing", "BVA · ECP · DT · CEG · WB · 448")]
fig, ax = plt.subplots(figsize=(12, 6.4))
ax.set_xlim(0, 12); ax.set_ylim(-0.6, 5.2); ax.axis("off")
fig.patch.set_facecolor("#fcfcfb")
W, H = 2.8, 0.8
pos_l = [(0.2 + i * 0.8, 4.2 - i * 1.05) for i in range(4)]
pos_r = [(12 - 0.2 - W - i * 0.8, 4.2 - i * 1.05) for i in range(4)]
for (t, s), (x, y) in zip(left, pos_l):
    ax.add_patch(FancyBboxPatch((x, y), W, H, boxstyle="round,pad=0,rounding_size=0.12", fc=LBLUE, ec=BLUE, lw=1.4))
    ax.text(x + W / 2, y + 0.52, t, ha="center", fontsize=11.5, fontweight="bold", color=INK)
    ax.text(x + W / 2, y + 0.2, s, ha="center", fontsize=8.8, color=INK2)
for (t, s), (x, y) in zip(right, pos_r):
    ax.add_patch(FancyBboxPatch((x, y), W, H, boxstyle="round,pad=0,rounding_size=0.12", fc=LAQUA, ec=AQUA, lw=1.4))
    ax.text(x + W / 2, y + 0.52, t, ha="center", fontsize=11.5, fontweight="bold", color=INK)
    ax.text(x + W / 2, y + 0.2, s, ha="center", fontsize=8.8, color=INK2)
for (xl, yl), (xr, yr) in zip(pos_l, pos_r):
    ax.annotate("", xy=(xr - 0.05, yr + H / 2), xytext=(xl + W + 0.05, yl + H / 2),
                arrowprops=dict(arrowstyle="<->", color=ORANGE, lw=1.3, ls="--"))
for i, (xl, yl) in enumerate(pos_l):
    xr = pos_r[i][0]
    lab = "validates — “right product?”" if i == 0 else ("verifies" if i == 3 else "verifies — “product right?”")
    ax.text((xl + W + xr) / 2, yl + H / 2 + 0.1, lab, ha="center", fontsize=8.8, color=ORANGE)
ax.add_patch(FancyBboxPatch((3.9, -0.45), 4.2, 0.8, boxstyle="round,pad=0,rounding_size=0.12", fc="#f1f0ec", ec="#8a8984", lw=1.4))
ax.text(6, -0.12, "Coding  ·  Python · FastAPI · SQLite", ha="center", fontsize=11, fontweight="bold", color=INK)
for i in range(3):
    ax.annotate("", xy=(pos_l[i + 1][0] + 0.4, pos_l[i + 1][1] + H), xytext=(pos_l[i][0] + 0.6, pos_l[i][1]),
                arrowprops=dict(arrowstyle="->", color=INK2, lw=1.2))
    ax.annotate("", xy=(pos_r[i][0] + W - 0.6, pos_r[i][1]), xytext=(pos_r[i + 1][0] + W - 0.4, pos_r[i + 1][1] + H),
                arrowprops=dict(arrowstyle="->", color=INK2, lw=1.2))
ax.annotate("", xy=(3.9, -0.05), xytext=(pos_l[3][0] + 0.8, pos_l[3][1]), arrowprops=dict(arrowstyle="->", color=INK2, lw=1.2))
ax.annotate("", xy=(pos_r[3][0] + W - 0.8, pos_r[3][1]), xytext=(8.1, -0.05), arrowprops=dict(arrowstyle="->", color=INK2, lw=1.2))
ax.set_title("V-model as applied to HRRS — each design level is paired with the test level that checks it",
             loc="left", fontsize=13, fontweight="bold", color=INK)
fig.savefig(OUT / "vmodel.png", dpi=200, bbox_inches="tight", facecolor="#fcfcfb")
