#!/usr/bin/env python3
import argparse
import os
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import plotly.express as px
import sys
import numpy as np
from pathlib import Path

# Global control if plotting should be interactive
plotly = False

def extract_column(data, column, configuration):
    return data[data["Configuration"] == configuration].set_index("cfile")[column]

def int_or_nan(value):
    """Helper for converting to int without dying if it is nan"""
    if np.isnan(value):
        return value
    return int(value)

def to_str(value, decimals=None):
    if isinstance(value, str):
        return value
    if decimals is not None:
        return f"{value:_.{decimals}f}".replace("_","\\,")
    return f"{value:_}".replace("_","\\,")

def print_benchmarks_table(file_data, fd):
    """
    Print info about each benchmark
    """
    benchmarks = file_data["benchmark"].unique()

    print(r"\begin{tabular}{l@{}r@{\ \,}r@{\ \,}r}", file=fd)
    print(r"\toprule", file=fd)
    print("Benchmark & KLOC & \\#Files & Loads\\\\", file=fd)
    print(r"\midrule", file=fd)
    for benchmark in sorted(list(benchmarks)):
        benchmark_name = benchmark.replace("cpu2017-", "")
        num_cfiles = file_data.loc[file_data['benchmark'] == benchmark, 'cfile'].nunique()
        total_loads = file_data.loc[(file_data['benchmark'] == benchmark) & (file_data['Configuration']=="sroa-noPtG"), '#LoadNodes-Tree'].sum()
        print(f"{benchmark_name} &  & {num_cfiles:_} & {total_loads:_}\\\\".replace("_", r"\,"), file=fd)
    print(r"\bottomrule", file=fd)
    print(r"\end{tabular}", file=fd)

def get_all_mod_ref_set_sizes(file_data, config):
    """
    Extracts the sizes of mod/ref entry sets from the "MemoryStateDistribution" column.
    It contains comma separated lists of elements like:
        LAMBDA[ps_get_standard_strings]-GAMMA-(8:7)-1-1
    This function adds up all sets from all files with the given configuration
    """

    data = extract_column(file_data, "MemoryStateDistribution", config)

    load_sizes = []
    store_sizes = []
    call_sizes = []
    gamma_sizes = []
    theta_sizes = []
    lambda_sizes = []
    other_sizes = []

    for row in data:
        # Files with no sets have float 0.0 in the cell
        if not isinstance(row, str):
            continue

        for element in row.split(","):
            func, node, pos, entry_size, exit_size = element.split("-")

            if node.startswith("Load"):
                load_sizes.append(int(entry_size))
            elif node.startswith("Store"):
                store_sizes.append(int(entry_size))
            elif node.startswith("CALL"):
                call_sizes.append(int(entry_size))
            elif node.startswith("GAMMA"):
                gamma_sizes.append(int(entry_size))
            elif node.startswith("THETA"):
                theta_sizes.append(int(entry_size))
            elif node.startswith("LAMBDA"):
                lambda_sizes.append(int(entry_size))
            else:
                other_sizes.append(int(entry_size))

    result = {
        "Load": pd.Series(load_sizes),
        "Store": pd.Series(store_sizes),
        "Call": pd.Series(call_sizes),
        "Gamma": pd.Series(gamma_sizes),
        "Theta": pd.Series(theta_sizes),
        "Lambda": pd.Series(lambda_sizes),
        "Other": pd.Series(other_sizes),
    }

    result["Total"] = pd.concat(result.values())
    return result


