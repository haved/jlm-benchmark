#!/usr/bin/env python3
import os
import os.path
import sys
import shutil
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
import re

def get_memory_node_counts(suffix):
    return [
        "#TotalAllocaState" + suffix,
        "#TotalMallocState" + suffix,
        "#TotalDeltaState" + suffix,
        "#TotalImportState" + suffix,
        "#TotalLambdaState" + suffix,
        "#TotalExternalState" + suffix,
        "#TotalNonEscapedState" + suffix,
        "#MaxMemoryState" + suffix,
        "#MaxNonEscapedMemoryState" + suffix,
    ]

# For each statistic, this dict contains values to keep
# If the entry is a tuple (name, rename), the statistic called `name` will be kept, but be called `rename`
KEEP_METRICS = {
    "AndersenAnalysis": [
        "#RvsdgNodes",
        "#PointsToGraphAllocaNodes", "#PointsToGraphMallocNodes", "#PointsToGraphDeltaNodes", "#PointsToGraphImportNodes", "#PointsToGraphLambdaNodes",
        "#PointsToGraphMemoryNodes", "#PointsToGraphRegisterNodes", "#PointsToGraphEscapedNodes", ("AnalysisTimer[ns]", "AndersenAnalysisTimer[ns]")
    ],
    "MemoryStateEncoder": [
        "#IntraProceduralRegions",
        *get_memory_node_counts("Arguments"),
        "#LoadOperations",
        *get_memory_node_counts("sThroughLoad"),
        "#StoreOperations",
        *get_memory_node_counts("sThroughStore"),
        "#CallEntryMergeOperations",
        *get_memory_node_counts("sIntoCallEntryMerge"),
        ("Time[ns]", "MemoryStateEncodinTime[ns]")
    ]
}

# Populate a direct mapping from (statistic, metric) to new metric name
KEEP_MAP = {}
for stat, metrics in KEEP_METRICS.items():
    for metric in metrics:
        if isinstance(metric, tuple):
            name, rename = metric
            KEEP_MAP[(stat, name)] = rename
        else:
            KEEP_MAP[(stat, metric)] = metric

def extract_file_data(folder):
    file_datas = []

    for fil in os.listdir(folder):
        if not fil.endswith(".log"):
            continue

        file_data = {}
        file_data["cfile"] = fil[:-4]

        with open(os.path.join(folder, fil), "r", encoding="utf-8") as fd:
            for line in fd:
                statistic, _, *parts = line.split(" ")
                for part in parts:
                    key, value = part.split(":")
                    superkey = (statistic, key)
                    if superkey in KEEP_MAP:
                        try:
                            file_data[KEEP_MAP[superkey]] = int(value)
                        except:
                            file_data[KEEP_MAP[superkey]] = value


        file_datas.append(file_data)

    return pd.DataFrame(file_datas)

def calculate_total_memory_states(file_data, suffix):
    file_data["#TotalMemoryState" + suffix] = (
        file_data["#TotalAllocaState" + suffix] +
        file_data["#TotalMallocState" + suffix] +
        file_data["#TotalDeltaState" + suffix] +
        file_data["#TotalImportState" + suffix] +
        file_data["#TotalLambdaState" + suffix] +
        file_data["#TotalExternalState" + suffix])

def make_file_data(folder, configuration):
    file_data = extract_file_data(folder)
    file_data["Configuration"] = configuration

    # Add calculated columns
    calculate_total_memory_states(file_data, "Arguments")
    calculate_total_memory_states(file_data, "sThroughLoad")
    calculate_total_memory_states(file_data, "sThroughStore")
    calculate_total_memory_states(file_data, "sIntoCallEntryMerge")

    return file_data


def extract_column(data, column, configuration):
    return data[data["Configuration"] == configuration].set_index("cfile")[column]

