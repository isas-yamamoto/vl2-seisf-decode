#!/usr/bin/env python3
"""Generate paper figures: SEISF / VUS format diagrams.

Outputs: docs/figures/fig_{seisf_format,vus_format,seisf_vus_bridge}.{pdf,png,svg}
Run from repo root or any cwd; paths resolve relative to this file.

    python3 docs/figures/generate_format_figures.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = Path(__file__).resolve().parent

C = {
    "header": "#2C5F6E",
    "science": "#C45C26",
    "pad": "#8A8A80",
    "cassette": "#1A3A4A",
    "record": "#3D6B4F",
    "half": "#5B6B7A",
    "word": "#4A6A8A",
    "bitpage": "#B8860B",
    "text": "#1A1A1A",
    "muted": "#555555",
    "bg": "#FFFFFF",
    "boxedge": "#222222",
    "light_s": "#F5E0D4",
    "light_r": "#DCE8E0",
    "light_w": "#DDE5EE",
    "light_b": "#F5ECD0",
}


def style_ax(ax):
    ax.axis("off")
    ax.set_facecolor(C["bg"])


def rounded(ax, x, y, w, h, fc, ec=None, lw=1.0, z=1):
    p = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        linewidth=lw,
        edgecolor=ec or C["boxedge"],
        facecolor=fc,
        zorder=z,
    )
    ax.add_patch(p)
    return p


def labeled_bar(ax, x, y, w, h, segments, fs=8):
    cx = x
    for frac, color, label in segments:
        sw = w * frac
        rounded(ax, cx, y, max(sw - 0.02, 0.05), h, color, lw=0.8)
        if label and sw > 0.35:
            ax.text(
                cx + sw / 2,
                y + h / 2,
                label,
                ha="center",
                va="center",
                fontsize=fs,
                color="white" if _dark(color) else C["text"],
                fontweight="medium",
                zorder=3,
            )
        cx += sw


def _dark(hexcolor: str) -> bool:
    h = hexcolor.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (r * 0.299 + g * 0.587 + b * 0.114) < 140


def fig_seisf():
    fig = plt.figure(figsize=(7.2, 8.6), dpi=200, facecolor=C["bg"])
    ax = fig.add_axes([0.04, 0.03, 0.92, 0.94])
    style_ax(ax)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 12.2)

    ax.text(
        5,
        11.85,
        "SEISF / DLT cassette layout (Viking Lander 2)",
        ha="center",
        va="top",
        fontsize=12,
        fontweight="bold",
        color=C["text"],
    )
    ax.text(
        5,
        11.45,
        "Scrambled SEISF instrument buffer as cassettes (UTIG vkg.1–29)",
        ha="center",
        va="top",
        fontsize=8.5,
        color=C["muted"],
    )

    y = 10.5
    ax.text(
        0.35,
        y + 0.45,
        "(A) UTIG cassette file (one subgroup)",
        ha="left",
        fontsize=9.5,
        fontweight="bold",
        color=C["cassette"],
    )
    labeled_bar(
        ax,
        0.4,
        y - 0.15,
        9.2,
        0.55,
        [
            (1000 / (1000 + 10752), C["header"], "subgroup\nheader\n1000 B"),
            (
                10752 / (1000 + 10752),
                C["record"],
                "data records × N\n10752 or 10764 B each",
            ),
        ],
        fs=7.2,
    )
    ax.text(
        0.4,
        y - 0.55,
        "Header bytes 0–1: tape_id=5 · 2–7: ASCII “DLT…” · 8–9: file no. · 10–11: record_length",
        fontsize=7,
        color=C["muted"],
    )

    # (B) visual row + formula on a separate line (avoid overlap with halfword box)
    ax.text(
        0.35,
        9.55,
        "(B) Body packing: sequential 18-bit halfwords",
        ha="left",
        va="bottom",
        fontsize=9.5,
        fontweight="bold",
        color=C["half"],
    )
    cell_w, cell_h = 0.95, 0.55
    row_y = 8.72
    x0 = 1.2
    for i, lab in enumerate(["b0 · 6 bits", "b1 · 6 bits", "b2 · 6 bits"]):
        rounded(ax, x0 + i * (cell_w + 0.12), row_y, cell_w, cell_h, C["light_w"], lw=0.8)
        ax.text(
            x0 + i * (cell_w + 0.12) + cell_w / 2,
            row_y + cell_h / 2,
            lab,
            ha="center",
            va="center",
            fontsize=7,
        )
    arrow_x0 = x0 + 3 * (cell_w + 0.12) + 0.08
    arrow_x1 = arrow_x0 + 0.5
    ax.annotate(
        "",
        xy=(arrow_x1, row_y + cell_h / 2),
        xytext=(arrow_x0, row_y + cell_h / 2),
        arrowprops=dict(arrowstyle="-|>", color=C["muted"], lw=1.1),
    )
    hw_x = arrow_x1 + 0.12
    hw_w = 2.7
    rounded(ax, hw_x, row_y, hw_w, cell_h, C["half"], lw=0.9)
    ax.text(
        hw_x + hw_w / 2,
        row_y + cell_h / 2,
        "halfword (18 bits)  ·  MSB … LSB",
        ha="center",
        va="center",
        fontsize=7.2,
        color="white",
    )
    ax.text(
        5.0,
        8.35,
        "body[i : i+3]  →  h = (b0<<12) | (b1<<6) | b2",
        ha="center",
        va="top",
        fontsize=7.5,
        color=C["muted"],
        family="monospace",
    )

    y = 6.55
    ax.text(
        0.35,
        y + 0.7,
        "(C) Logical SEISF frame  —  224 halfwords  =  672 cassette bytes",
        ha="left",
        fontsize=9.5,
        fontweight="bold",
        color=C["header"],
    )
    labeled_bar(
        ax,
        0.4,
        y,
        9.2,
        0.65,
        [
            (36 / 224, C["header"], "header\n36 HW\n(= 108 B)"),
            (188 / 224, C["science"], "science region\n188 halfwords  (scrambled)"),
        ],
        fs=7.5,
    )
    ax.text(
        0.4,
        y - 0.4,
        "Frame pitch 224 HW · first base on gold reel ≈ halfword index 170 of record body",
        fontsize=7,
        color=C["muted"],
    )
    ax.text(
        0.4,
        y - 0.7,
        "Shared eng. header fields (year, DOY, …) match VUS 108-byte prefix after unpack.",
        fontsize=7,
        color=C["muted"],
    )

    y = 4.7
    ax.text(
        0.35,
        y + 0.95,
        "(D) Science unscramble (production) — from halfword pairs to 2048-bit buffer",
        ha="left",
        fontsize=9.5,
        fontweight="bold",
        color=C["science"],
    )
    steps = [
        (0.4, "pair\n36 bits"),
        (2.3, "drop top\n4 bits"),
        (4.2, "32 bits\nkept"),
        (6.1, "offset\n15 bits"),
        (8.0, "take\n2048"),
    ]
    for x, lab in steps:
        rounded(ax, x, y + 0.15, 1.7, 0.65, C["light_s"], lw=0.8)
        ax.text(x + 0.85, y + 0.47, lab, ha="center", va="center", fontsize=7.2)
    for x0, x1 in [(2.1, 2.3), (4.0, 4.2), (5.9, 6.1), (7.8, 8.0)]:
        ax.annotate(
            "",
            xy=(x1, y + 0.47),
            xytext=(x0, y + 0.47),
            arrowprops=dict(arrowstyle="-|>", color=C["science"], lw=1.0),
        )
    ax.text(
        0.4,
        y - 0.2,
        "Unscramble with PD7400072 page order using Q = matv (MAP probe on first data pair).",
        fontsize=7.2,
        color=C["muted"],
    )
    ax.text(
        0.4,
        y - 0.5,
        "Four 512-bit pages → sequential 2048-bit science (same region as VUS bits 648…2695).",
        fontsize=7.2,
        color=C["muted"],
    )

    y = 2.55
    ax.text(
        0.35,
        y + 0.85,
        "(E) 2048-bit science after unscramble (4 × 512-bit pages)",
        ha="left",
        fontsize=9.5,
        fontweight="bold",
        color=C["bitpage"],
    )
    labeled_bar(
        ax,
        0.4,
        y + 0.1,
        9.2,
        0.6,
        [
            (0.25, "#8B6914", "page 0\n512 b"),
            (0.25, "#A67C1A", "page 1\n512 b"),
            (0.25, "#B8860B", "page 2\n512 b"),
            (0.25, "#C9A227", "page 3\n512 b"),
        ],
        fs=7.5,
    )
    rounded(ax, 0.4, 0.55, 9.2, 1.4, "#F7F7F4", lw=0.6)
    ax.text(0.6, 1.65, "Record boundary note", fontsize=8, fontweight="bold", color=C["text"])
    ax.text(
        0.6,
        0.85,
        "A frame header near the end of a 10752 B record may need science halfwords from the next\n"
        "physical record. Decoder performs halfword lookahead across record edges.",
        fontsize=7.2,
        color=C["muted"],
        va="center",
    )

    for ext in ("pdf", "png", "svg"):
        kw = {"bbox_inches": "tight"}
        if ext == "png":
            kw["dpi"] = 220
        fig.savefig(OUT / f"fig_seisf_format.{ext}", **kw)
    plt.close(fig)


def fig_vus():
    fig = plt.figure(figsize=(7.2, 8.6), dpi=200, facecolor=C["bg"])
    ax = fig.add_axes([0.04, 0.03, 0.92, 0.94])
    style_ax(ax)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 12.2)

    ax.text(
        5,
        11.85,
        "VUS / USEIS cassette layout (Viking Lander 2)",
        ha="center",
        va="top",
        fontsize=12,
        fontweight="bold",
        color=C["text"],
    )
    ax.text(
        5,
        11.45,
        "Ground-processed frames — dual-archive ground truth (UTIG vkg.47–56)",
        ha="center",
        va="top",
        fontsize=8.5,
        color=C["muted"],
    )

    y = 10.5
    ax.text(
        0.35,
        y + 0.45,
        "(A) UTIG cassette file (one subgroup)",
        ha="left",
        fontsize=9.5,
        fontweight="bold",
        color=C["cassette"],
    )
    labeled_bar(
        ax,
        0.4,
        y - 0.15,
        9.2,
        0.55,
        [
            (1000 / (1000 + 11250), C["header"], "subgroup\nheader\n1000 B"),
            (
                11250 / (1000 + 11250),
                C["record"],
                "data records × N\n11250 B each  (= 25 × 450 B)",
            ),
        ],
        fs=7.2,
    )
    ax.text(
        0.4,
        y - 0.55,
        "Header tape label ASCII “VUS…” · record_length = 11250",
        fontsize=7,
        color=C["muted"],
    )

    y = 8.65
    ax.text(
        0.35,
        y + 0.55,
        "(B) One physical record = 25 consecutive VUS frames",
        ha="left",
        fontsize=9.5,
        fontweight="bold",
        color=C["record"],
    )
    fw = 1.05
    for i in range(5):
        rounded(
            ax,
            0.4 + i * (fw + 0.08),
            y - 0.05,
            fw,
            0.5,
            C["light_r"] if i % 2 == 0 else C["light_w"],
            lw=0.7,
        )
        ax.text(
            0.4 + i * (fw + 0.08) + fw / 2,
            y + 0.2,
            f"f{i}\n450 B",
            ha="center",
            va="center",
            fontsize=7,
        )
    ax.text(
        0.4 + 5 * (fw + 0.08) + 0.15,
        y + 0.2,
        "···  f24",
        ha="left",
        va="center",
        fontsize=8,
        color=C["muted"],
    )
    ax.text(
        0.4,
        y - 0.45,
        "Frame index advances by 450 B within the concatenated record body.",
        fontsize=7,
        color=C["muted"],
    )

    y = 6.85
    ax.text(
        0.35,
        y + 0.75,
        "(C) One VUS frame  —  75 × 36-bit words  =  450 bytes (6-bit units)",
        ha="left",
        fontsize=9.5,
        fontweight="bold",
        color=C["word"],
    )
    labeled_bar(
        ax,
        0.4,
        y,
        9.2,
        0.65,
        [
            (108 / 450, C["header"], "header 108 B\n(18 × 36-bit words)"),
            (342 / 450, C["science"], "remainder 342 B\n(holds packed science + status)"),
        ],
        fs=7.5,
    )
    ax.text(
        0.4,
        y - 0.4,
        "On media: each 36-bit word = six 6-bit cells (one byte each, low 6 bits used).",
        fontsize=7,
        color=C["muted"],
    )
    ax.text(
        0.4,
        y - 0.7,
        "Halfword view of header: 36 × 18-bit halfwords — same eng. fields as SEISF header.",
        fontsize=7,
        color=C["muted"],
    )

    y = 4.55
    ax.text(
        0.35,
        y + 1.05,
        "(D) Logical 2700-bit stream (make_bit_stream / vusinfo layout)",
        ha="left",
        fontsize=9.5,
        fontweight="bold",
        color=C["bitpage"],
    )
    labeled_bar(
        ax,
        0.4,
        y + 0.2,
        9.2,
        0.7,
        [
            (648 / 2700, C["header"], "pre-science\nbits 0…647\n(648 bits)"),
            (
                2048 / 2700,
                C["science"],
                "instrument science buffer\nbits 648…2695   (2048 bits)",
            ),
            (4 / 2700, C["pad"], ""),
        ],
        fs=7,
    )
    ax.text(9.35, y + 0.55, "4 b", ha="center", va="center", fontsize=6, color=C["muted"])
    ax.text(
        0.4,
        y - 0.25,
        "Science offset = (word 19 − 1) × 36 = 648.  The production unscramble injects recovered SEISF bits into this region.",
        fontsize=7.2,
        color=C["muted"],
    )
    ax.text(
        0.4,
        y - 0.55,
        "Command / mode / GCSC and amplitude blocks are parsed from this stream (vusinfo).",
        fontsize=7.2,
        color=C["muted"],
    )

    y = 2.55
    ax.text(
        0.35,
        y + 0.8,
        "(E) Science buffer pages (instrument DRAM readout order inverted on ground)",
        ha="left",
        fontsize=9.5,
        fontweight="bold",
        color=C["science"],
    )
    labeled_bar(
        ax,
        0.4,
        y + 0.05,
        9.2,
        0.6,
        [
            (0.25, "#8B6914", "512 b"),
            (0.25, "#A67C1A", "512 b"),
            (0.25, "#B8860B", "512 b"),
            (0.25, "#C9A227", "512 b"),
        ],
        fs=7.5,
    )
    ax.text(
        0.4,
        y - 0.35,
        "On VUS this 2048-bit region is already sequential.  On SEISF it is scrambled until unscrambled.",
        fontsize=7.2,
        color=C["muted"],
    )

    rounded(ax, 0.4, 0.4, 9.2, 1.45, "#F7F7F4", lw=0.6)
    ax.text(0.6, 1.55, "Validation role", fontsize=8, fontweight="bold", color=C["text"])
    ax.text(
        0.6,
        0.75,
        "Header-matched pairs (same year/DOY/GCSC) let the production unscramble assert bit identity: 2048/2048 residual 0\n"
        "and 450-byte frame equality on gold cases (e.g. GCSC = 125078, year/DOY 1976/249).",
        fontsize=7.2,
        color=C["muted"],
        va="center",
    )

    for ext in ("pdf", "png", "svg"):
        kw = {"bbox_inches": "tight"}
        if ext == "png":
            kw["dpi"] = 220
        fig.savefig(OUT / f"fig_vus_format.{ext}", **kw)
    plt.close(fig)


def fig_bridge():
    fig = plt.figure(figsize=(7.2, 3.8), dpi=200, facecolor=C["bg"])
    ax = fig.add_axes([0.04, 0.08, 0.92, 0.84])
    style_ax(ax)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)

    ax.text(
        5,
        4.7,
        "Dual-archive correspondence (logical view)",
        ha="center",
        fontsize=11,
        fontweight="bold",
        color=C["text"],
    )

    rounded(ax, 0.3, 1.2, 2.8, 2.8, C["light_s"], lw=1.0)
    ax.text(1.7, 3.7, "SEISF frame", ha="center", fontsize=9, fontweight="bold", color=C["science"])
    ax.text(1.7, 3.25, "224 halfwords", ha="center", fontsize=8, color=C["muted"])
    rounded(ax, 0.5, 2.5, 2.4, 0.45, C["header"], lw=0.6)
    ax.text(1.7, 2.72, "36 HW header", ha="center", va="center", fontsize=7.5, color="white")
    rounded(ax, 0.5, 1.5, 2.4, 0.85, C["science"], lw=0.6)
    ax.text(
        1.7,
        1.92,
        "scrambled\nscience HW",
        ha="center",
        va="center",
        fontsize=7.5,
        color="white",
    )

    rounded(ax, 3.5, 1.85, 3.0, 1.5, C["light_b"], lw=1.0)
    ax.text(5.0, 3.05, "unscramble", ha="center", fontsize=9, fontweight="bold", color=C["bitpage"])
    ax.text(
        5.0,
        2.35,
        "pair-36 · drop 4\noff=15 · Q=matv\n+ page inverse\n+ record lookahead",
        ha="center",
        va="center",
        fontsize=7,
        color=C["text"],
    )

    ax.annotate(
        "",
        xy=(3.5, 2.6),
        xytext=(3.1, 2.6),
        arrowprops=dict(arrowstyle="-|>", color=C["muted"], lw=1.3),
    )
    ax.annotate(
        "",
        xy=(6.9, 2.6),
        xytext=(6.5, 2.6),
        arrowprops=dict(arrowstyle="-|>", color=C["muted"], lw=1.3),
    )

    rounded(ax, 6.9, 1.2, 2.8, 2.8, C["light_r"], lw=1.0)
    ax.text(8.3, 3.7, "VUS frame", ha="center", fontsize=9, fontweight="bold", color=C["record"])
    ax.text(8.3, 3.25, "75 words · 450 B", ha="center", fontsize=8, color=C["muted"])
    rounded(ax, 7.1, 2.5, 2.4, 0.45, C["header"], lw=0.6)
    ax.text(8.3, 2.72, "108 B header", ha="center", va="center", fontsize=7.5, color="white")
    rounded(ax, 7.1, 1.5, 2.4, 0.85, C["science"], lw=0.6)
    ax.text(
        8.3,
        1.92,
        "bits 648…\n2048 sequential",
        ha="center",
        va="center",
        fontsize=7.5,
        color="white",
    )

    ax.text(
        5,
        0.55,
        "Shared header bytes · bit-exact science region under matched GCSC/year/DOY",
        ha="center",
        fontsize=7.5,
        color=C["muted"],
    )

    for ext in ("pdf", "png", "svg"):
        kw = {"bbox_inches": "tight"}
        if ext == "png":
            kw["dpi"] = 220
        fig.savefig(OUT / f"fig_seisf_vus_bridge.{ext}", **kw)
    plt.close(fig)


def main():
    fig_seisf()
    fig_vus()
    fig_bridge()
    print("Wrote figures to", OUT)


if __name__ == "__main__":
    main()