def print_mod_ref_set_table(file_data, fd):
    """
    Print quartiles of Mod/Ref set sizes for selected benchmarks
    """
    configurations = [
        ("sroa-rag", r"\Rag"),
        ("sroa-rag-cmf-osf", r"\RagCmfOsf"),
        ("sora-rag-omf", r"\RagOf"),
        ("sroa-rag-omf-cmf-osf", r"\RagOfCmfOsf"),

        ("midrule", ""),

        ("sroa-raw-ip", r"\Raw"),
        ("sroa-raw-ip-cmf", r"\RawCmf"),
        ("sroa-raw-ip-rcaf-cmf-osf", r"\RawRcafCmfOsf"),
        ("sroa-raw-ip-omf", r"\RawOf"),
        ("sroa-raw-ip-omf-cmf-osf", r"\RawOfCmfOsf"),
        ("sroa-raw-ip-rcaf-omf-cmf-osf", r"\RawOfRcafCmfOsf")
    ]

    print(r"\begin{tabular}{lrrrrrrrrr}", file=fd)
    print(r"\toprule", file=fd)
    print("Configuration & $p_{25}$ & $p_{50}$ & $p_{75}$ & $p_{90}$ & $p_{95}$ & $p_{99}$ & Max & Mean & Sum", file=fd)
    print(r"\midule", file=fd)
    for config, name in configurations:
        if config == "midrule":
            print(r"\midrule", file=fd)
            continue

        mod_ref_set_sizes = get_all_mod_ref_set_sizes(file_data, config)["Total"]
        data = []
        for quantile in [25, 50, 75, 90, 95, 99]:
            data.append(int_or_nan(mod_ref_set_sizes.quantile(q=quantile/100)))
        data.append(mod_ref_set_sizes.max())
        data.append(round(mod_ref_set_sizes.mean(), 2))
        data.append(mod_ref_set_sizes.sum())

        data = map(to_str, data)
        print(f"{name} & {' & '.join(data)} \\\\", file=fd)

    print(r"\bottomrule", file=fd)
    print(r"\end{tabular}", file=fd)


def print_mod_ref_set_per_node_type_table(file_data, fd):
    config = "sroa-raw-ip-rcaf-omf-cmf-osf"

    print(f"Table for configuration: {config}\n", file=fd)

    mod_ref_set_sizes = get_all_mod_ref_set_sizes(file_data, config)

    print(r"\begin{tabular}{lrrrrrrrrrr}", file=fd)
    print(r"\toprule", file=fd)
    print("Node Type & $p_{25}$ & $p_{50}$ & $p_{75}$ & $p_{90}$ & $p_{95}$ & $p_{99}$ & Max & Mean & \\multicolumn{2}{c}{\\#Nodes} \\\\", file=fd)
    print(r"\midrule", file=fd)

    nodes_total = len(mod_ref_set_sizes["Total"])

    for node_type, counts in mod_ref_set_sizes.items():
        if node_type == "Total":
            continue

        data = []
        for quantile in [25, 50, 75, 90, 95, 99]:
            data.append(int_or_nan(counts.quantile(q=quantile/100)))
        data.append(counts.max())
        data.append(round(counts.mean(), 2))

        data.append(len(counts))
        share_of_sets = len(counts)/nodes_total
        data.append(f"{share_of_sets*100:.2f}\\%")

        data = map(to_str, data)
        print(f"{node_type} & {' & '.join(data)} \\\\", file=fd)
    print(r"\midrule", file=fd)
    print(f"Total & & & & & & & & & {to_str(nodes_total)} & 100.00\\% \\\\", file=fd)
    print(r"\bottomrule", file=fd)
    print(r"\end{tabular}", file=fd)


def print_mse_runtime_table(file_data, fd):
    """
    Prints table containing quantiles of runtime for the different passes and stages
    """

    configurations = [
        ("sroa-rag", r"\Rag"),
        ("sroa-rag-cmf-osf", r"\RagCmfOsf"),
        ("sroa-rag-omf-cmf-osf", r"\RagOfCmfOsf"),
        ("sroa-raw", r"\Raw"),
        ("sroa-raw-rcaf-omf-cmf-osf", r"\RawOfRcafCmfOsf"),
        ("sroa-raw-ip-rcaf-omf-cmf-osf", r"\RawOfRcafCmfOsfIp")
    ]
    # Skipping the second to last
    configurations_sans_nonip = configurations[:-2] + configurations[-1:]

    print(r"\begin{tabular}{llrrrrrrrr}", file=fd)
    print(r"\toprule", file=fd)
    print(r" & Configuration & $p_{50}$ & $p_{75}$ & $p_{90}$ & $p_{95}$ & $p_{99}$ & Max & Mean \\\\", file=fd)
    print(r"\midrule", file=fd)
    print(r"\multirow{6}{*}{\rotatebox[origin=c]{90}{Construction}}", file=fd)

    def print_rows(configurations, column):
        for config, name in configurations:
            # Get times in milliseconds
            times = extract_column(file_data, column, config) / 1_000_000

            data = []
            for quantile in [50, 75, 90, 95, 99]:
                data.append(times.quantile(q=quantile/100))
            data.append(times.max())
            data.append(times.mean())

            data = [to_str(value, 2) for value in data]
            print(f" & {name} & {' & '.join(data)} \\\\", file=fd)

    print_rows(configurations, "ConstructionTime[ns]-mean")

    print(r"\midrule", file=fd)
    print(r"\multirow{5}{*}{\rotatebox[origin=c]{90}{Encoding}}", file=fd)

    print_rows(configurations_sans_nonip, "MemoryStateEncodingTime[ns]-mean")

    print(r"\midrule", file=fd)
    print(r"\multirow{5}{*}{\rotatebox[origin=c]{90}{MSE}}", file=fd)

    print_rows(configurations_sans_nonip, "TotalMSETime[ns]-mean")

    print(r"\bottomrule", file=fd)
    print(r"\end{tabular}", file=fd)