def plot_ratio_between_configs(file_data, column, conf, baseline_conf, savefig=None):
    data = pd.DataFrame({
        conf: extract_column(file_data, column, conf),
        baseline_conf: extract_column(file_data, column, baseline_conf)
    })
    data.sort_values(baseline_conf, ascending=True, inplace=True)

    plt.figure(figsize=(7,3))

    data["ratio"] = data[conf] / data[baseline_conf]
    sns.scatterplot(x=range(len(data)), y=data["ratio"])

    plt.title(column, fontsize=10)
    plt.ylabel(f"{conf} / {baseline_conf}", fontsize=7)
    plt.xlabel(f"Files sorted by {baseline_conf}", fontsize=7)

    def xline(i):
        plt.gca().axvline(i, linewidth=1, zorder=3, color='#444')
        text = f"{data[baseline_conf].iloc[i]}"
        plt.gca().text(i, 0.1, s=text)

    for p in range(100, len(data), 100):
        xline(p)

    plt.tight_layout(pad=0.2)

    if savefig is not None:
        plt.savefig(savefig)
    else:
        plt.show()

def plot_ratio_between_columns(file_data, configuration, column, baseline_column, savefig=None):
    data = pd.DataFrame({
        column: extract_column(file_data, column, configuration),
        baseline_column: extract_column(file_data, baseline_column, configuration)
    })
    data.sort_values(baseline_column, ascending=True, inplace=True)

    plt.figure(figsize=(7,3))

    data["ratio"] = data[column] / data[baseline_column]
    sns.scatterplot(x=range(len(data)), y=data["ratio"])

    plt.title(configuration, fontsize=10)
    plt.ylabel(f"{column} / {baseline_column}", fontsize=7)
    plt.xlabel(f"Files sorted by {baseline_column}", fontsize=7)

    def xline(i):
        plt.gca().axvline(i, linewidth=1, zorder=3, color='#444')
        text = f"{data[baseline_column].iloc[i]}"
        plt.gca().text(i, 0.1, s=text)

    for p in range(100, len(data), 100):
        xline(p)

    plt.tight_layout(pad=0.2)

    if savefig is not None:
        plt.savefig(savefig)
    else:
        plt.show()

    # print(data.iloc[-10::]["ratio"])

def plot_column(file_data, configuration, column, savefig=None):
    data = pd.DataFrame({
        column: extract_column(file_data, column, configuration)
    })
    data.sort_values(column, ascending=True, inplace=True)

    plt.figure(figsize=(7,3))

    sns.scatterplot(x=range(len(data)), y=data[column])

    plt.title(configuration)
    plt.ylabel(f"{column}")
    plt.xlabel(f"Files sorted by {column}")

    def xline(i):
        plt.gca().axvline(i, linewidth=1, zorder=3, color='#444')
        text = f"{data[column].iloc[i]}"
        plt.gca().text(i, 0.1, s=text)

    for p in range(100, len(data), 100):
        xline(p)

    plt.tight_layout(pad=0.2)

    if savefig is not None:
        plt.savefig(savefig)
    else:
        plt.show()

    # print(data.iloc[-10::]["ratio"])


