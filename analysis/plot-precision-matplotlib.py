#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import numpy as np
import re

def plot_weighted(data, savefig=None):
    data.loc[data["AA"] == "BasicAA", "AA"] = "local"
    data.loc[data["AA"] == "PointsToGraphAA", "AA"] = "andersen"
    data.loc[data["AA"] == "ChainedAA(PointsToGraphAA,BasicAA)", "AA"] = "local+andersen"

    # Skip the "only PtG column"
    # data = data[data["AA"] != "andersen"]

    data = data[data["Response"] != "NoAlias"]
    data = data[data["Response"] != "MustAlias"]

    colors = {
        "LLVM": "#636EFA",
        "local": "#CC9600",
        "andersen": "#EF553B",
        "local+andersen": "#00CC96"
    }

    benchmarks = data["Benchmark"].unique()
    AAs = [
        "LLVM",
        "local",
        "andersen",
        "local+andersen"]

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
LLVM
500.perlbench        0.829991  0.107456   0.062502
502.gcc              0.820241  0.058842   0.120472
505.mcf              0.838202  0.111204   0.050594
507.cactuBSSN        0.747390  0.203120   0.049465
525.x264             0.830692  0.113428   0.055347
526.blender          0.817635  0.073085   0.108764
538.imagick          0.834604  0.084890   0.080262
544.nab              0.839827  0.089936   0.069741
557.xz               0.812210  0.098177   0.088982
emacs-29.4           0.839675  0.048021   0.111139
gdb-15.2             0.834699  0.070888   0.093895
ghostscript-10.04.0  0.861872  0.065586   0.072231
sendmail-8.18.1      0.842777  0.085923   0.070154

BasicAA
500.perlbench        0.804925  0.132681   0.062342
502.gcc              0.821669  0.057573   0.120312
505.mcf              0.826400  0.123476   0.050124
507.cactuBSSN        0.891204  0.059418   0.049354
525.x264             0.833818  0.110513   0.055135
526.blender          0.816331  0.074454   0.108698
538.imagick          0.844291  0.075357   0.080107
544.nab              0.842944  0.086891   0.069670
557.xz               0.827778  0.082717   0.088873
emacs-29.4           0.831961  0.055891   0.110984
gdb-15.2             0.830937  0.074817   0.093727
ghostscript-10.04.0  0.859719  0.067917   0.072053
sendmail-8.18.1      0.803455  0.126010   0.069389

PointsToGraphAA
500.perlbench        0.825768  0.112106   0.062074
502.gcc              0.818884  0.063151   0.117519
505.mcf              0.842263  0.107673   0.050064
507.cactuBSSN        0.899314  0.051559   0.049103
525.x264             0.838522  0.106056   0.054889
526.blender          0.809597  0.082438   0.107449
538.imagick          0.848207  0.072221   0.079327
544.nab              0.866292  0.063712   0.069501
557.xz               0.825893  0.092460   0.081015
emacs-29.4           0.829795  0.060836   0.108205
gdb-15.2             0.837637  0.068592   0.093253
ghostscript-10.04.0  0.860026  0.068246   0.071417
sendmail-8.18.1      0.838615  0.091872   0.068367

ChainedAA(PointsToGraphAA,BasicAA)
500.perlbench        0.851109  0.086499   0.062341
502.gcc              0.835144  0.043957   0.120454
505.mcf              0.847695  0.102182   0.050124
507.cactuBSSN        0.901991  0.048629   0.049355
525.x264             0.844882  0.099450   0.055135
526.blender          0.821750  0.069033   0.108701
538.imagick          0.853977  0.065671   0.080107
544.nab              0.868924  0.060911   0.069670
557.xz               0.844892  0.065603   0.088873
emacs-29.4           0.849122  0.038729   0.110985
gdb-15.2             0.845273  0.060481   0.093728
ghostscript-10.04.0  0.869608  0.058028   0.072053
sendmail-8.18.1      0.856818  0.072641   0.069395
"""

data = parse_text_weighted(CS_NoDedup)
plot_weighted(data, savefig="precision.pdf")