def num_loads(file_data, config, tree_num):
    colname = "#LoadNodes-Tree"
    if tree_num > 0:
        colname = f"{colname}--{tree_num:02d}"
    return extract_column(file_data, colname, config).sum()

def num_alias_queries(file_data, config):
    return extract_column(file_data, "TotalAliasQueries", config).sum()

def print_load_elision_table(file_data, fd):
    """
    Prints the load elision table from the paper, plus some numbers mentioned in the text
    """

    base_config = "noPtG"
    FIRST_TREE = 0
    FINAL_TREE = 4

    configurations = [
        ("noPtG", r"\NoPtg"),
        ("PtGAA", r"\PtgAA"),
        ("rag-omf-cmf-osf", r"\RagOfCmfOsf"),
        ("raw-ip-omf", r"\RawOf"),
        ("raw-ip-omf-cmf-osf", r"\RawOfCmfOsf"),
        ("raw-ip-rcaf-omf-cmf-osf", r"\RawOfRcafCmfOsf")
    ]

    num_loads_after_sroa = num_loads(file_data, "sroa-" + base_config, FIRST_TREE)
    num_loads_after_Oz = num_loads(file_data, "Oz-" + base_config, FIRST_TREE)

    print(f"After sroa, the number of loads left is {num_loads_after_sroa}", file=fd)
    print(f"After Oz, the number of loads left is {num_loads_after_Oz}", file=fd)
    print("", file=fd)

    print(r"\begin{tabular}{lr@{\ \ }rr@{\ \ }rr@{\ \ }rr@{\ \ }r}", file=fd)
    print(r"\toprule", file=fd)
    print(r"Clang Pipeline & \multicolumn{4}{c}{\texttt{clang -O0 + sroa}} & \multicolumn{4}{c}{\texttt{clang -Oz}} \\", file=fd)
    print(r"\cmidrule(lr){2-5}\cmidrule(lr){6-9}", file=fd)
    print(r"\verb|jlm| Configuration & \multicolumn{2}{c}{Loads elided} & \multicolumn{2}{c}{Alias Queries} & \multicolumn{2}{c}{Loads elided} & \multicolumn{2}{c}{Alias Queries} \\", file=fd)
    print(r"\midrule", file=fd)

    loads_after = {"sroa": num_loads_after_sroa, "Oz": num_loads_after_Oz}
    first_loads_elided = {}
    first_aa_queries = {}

    for config, name in configurations:
        print(f"{name} ", file=fd)
        for clang_choice in ["sroa", "Oz"]:
            full_config = f"{clang_choice}-{config}"

            loads = num_loads(file_data, full_config, FINAL_TREE)
            loads_elided = loads_after[clang_choice] - loads

            print(f" & {to_str(loads_elided)}", end="", file=fd)
            if clang_choice in first_loads_elided:
                ratio = (loads_elided - first_loads_elided[clang_choice]) / first_loads_elided[clang_choice]
                print(f" & {ratio*100:+.1f}\\%", end="", file=fd)
            else:
                first_loads_elided[clang_choice] = loads_elided
                print(r" & \multicolumn{1}{c}{--}", end="", file=fd)

            alias_queries = num_alias_queries(file_data, full_config)
            print(f" & {to_str(alias_queries)}", end="", file=fd)
            if clang_choice in first_aa_queries:
                ratio = (alias_queries - first_aa_queries[clang_choice]) / first_aa_queries[clang_choice]
                print(f" & {ratio*100:+.1f}\\%", end="", file=fd)
            else:
                first_aa_queries[clang_choice] = alias_queries
                print(r" & \multicolumn{1}{c}{--}", end="", file=fd)

        print(r"\\", file=fd)

    print(r"\bottomrule", file=fd)
    print(r"\end{tabular}", file=fd)


