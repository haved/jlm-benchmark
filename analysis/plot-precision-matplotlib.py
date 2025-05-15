#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import numpy as np
import re

def plot_weighted(data, savefig=None):
    data.loc[data["AA"] == "BasicAA", "AA"] = "local"
    data.loc[data["AA"] == "LlvmAA", "AA"] = "LLVM"
    data.loc[data["AA"] == "PointsToGraphAA", "AA"] = "andersen"
    data.loc[data["AA"] == "ChainedAA(PointsToGraphAA,LlvmAA)", "AA"] = "LLVM+andersen"

    # Skip the "only PtG column"
    # data = data[data["AA"] != "andersen"]

    data = data[data["Response"] != "NoAlias"]
    data = data[data["Response"] != "MustAlias"]

    colors = {
        "local": "#CC9600",
        "LLVM": "#636EFA",
        "andersen": "#EF553B",
        "LLVM+andersen": "#00CC96"
    }

    benchmarks = data["Benchmark"].unique()
    AAs = [
        "local",
        "LLVM",
        "andersen",
        "LLVM+andersen"]

    fig, ax = plt.subplots(figsize=(8, 4))
    width = 0.25
    stride = len(AAs) * width + 0.3
    x = np.arange(len(benchmarks)) * stride

    legend_keys = []
    legend_names = []

    for i, aa in enumerate(AAs):
        offset = width * i
        rates = data[data["AA"] == aa].set_index("Benchmark")
        rates = rates.loc[benchmarks, "Rate"]
        rects = ax.bar(x + offset,
                       rates,
                       width,
                       label=aa,
                       facecolor=colors[aa],
                       alpha=0.9,
                       edgecolor="#333",
                       linewidth=1.5,
                       zorder=3)

        legend_keys.append(mlines.Line2D([], [],
                                         marker="s",
                                         markersize=10,
                                         linewidth=0,
                                         color=colors[aa]))
        legend_names.append(aa)

    ax.set_xlim(-width * 1.5, max(x) + width * len(AAs) + width * 0.5)
    benchmark_ticks = [re.sub("[-\\.]", "\n", b, count=1) for b in benchmarks]
    ax.set_xticks(x + width * (len(AAs) - 1) / 2, benchmark_ticks)
    ax.tick_params(axis='x', labelrotation=40)
    for tick in ax.xaxis.get_majorticklabels():
        tick.set_horizontalalignment("right")
        tick.set_verticalalignment("top")
        tick.set_rotation_mode("anchor")

    ax.set_ylabel("Average Store MayAlias %")
    ax.yaxis.label.set_size(13)

    ax.set_yticks(np.arange(0, 16 + 1, 2))
    ax.tick_params(axis='y', labelsize=12)
    ax.grid(which='major', axis='y', zorder=0)

    ax.legend(legend_keys, legend_names,
              loc='best',
              ncols=3,
              fontsize=10,
              frameon=False,
              borderpad=1.55)


    plt.tight_layout(pad=0.05)

    if savefig:
        plt.savefig(savefig)
    plt.show()


def parse_text_weighted(text):
    text = text.strip()
    lines = text.split("\n")

    rows = []

    # The current alias analysis being used
    AA = None
    for line in lines:
        if line == "":
            continue
        parts = line.split(" ")
        if len(parts) == 1:
            AA, = parts
            continue

        # Skip empty parts
        parts = [part for part in parts if part]
        benchmark, no_alias_rate, may_alias_rate, must_alias_rate = parts
        no_alias_rate = float(no_alias_rate)
        may_alias_rate = float(may_alias_rate)
        must_alias_rate = float(must_alias_rate)

        rows.append({
            "AA": AA,
            "Benchmark": benchmark,
            "Response": "MayAlias",
            "Rate": may_alias_rate * 100
            })
        rows.append({
            "AA": AA,
            "Benchmark": benchmark,
            "Response": "MustAlias",
            "Rate": must_alias_rate * 100
            })
        rows.append({
            "AA": AA,
            "Benchmark": benchmark,
            "Response": "NoAlias",
            "Rate": no_alias_rate * 100
            })

    return pd.DataFrame(rows)


CS_NoDedup = """
BasicAA
500.perlbench  0.804925  0.132681   0.062342
502.gcc        0.819753  0.058408   0.121347
505.mcf        0.826400  0.123476   0.050124
507.cactuBSSN  0.891204  0.059418   0.049354
525.x264       0.833818  0.110513   0.055135
526.blender    0.818740  0.077578   0.103156
538.imagick    0.845298  0.069975   0.084445
544.nab        0.842944  0.086891   0.069670
557.xz         0.827778  0.082717   0.088873

LlvmAA
500.perlbench  0.829937  0.107493   0.062518
502.gcc        0.824115  0.053869   0.121523
505.mcf        0.838202  0.111204   0.050594
507.cactuBSSN  0.747390  0.203120   0.049465
525.x264       0.830692  0.113428   0.055347
526.blender    0.820466  0.075790   0.103219
538.imagick    0.837878  0.077217   0.084622
544.nab        0.839827  0.089936   0.069742
557.xz         0.812210  0.098177   0.088982

PointsToGraphAA
500.perlbench  0.825768  0.112106   0.062074
502.gcc        0.818755  0.062096   0.118657
505.mcf        0.842263  0.107673   0.050064
507.cactuBSSN  0.899314  0.051559   0.049103
525.x264       0.838522  0.106056   0.054889
526.blender    0.812926  0.084145   0.102403
538.imagick    0.849984  0.066144   0.083591
544.nab        0.866292  0.063712   0.069501
557.xz         0.825893  0.092460   0.081015

ChainedAA(PointsToGraphAA,LlvmAA)
500.perlbench  0.851657  0.085774   0.062517
502.gcc        0.834760  0.043069   0.121678
505.mcf        0.846968  0.102439   0.050594
507.cactuBSSN  0.901915  0.048595   0.049466
525.x264       0.844632  0.099488   0.055347
526.blender    0.824223  0.072033   0.103219
538.imagick    0.860195  0.054901   0.084622
544.nab        0.868775  0.060988   0.069742
557.xz         0.844598  0.065788   0.088982
"""

data = parse_text_weighted(CS_NoDedup)
plot_weighted(data, savefig="precision.pdf")
