#!/usr/bin/env python3

import pandas as pd
import argparse
import os
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import re
import numpy as np

def print_average_points_to_external_info(file_data):
    # Only includes PointerObjects marked "CanPoint"
    pointer_objects_point_to_external = file_data["#PointsToExternalRelations"]
    pointer_objects_can_point = (
        file_data["#MemoryPointerObjectsCanPoint"] + file_data["#RegisterPointerObjects"])

    rate = pointer_objects_point_to_external.sum() / pointer_objects_can_point.sum()

    print(f"Percentage of pointers that may point to external: {rate*100:.2f}%")


def calculate_average_for_aa(aaName):
    aaPrefix = aaName + "-"

    module_num_clobbers = file_data[aaPrefix + "ModuleNumClobbers"]

    clobber_average_no_alias = file_data[aaPrefix + "ClobberAverageNoAlias"].fillna(0)
    clobber_average_may_alias = file_data[aaPrefix + "ClobberAverageMayAlias"].fillna(0)
    clobber_average_must_alias = file_data[aaPrefix + "ClobberAverageMustAlias"].fillna(0)

    # Create a column of total weighted response ratios
    file_data[aaPrefix + "CA_NoAlias"] = module_num_clobbers * clobber_average_no_alias
    file_data[aaPrefix + "CA_MayAlias"] = module_num_clobbers * clobber_average_may_alias
    file_data[aaPrefix + "CA_MustAlias"] = module_num_clobbers * clobber_average_must_alias

    # Calculate weighted average per program
    per_program = file_data.groupby("program").sum()
    program_no_alias = per_program[aaPrefix + "CA_NoAlias"] / per_program[aaPrefix + "ModuleNumClobbers"]
    program_may_alias = per_program[aaPrefix + "CA_MayAlias"] / per_program[aaPrefix + "ModuleNumClobbers"]
    program_must_alias = per_program[aaPrefix + "CA_MustAlias"] / per_program[aaPrefix + "ModuleNumClobbers"]

    res = pd.DataFrame({
        "NoAlias": program_no_alias,
        "MayAlias": program_may_alias,
        "MustAlias": program_must_alias
    })

    # Create an "all"-column weighted by the number of clobbers in each program
    res.loc["all", "NoAlias"] = file_data[aaPrefix + "CA_NoAlias"].sum() / module_num_clobbers.sum()
    res.loc["all", "MayAlias"] = file_data[aaPrefix + "CA_MayAlias"].sum() / module_num_clobbers.sum()
    res.loc["all", "MustAlias"] = file_data[aaPrefix + "CA_MustAlias"].sum() / module_num_clobbers.sum()

    return res


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
    505.gcc   BasicAA   14.2
    505.gcc   BasicAA    9.8
    ...

    and plots the MayAlias rate for each benchmark
    """
    data.loc[data["AA"] == "BasicAA", "AA"] = "local"
    data.loc[data["AA"] == "LlvmAA", "AA"] = "BasicAA"
    data.loc[data["AA"] == "PointsToGraphAA", "AA"] = "Andersen"
    data.loc[data["AA"] == "ChainedAA(PointsToGraphAA,LlvmAA)", "AA"] = "Andersen + BasicAA"

    colors = {
        "local": "#CC9600",
        "BasicAA": "#636EFA",
        "Andersen": "#EF553B",
        "Andersen + BasicAA": "#00CC96"
    }

    benchmarks = data["Benchmark"].unique()
    AAs = [
        #"local",
        "BasicAA",
        "Andersen",
        "Andersen + BasicAA"
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

    ax.set_yticks(np.arange(0, 28 + 1, 2))
    ax.tick_params(axis='y', labelsize=12)
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

    print_average_points_to_external_info(file_data)

    aas = ["LlvmAA", "PointsToGraphAA", "ChainedAA(PointsToGraphAA,LlvmAA)"]

    # Contains may alias rates, per benchmark and per AA, as numbers between 0 and 100
    may_alias_rates = []

    for aa in aas:
        result = calculate_total_query_responses_for_aa(file_data, aa)
        print("For alias analysis called:", aa)
        print(result)
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

        may_alias_rates.append(pd.DataFrame({
            "AA": aa,
            "Benchmark": "arithmetic\nmean",
            "Rate": may_rate.mean()
        }, index=[0]))

    may_alias_rates = pd.concat(may_alias_rates)

    plot(may_alias_rates, ylabel="MayAlias Response %", savefig=os.path.join(args.out_dir, "precision.pdf"))

    print("mean MayAlias rates using different AAs:")
    print(may_alias_rates[may_alias_rates["Benchmark"] == "aritmetic\nmean"])

if __name__ == "__main__":
    main()