def main():
    parser = argparse.ArgumentParser(description='Process raw statistics from the given folder.')
    parser.add_argument('--stats-in', dest='stats_in', action='store', default="statistics",
                        help='The folder where statistics files are located')
    parser.add_argument('--stats-out', dest='stats_out', action='store', default="statistics-out",
                        help='Folder where aggregated statistics should be placed')
    args = parser.parse_args()

    if not os.path.exists(args.stats_out):
        os.mkdir(args.stats_out)
    def stats_out(filename=""):
        return os.path.join(args.stats_out, filename)

    raware_curtailed_data = make_file_data(os.path.join(args.stats_in, "raware-curtailed"), "RegionAwareModRef-Curtailed")
    raware_data = make_file_data(os.path.join(args.stats_in, "raware"), "RegionAwareModRef")
    # raware_extraOpts_data = make_file_data(os.path.join(args.stats_in, "raware-extraOpts"), "RegionAwareModRef-ExtraOpts")
    #agnostic_data = make_file_data(os.path.join(args.stats_in, "agnostic"), "AgnosticModRef")

    file_data = pd.concat((raware_curtailed_data, raware_data))
    file_data.to_csv(stats_out("memstate-file-data.csv"))

    plot_ratio_between_configs(file_data, "#TotalMemoryStateArguments", "RegionAwareModRef", "RegionAwareModRef-Curtailed", savefig="results/memrefs-raware-vs-curtailed.pdf")

    #plot_ratio_between_configs(file_data, "#TotalMemoryStateArguments", "RegionAwareModRef-ExtraOpts", "RegionAwareModRef-New", savefig="results/memrefs-extraOpts-vs-new.pdf")
    #plot_ratio_between_configs(file_data, "#TotalLoads", "RegionAwareModRef-ExtraOpts", "RegionAwareModRef-New", savefig="results/memrefs-extraOpts-vs-new.pdf")
    #plot_ratio_between_configs(file_data, "#TotalStores", "RegionAwareModRef-ExtraOpts", "RegionAwareModRef-New", savefig="results/memrefs-extraOpts-vs-new.pdf")

    plot_ratio_between_columns(file_data, "RegionAwareModRef", "#TotalDeltaStateArguments", "#TotalMemoryStateArguments", savefig="results/memstate-args-delta-ratio.pdf")
    plot_ratio_between_columns(file_data, "RegionAwareModRef", "#TotalAllocaStateArguments", "#TotalMemoryStateArguments", savefig="results/memstate-args-alloca-ratio.pdf")
    plot_ratio_between_columns(file_data, "RegionAwareModRef", "#TotalLambdaStateArguments", "#TotalMemoryStateArguments", savefig="results/memstate-args-lambda-ratio.pdf")
    plot_ratio_between_columns(file_data, "RegionAwareModRef", "#TotalImportStateArguments", "#TotalMemoryStateArguments", savefig="results/memstate-args-import-ratio.pdf")
    plot_ratio_between_columns(file_data, "RegionAwareModRef", "#TotalMallocStateArguments", "#TotalMemoryStateArguments", savefig="results/memstate-args-malloc-ratio.pdf")
    plot_ratio_between_columns(file_data, "RegionAwareModRef", "#TotalNonEscapedStateArguments", "#TotalMemoryStateArguments", savefig="results/memstate-args-nonescaped-ratio.pdf")

    plot_ratio_between_columns(file_data, "RegionAwareModRef-Curtailed", "#TotalDeltaStateArguments", "#TotalMemoryStateArguments", savefig="results/memstate-args-delta-ratio-curtailed.pdf")
    plot_ratio_between_columns(file_data, "RegionAwareModRef-Curtailed", "#TotalAllocaStateArguments", "#TotalMemoryStateArguments", savefig="results/memstate-args-alloca-ratio-curtailed.pdf")
    plot_ratio_between_columns(file_data, "RegionAwareModRef-Curtailed", "#TotalLambdaStateArguments", "#TotalMemoryStateArguments", savefig="results/memstate-args-lambda-ratio-curtailed.pdf")
    plot_ratio_between_columns(file_data, "RegionAwareModRef-Curtailed", "#TotalImportStateArguments", "#TotalMemoryStateArguments", savefig="results/memstate-args-import-ratio-curtailed.pdf")
    plot_ratio_between_columns(file_data, "RegionAwareModRef-Curtailed", "#TotalMallocStateArguments", "#TotalMemoryStateArguments", savefig="results/memstate-args-malloc-ratio-curtailed.pdf")
    plot_ratio_between_columns(file_data, "RegionAwareModRef-Curtailed", "#TotalNonEscapedStateArguments", "#TotalMemoryStateArguments", savefig="results/memstate-args-nonescaped-ratio-curtailed.pdf")

    plot_column(file_data, "RegionAwareModRef-Curtailed", "#MaxMemoryStateArguments", savefig="results/memstate-args-max-curtailed.pdf")
    plot_column(file_data, "RegionAwareModRef", "#MaxMemoryStateArguments", savefig="results/memstate-args-max-raware.pdf")
    #plot_column(file_data, "RegionAwareModRef", "#MaxNonEscapedMemoryStatesThroughLoad", savefig="results/memstate-loads-max-nonescaped.pdf")

if __name__ == "__main__":
    main()
