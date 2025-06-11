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
        "NoAlias": per_program[aa_prefix + "#TotalNoAlias"],
        "MayAlias": per_program[aa_prefix + "#TotalMayAlias"],
        "MustAlias": per_program[aa_prefix + "#TotalMustAlias"]
                  })

    result["MayRate"] = result["MayAlias"] / result.sum(axis=1)

    return result


def plot(data, ylabel, savefig=None):
    """ Takes data in the format
    Benchmark AA        Rate
    ========= ========= ====
    505.gcc   BasicAA   76.0
    500.perl  BasicAA   14.2
    521.blend BasicAA    9.8
    ...

    and plots the MayAlias rate for each LLVM AA configuration, with and without Andersen
    """

    colors = ["#CC9600", "#EF553B"]

    llvm_configs = ["LlvmAA" , "LlvmAA+GlobalsAA", "LlvmAA+TypeBasedAA", "LlvmAA+GlobalsAA+TypeBasedAA"]

    bars = [
        lambda llvm: llvm,
        lambda llvm: f"ChainedAA(PointsToGraphAA,{llvm})"
    ]

    fig, ax = plt.subplots(figsize=(8, 4))
    width = 0.25
    stride = len(bars) * width + 0.3
    x = np.arange(len(llvm_configs)) * stride

    legend_keys = []
    legend_names = ["LLVM", "LLVM+Andersen"]

    for i, bar in enumerate(bars):
        offset = width * i

        aas = [bar(c) for c in llvm_configs]
        rates = [data[data["AA"] == aa]["Rate"].mean() for aa in aas]

        rects = ax.bar(x + offset,
                       rates,
                       width,
                       label=legend_names[i],
                       facecolor=colors[i],
                       alpha=0.9,
                       edgecolor="#333",
                       linewidth=1.5,
                       zorder=3)

        legend_keys.append(mlines.Line2D([], [],
                                         marker="s",
                                         markersize=10,
                                         linewidth=0,
                                         color=colors[i]))


    ax.set_xlim(-width * 1.5, max(x) + width * len(bars) + width * 0.5)
    ticks = llvm_configs
    ax.set_xticks(x + width * (len(bars) - 1) / 2, llvm_configs)
    ax.tick_params(axis='x', labelrotation=40)
    for tick in ax.xaxis.get_majorticklabels():
        tick.set_horizontalalignment("right")
        tick.set_verticalalignment("top")
        tick.set_rotation_mode("anchor")

    ax.set_ylabel(ylabel)
    ax.yaxis.label.set_size(13)

    # ax.set_yticks(np.arange(0, 28 + 1, 2))
    # ax.tick_params(axis='y', labelsize=12)
    ax.grid(which='major', axis='y', zorder=0)

    ax.legend(legend_keys, legend_names,
              loc='best',
              ncols=3,
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

    # Contains may alias rates, per benchmark and per AA, as numbers between 0 and 100
    may_alias_rates = []

    for aa in aas:
        result = calculate_total_query_responses_for_aa(file_data, aa)
        print("For alias analysis called:", aa)
        print(result)
        # print("Average clobber:")
        # print(calculate_average_for_aa(file_data, aa))
        print("Time spent on alias queries:",
          file_data[aa + "-PrecisionEvaluationTimer[ns]"].sum() / 1.e9, "seconds")
        print()

        total = result["NoAlias"] + result["MayAlias"] + result["MustAlias"]
        may_rate = result["MayAlias"] / total * 100

        may_alias_rates.append(pd.DataFrame({
            "AA": aa,
            "Benchmark": result.index,
            "Rate": may_rate
        }))

        #may_alias_rates.append(pd.DataFrame({
        #    "AA": aa,
        #    "Benchmark": "arithmetic\nmean",
        #    "Rate": may_rate.mean()
        #}, index=[0]))

    may_alias_rates = pd.concat(may_alias_rates)

    plot(may_alias_rates, ylabel="MayAlias Response %", savefig=os.path.join(args.out_dir, "precision-llvms.pdf"))

if __name__ == "__main__":
    main()