def main():
    parser = argparse.ArgumentParser(description='Create results from from aggregated statistics.')
    parser.add_argument('--stats-file', dest='stats_file', action='store', default="statistics-out/file-data.csv",
                        help='The folder where aggregated statistics are located')
    parser.add_argument('--outout', dest='outdir', action='store', default="results",
                        help='Folder where result plots and tables should be placed')
    parser.add_argument('--plotly', action='store_true',
                        help='Use plotly to render interactive')
    args = parser.parse_args()

    global plotly
    plotly = args.plotly

    outdir = Path(args.outdir)

    # Read the input file (which is huge!)
    file_data = pd.read_csv(args.stats_file)

    # Remove all files that are not present in all configurations
    nconfigs = file_data["Configuration"].nunique()
    keep_cfiles = file_data.groupby("cfile")["Configuration"].nunique() == nconfigs
    delete_cfiles = keep_cfiles[~keep_cfiles].index
    if len(delete_cfiles):
        print("WARNING: Ingoring cfiles due to missing some configurations:", delete_cfiles)
        file_data = file_data[file_data["cfile"].map(keep_cfiles)]

    print("Removing files with no structural nodes")
    remove_cfiles = file_data.loc[(file_data["#Regions-Tree"]<=1) & (file_data["Configuration"]=="sroa-noPtG"), "cfile"].unique()
    print(f"Removing {len(remove_cfiles)} files")
    file_data = file_data.loc[~file_data["cfile"].isin(remove_cfiles)]
    print(f'cfiles left: {file_data["cfile"].nunique()}')

    # =============================================
    #           Create derived columns
    # =============================================
    all_configurations = file_data["Configuration"].unique()
    file_data["benchmark"] = file_data["cfile"].str.extract(r'^(.*)\+.*')[0]

    # Define column and accessor for getting number of alias queries made by (first iteration of) SVF
    alias_columns = ["#NoAliasStore", "#MayAliasStore", "#MustAliasStore", "#NoAliasLoad", "#MayAliasLoad", "#MustAliasLoad"]
    file_data["TotalAliasQueries"] = file_data.loc[:, alias_columns].sum(axis=1)

    # Total runtimes, including whatever mod/ref set construction was used
    file_data["ConstructionTime[ns]-mean"] = file_data["RegionAwareModRefSummarizerTime[ns]-mean"].fillna(0.0) + file_data["AgnosticModRefSummarizerTime[ns]-mean"].fillna(0.0)
    file_data["TotalMSETime[ns]-mean"] = file_data["ConstructionTime[ns]-mean"] + file_data["MemoryStateEncodingTime[ns]-mean"].fillna(0.0)

    # =============================================
    #           Output tables and figures
    # =============================================

    # Table of benchmarks
    with open(outdir / "benchmarks.txt", "w", encoding="utf-8") as fd:
        print_benchmarks_table(file_data, fd)

    # Table of mod/ref set sizes for different configurations
    with open(outdir / "mod_ref_set_sizes.txt", "w", encoding="utf-8") as fd:
        print_mod_ref_set_table(file_data, fd)

    # Table of mod/ref set sizes for different node types in single configuration
    with open(outdir / "mod_ref_set_sizes_per_node_type.txt", "w", encoding="utf-8") as fd:
        print_mod_ref_set_per_node_type_table(file_data, fd)

    # Table of runtime of mod/ref set construction, encoding and both
    with open(outdir / "mse_runtime.txt", "w", encoding="utf-8") as fd:
        print_mse_runtime_table(file_data, fd)

    # Load elision table for both sroa and Oz
    with open(outdir / "load_elision_table.txt", "w", encoding="utf-8") as fd:
        print_load_elision_table(file_data, fd)

    # ===========================================
    #       Useful standalone numbers
    # ===========================================

    # Number of (trivial) loads removed by opt's sroa
    loads_O0 = num_loads(file_data, "O0-noPtG", 0)
    loads_sroa = num_loads(file_data, "sroa-noPtG", 0)
    print(f"After O0, the number of loads is: {loads_O0}")
    print(f"After O0 + sroa, the number of loads is: {loads_sroa}, which is {(loads_sroa-loads_O0)/loads_O0*100:+.2f}%")
    print()

    # Number of allocas that are register confined (simple)
    total_allocas = extract_column(file_data, "#AllocaNodes-Tree--01", "sroa-raw-ip-rcaf").sum()
    simple_allocas = extract_column(file_data, "#SimpleAllocas", "sroa-raw-ip-rcaf").sum()
    print(f"Total number of allocas after sroa: {total_allocas}")
    print(f"Number of simple allocas: {simple_allocas} ({simple_allocas/total_allocas*100:.2f}%)")
    print()

if __name__ == "__main__":
    main()
