#!/usr/bin/env python3

import pandas as pd
import argparse
import os
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import re
import numpy as np


def calculate_total_query_responses_for_aa(file_data, aa_name):
    """This function is used when considering the total number of alias responses"""
    aa_prefix = aa_name + "-"
    per_program = file_data.groupby("program").sum()

    result = pd.DataFrame({
        "MayAlias": per_program[aa_prefix + "#TotalMayAlias"],
    })

    return result


def plot(data, ylabel, savefig=None):
    """ Takes data in the format
    Benchmark AA        MayAlias
    ========= ========= ====
    505.gcc   BasicAA   475756
    500.perl  BasicAA   493493
    521.blend BasicAA   33282
    ...

    and plots the relative decrease in MayAlias responses for each benchmark
    """
    baseline_aa = "Basic + Type"
    data.loc[data["AA"] == "BasicAA", "AA"] = "local"
    data.loc[data["AA"] == "PointsToGraphAA", "AA"] = "Andersen"
    data.loc[data["AA"] == "LlvmAA", "AA"] = "Basic"
    data.loc[data["AA"] == "LlvmAA+TypeBasedAA", "AA"] = "Basic + Type"
    data.loc[data["AA"] == "LlvmAA+GlobalsAA+TypeBasedAA", "AA"] = "Basic + Type + Global"
    data.loc[data["AA"] == "ChainedAA(PointsToGraphAA,LlvmAA+TypeBasedAA)", "AA"] = "Basic + Type + Andersen"
    data.loc[data["AA"] == "ChainedAA(PointsToGraphAA,LlvmAA+GlobalsAA+TypeBasedAA)", "AA"] = "Basic + Type + Global + Andersen"

    # Create the Rate column
    baseline = data[data["AA"] == baseline_aa].set_index("Benchmark")["MayAlias"]
    data["Rate"] = (1 - data["MayAlias"] / data["Benchmark"].map(baseline)) * 100

    mean_per_aa = data.groupby("AA")["Rate"].mean()
    data = pd.concat([data, pd.DataFrame({
        "Benchmark": "arithmetic\nmean",
        "AA": mean_per_aa.index,
        "Rate": mean_per_aa
        })])
    print("mean_per_aa:", mean_per_aa)

    colors = {
        "local": "#CC9600",
        "Andersen": "#EF553B",
        "Basic + Type": "#636EFA",
        "Basic + Type + Global": "#636EFA",
        "Basic + Type + Andersen": "#EF553B",
        "Basic + Type + Global + Andersen": "#00CC96",
    }

    benchmarks = data["Benchmark"].unique()
    AAs = [
        #"local",
        # "Andersen",
        # "Basic + Type",
        "Basic + Type + Global",
        "Basic + Type + Andersen",
        "Basic + Type + Global + Andersen"
        ]

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
    benchmark_ticks = [re.sub("([-\\.])", "\\1\n", b, count=1) for b in benchmarks]
    ax.set_xticks(x + width * (len(AAs) - 1) / 2, benchmark_ticks)
    ax.tick_params(axis='x', labelrotation=40)
    for tick in ax.xaxis.get_majorticklabels():
        tick.set_horizontalalignment("right")
        tick.set_verticalalignment("top")
        tick.set_rotation_mode("anchor")

    ax.set_ylabel(ylabel)
    ax.yaxis.label.set_size(13)

    ax.set_yticks(np.arange(0, 24+1, 2))
    ax.tick_params(axis='y', labelsize=12)
    ax.grid(which='major', axis='y', zorder=0)

    ax.legend(legend_keys, legend_names,
              loc='best',
              ncols=1,
              fontsize=12,
              frameon=True,
              framealpha=1,
              borderpad=0.35)


    plt.tight_layout(pad=0.05)

    if savefig:
        plt.savefig(savefig)
    plt.show()


def main():
    parser = argparse.ArgumentParser(description='Make figures about analysis precision')
    parser.add_argument('--stats', dest='stats', action='store', required=True,
                        help='Specify the folder for aggregated statistics')
    parser.add_argument('--out', dest='out_dir', action='store', required=True,
                        help='The output folder for plots')
    args = parser.parse_args()

    file_data = pd.read_csv(os.path.join(args.stats, "file_data.csv"), index_col=0)

    print("PrecisionEvaluationMode:", file_data["BasicAA-PrecisionEvaluationMode"].unique())
    print("IsRemovingDuplicatePointers:", file_data["BasicAA-IsRemovingDuplicatePointers"].unique())

    aas = ["LlvmAA", "LlvmAA+GlobalsAA", "LlvmAA+TypeBasedAA", "LlvmAA+GlobalsAA+TypeBasedAA"]
    aas.extend([f"ChainedAA(PointsToGraphAA,{aa})" for aa in aas])
    aas.extend(["PointsToGraphAA"])

    # Contains may alias rates, per benchmark and per AA, as numbers between 0 and 100
    may_alias_rates = []

    for aa in aas:
        result = calculate_total_query_responses_for_aa(file_data, aa)

        may_alias_rates.append(pd.DataFrame({
            "AA": aa,
            "Benchmark": result.index,
            "MayAlias": result["MayAlias"]
        }))

    may_alias_rates = pd.concat(may_alias_rates)

    print(may_alias_rates)

    plot(may_alias_rates, ylabel="% Reduction in MayAlias responses\ncompared to ${\\tt Basic + Type}$", savefig=os.path.join(args.out_dir, f"precision-mayalias-reduction.pdf"))

if __name__ == "__main__":
    main()
