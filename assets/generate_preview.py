"""
Asset Generator: Generates high-resolution dashboard preview for README.
"""

from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_PATH = BASE_DIR / "assets" / "preview.png"


def generate_preview():
    fig = plt.figure(figsize=(14, 8), facecolor="#0e1117")
    gs = fig.add_gridspec(2, 2, hspace=0.35, wspace=0.25)

    # Style settings
    plt.rcParams["text.color"] = "#FAFAFA"
    plt.rcParams["axes.labelcolor"] = "#FAFAFA"
    plt.rcParams["xtick.color"] = "#FAFAFA"
    plt.rcParams["ytick.color"] = "#FAFAFA"

    # Plot 1: Daily Conversion Rate Trends
    ax1 = fig.add_subplot(gs[0, 0], facecolor="#161b22")
    days = np.arange(1, 24)
    ctrl_cr = 12.04 + np.random.normal(0, 0.25, size=23)
    treat_cr = 11.88 + np.random.normal(0, 0.25, size=23)
    ax1.plot(days, ctrl_cr, color="#58a6ff", marker="o", label="Control (Baseline 12.04%)", linewidth=2)
    ax1.plot(days, treat_cr, color="#f0883e", marker="s", label="Treatment (Variant 11.88%)", linewidth=2)
    ax1.set_title("Longitudinal Conversion Rate by Variant", fontsize=12, fontweight="bold", color="#58a6ff")
    ax1.set_xlabel("Experiment Day")
    ax1.set_ylabel("Conversion Rate (%)")
    ax1.legend(loc="upper right", facecolor="#0e1117", edgecolor="gray")
    ax1.grid(True, linestyle="--", alpha=0.3, color="#30363d")

    # Plot 2: Posterior Beta Curves
    ax2 = fig.add_subplot(gs[0, 1], facecolor="#161b22")
    x = np.linspace(11.4, 12.5, 300)
    # Beta PDFs approximated as normals
    pdf_c = np.exp(-0.5 * ((x - 12.039) / 0.085)**2)
    pdf_t = np.exp(-0.5 * ((x - 11.881) / 0.085)**2)
    ax2.plot(x, pdf_c, color="#58a6ff", linewidth=2.5, label="Control Beta(17490, 127786)")
    ax2.fill_between(x, pdf_c, color="#58a6ff", alpha=0.25)
    ax2.plot(x, pdf_t, color="#f0883e", linewidth=2.5, label="Treatment Beta(17265, 128047)")
    ax2.fill_between(x, pdf_t, color="#f0883e", alpha=0.25)
    ax2.set_title("Bayesian Posterior Distributions: P(Control > Treatment) = 90.6%", fontsize=12, fontweight="bold", color="#7ee787")
    ax2.set_xlabel("Conversion Rate (%)")
    ax2.set_ylabel("Posterior Density")
    ax2.legend(loc="upper right", facecolor="#0e1117", edgecolor="gray")
    ax2.grid(True, linestyle="--", alpha=0.3, color="#30363d")

    # Plot 3: Power Analysis MDE Hockey Stick Curve
    ax3 = fig.add_subplot(gs[1, 0], facecolor="#161b22")
    mde = np.linspace(0.5, 6.0, 100)
    req_n = (2.80 / (mde / 100))**2 * 12.04 * (100 - 12.04) / 10000  # simplified sample size formula
    ax3.plot(mde, req_n, color="#bc8cff", linewidth=2.5)
    ax3.scatter([2.83], [145274], color="#ff7b72", s=100, zorder=5, label="Actual Cohort (145k / Arm -> MDE +/-2.83%)")
    ax3.set_title("Pre-Experiment Sizing: MDE vs Required Sample Size", fontsize=12, fontweight="bold", color="#bc8cff")
    ax3.set_xlabel("Minimum Detectable Effect (Relative %)")
    ax3.set_ylabel("Required Users per Arm")
    ax3.legend(loc="upper right", facecolor="#0e1117", edgecolor="gray")
    ax3.grid(True, linestyle="--", alpha=0.3, color="#30363d")

    # Plot 4: KPI Dashboard Card Panel
    ax4 = fig.add_subplot(gs[1, 1], facecolor="#161b22")
    ax4.axis("off")
    ax4.text(0.05, 0.85, "EXPERIMENT KPI SUMMARY", fontsize=13, fontweight="bold", color="#58a6ff")
    ax4.text(0.05, 0.70, "Total Users: 290,584", fontsize=11, color="#FAFAFA")
    ax4.text(0.05, 0.58, "Control CR: 12.039% (95% CI: [11.87%, 12.21%])", fontsize=11, color="#FAFAFA")
    ax4.text(0.05, 0.46, "Treatment CR: 11.881% (95% CI: [11.71%, 12.05%])", fontsize=11, color="#FAFAFA")
    ax4.text(0.05, 0.34, "Relative Lift: -1.31% (Chi2 p = 0.1899)", fontsize=11, color="#ff7b72", fontweight="bold")
    ax4.text(0.05, 0.22, "Bayesian P(Treatment > Control): 9.36%", fontsize=11, color="#ff7b72")
    ax4.text(0.05, 0.08, "VERDICT: DO NOT ROLL OUT (Maintain Control)", fontsize=12, fontweight="bold", color="#f0883e")

    fig.suptitle("A/B Testing & Statistical Experimentation Platform (Google-Grade)", fontsize=16, fontweight="bold", color="#FAFAFA", y=0.98)
    
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT_PATH, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"Generated dashboard preview graphic at: {OUTPUT_PATH}")


if __name__ == "__main__":
    generate_preview()
