#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import numpy as np
import re

def plot_weighted(data, savefig=None):
    data.loc[data["AA"] == "BasicAA", "AA"] = "local"
    data.loc[data["AA"] == "PointsToGraphAA", "AA"] = "andersen"
    data.loc[data["AA"] == "ChainedAA(PointsToGraphAA,BasicAA)", "AA"] = "both"

    # Skip the "only PtG column"
    # data = data[data["AA"] != "andersen"]

    data = data[data["Response"] != "NoAlias"]
    data = data[data["Response"] != "MustAlias"]

    colors = {
        "local": "#636EFA",
        "andersen": "#EF553B",
        "both": "#00CC96"
    }

    benchmarks = data["Benchmark"].unique()
    AAs = ["local", "andersen", "both"]

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


CS_NoDedup_NoMem2reg_YesEA = """
BasicAA
500.perlbench        0.775177  0.162430   0.062342
502.gcc              0.811340  0.067903   0.120312
505.mcf              0.819263  0.130612   0.050124
507.cactuBSSN        0.890392  0.060230   0.049354
525.x264             0.824669  0.119663   0.055135
526.blender          0.809476  0.081308   0.108698
538.imagick          0.839446  0.080201   0.080107
544.nab              0.838371  0.091464   0.069670
557.xz               0.817447  0.093048   0.088873
emacs-29.4           0.819083  0.068770   0.110984
gdb-15.2             0.842923  0.057178   0.099562
ghostscript-10.04.0  0.850902  0.076731   0.072056
sendmail-8.18.1      0.789630  0.139835   0.069389

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
gdb-15.2             0.857611  0.043010   0.099042
ghostscript-10.04.0  0.860027  0.068240   0.071421
sendmail-8.18.1      0.838615  0.091872   0.068367

ChainedAA(PointsToGraphAA,BasicAA)
500.perlbench        0.826957  0.110650   0.062341
502.gcc              0.829705  0.049396   0.120454
505.mcf              0.843037  0.106839   0.050124
507.cactuBSSN        0.901651  0.048970   0.049355
525.x264             0.841660  0.102672   0.055135
526.blender          0.816747  0.074035   0.108701
538.imagick          0.851403  0.068245   0.080107
544.nab              0.867791  0.062044   0.069670
557.xz               0.841782  0.068714   0.088873
emacs-29.4           0.841451  0.046399   0.110985
gdb-15.2             0.859406  0.040695   0.099562
ghostscript-10.04.0  0.863311  0.064321   0.072056
sendmail-8.18.1      0.844901  0.084558   0.069395
"""

data = parse_text_weighted(CS_NoDedup_NoMem2reg_YesEA)
plot_weighted(data, savefig="precision.pdf")
