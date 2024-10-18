#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

default = pd.read_csv("statistics-out/release/file_config_data.csv")
default["Configuration"] = "ImP_" + default["Configuration"]
anf = pd.read_csv("statistics-out/release-anf/file_config_data.csv")

for cfile in set(default["cfile"]).symmetric_difference(anf["cfile"]):
    print(f"cfile not present in both default and anf: {cfile}")

# Make a single unified dataframe containing all files with all configurations
all_configs = pd.concat([default, anf], ignore_index=True)

# Remove empty files
all_configs = all_configs[all_configs["#RvsdgNodes"] > 0]

# Use the config that is fastest on average with flags
BEST_CONFIG = "ImP_Solver=Worklist_Policy=FirstInFirstOut_PIP"
BEST_CONFIG_SANS_PIP = "ImP_Solver=Worklist_Policy=FirstInFirstOut"
BEST_CONFIG_SANS_IMP = "OVS_Solver=Worklist_Policy=LeastRecentlyFired_OnlineCD"

# This dataframe contains one column with the total time per interesting choice of configuration
total_time_ns = pd.DataFrame(index=pd.Index(all_configs["cfile"]).unique())

def add_column_to_total_time(data, column_name):
    data = data.set_index("cfile")
    total_time_ns[column_name] = data["TotalTime[ns]"]

# Adds the TotalTime from all_configs where the configuration matches the given config
def add_column_with_config(config_name, column_name):
    only_given_config = all_configs[all_configs["Configuration"] == config_name]
    add_column_to_total_time(only_given_config, column_name)

add_column_with_config(BEST_CONFIG, "best_config")
add_column_with_config(BEST_CONFIG_SANS_PIP, "best_config_sans_pip")
add_column_with_config(BEST_CONFIG_SANS_IMP, "best_config_sans_imp")

# Among all rows in data, picks the fastest TotalTime per cfile and uses that
def add_oracle_config_per_cfile(data, column_name):
    idx_per_cfile = data.groupby("cfile")["TotalTime[ns]"].idxmin()
    add_column_to_total_time(data.loc[idx_per_cfile, :], column_name)

all_configs_sans_pip = all_configs[~all_configs["Configuration"].str.contains("PIP")]
all_configs_sans_naive = all_configs[~all_configs["Configuration"].str.contains("Naive")]
all_configs_sans_pip_or_naive = all_configs_sans_naive[~all_configs_sans_naive["Configuration"].str.contains("PIP")]
all_configs_sans_imp = all_configs[~all_configs["Configuration"].str.contains("ImP")]
all_configs_only_naive = all_configs[all_configs["Configuration"].str.contains("Naive")]

add_oracle_config_per_cfile(all_configs, "oracle")
add_oracle_config_per_cfile(all_configs_sans_pip, "oracle_sans_pip")
add_oracle_config_per_cfile(all_configs_sans_naive, "oracle_sans_naive")
add_oracle_config_per_cfile(all_configs_sans_pip_or_naive, "oracle_sans_pip_or_naive")
add_oracle_config_per_cfile(all_configs_sans_imp, "oracle_sans_imp")
add_oracle_config_per_cfile(all_configs_only_naive, "oracle_only_naive")

total_time_ns.sort_values("best_config", ascending=True, inplace=True)

def print_table_header():
    us = "\\unit{\\micro\\second}"
    print(" & \\multicolumn{4}{c}{" + f"Total solving time [{us}]" + "} \\\\")
    print("Configuration & Mean & p50 & p99 & max \\\\")
    print("\\midrule")

def print_table_row(name, column_name):
    print(f"{name:<30}", end=" ")

    average_us = total_time_ns[column_name].mean() / 1000
    p50_us = total_time_ns[column_name].quantile(q=0.5) / 1000
    p99_us = total_time_ns[column_name].quantile(q=0.99) / 1000
    slowest_us = total_time_ns[column_name].max() / 1000

    for number in [average_us, p50_us, p99_us, slowest_us]:
        number = f"{number:_.0f}"
        number = number.replace("_", "\\;")
        print(f"& {number:>8}", end=" ")
    print("\\\\")

print_table_header()
#print_table_row("Oracle", "oracle")
print_table_row("\\texttt{ImP+WL=FIFO+PIP}", "best_config")
#print_table_row("Oracle without \\texttt{PIP}", "oracle_sans_pip")
#print_table_row("Oracle without \\texttt{Naive}", "oracle_sans_naive")
#print_table_row("Oracle with \\texttt{Naive}", "oracle_only_naive")
#print_table_row("Oracle without \\texttt{PIP} or \\texttt{Naive}", "oracle_sans_pip_or_naive")
#print_table_row("\\texttt{ImP+WL=FIFO}", "best_config_sans_pip")
print_table_row("Oracle without \\texttt{ImP}", "oracle_sans_imp")
print_table_row("\\texttt{OVS+WL=LRF+OnlineCD}", "best_config_sans_imp")

CUTOFF = 1e4
total_time_cutoff = total_time_ns[(total_time_ns["best_config"] > CUTOFF) | (total_time_ns["oracle_sans_imp"] > CUTOFF)]

print("C files before cutoff:", len(total_time_ns), "after cutoff:", len(total_time_cutoff))
print("Mean speedup:", (total_time_ns["oracle_sans_imp"] / total_time_ns["best_config"]).mean())
print("Mean speedup (with cutoff):", (total_time_cutoff["oracle_sans_imp"] / total_time_cutoff["best_config"]).mean())
print("Total speedup:", total_time_ns["oracle_sans_imp"].sum() / total_time_ns["best_config"].sum())
print("Total speedup (with cutoff):", total_time_cutoff["oracle_sans_imp"].sum() / total_time_cutoff["best_config"].sum())

#x = np.linspace(0, 1, len(total_time_cutoff))
x = range(len(total_time_cutoff))

plt.figure(figsize=(7,3))
plt.yscale("log")

plt.scatter(x=x, y=total_time_cutoff["best_config"]/1000, color="blue", alpha=0.3, label="ImP+WL=FIFO+PIP")
plt.scatter(x=x, y=total_time_cutoff["oracle_sans_imp"]/1000, color="red", alpha=0.3, label="Oracle without ImP")

plt.ylabel("Solving time [$\\mu$s]")
plt.xlabel("File number")
# plt.margins(x=10)

plt.grid()
plt.legend()
plt.tight_layout(pad=0.2)
plt.savefig("results/default_best_vs_oracle_without_imp.pdf")

### Now we wish to compare PIP and no PIP
print(" ==== NOW COMPARING PIP AGAINST NO PIP ==== ")

print_table_header()
#print_table_row("Oracle", "oracle")
print_table_row("\\texttt{ImP+WL=FIFO+PIP}", "best_config")
#print_table_row("Oracle without \\texttt{PIP}", "oracle_sans_pip")
#print_table_row("Oracle without \\texttt{Naive}", "oracle_sans_naive")
#print_table_row("Oracle with \\texttt{Naive}", "oracle_only_naive")
#print_table_row("Oracle without \\texttt{PIP} or \\texttt{Naive}", "oracle_sans_pip_or_naive")
#print_table_row("\\texttt{ImP+WL=FIFO}", "best_config_sans_pip")
print_table_row("Oracle without \\texttt{PIP}", "oracle_sans_pip_or_naive")
print_table_row("\\texttt{ImP+WL=FIFO}", "best_config_sans_pip")


plt.figure(figsize=(7,3))
plt.yscale("log")

plt.scatter(x=x, y=total_time_cutoff["best_config"]/1000, color="blue", alpha=0.3, label="ImP+WL=FIFO+PIP")
plt.scatter(x=x, y=total_time_cutoff["oracle_sans_pip_or_naive"]/1000, color="green", alpha=0.3, label="Oracle without PIP")

plt.ylabel("Solving time [$\\mu$s]")
plt.xlabel("File number")
# plt.margins(x=10)

plt.grid()
plt.legend()
plt.tight_layout(pad=0.2)
plt.savefig("results/default_best_vs_oracle_without_pip.pdf")

print(" ==== Some final stats ==== ")
print("Number of configurations:", len(all_configs["Configuration"].unique()))
print("Number of configurations with ImP:", len(default["Configuration"].unique()))
print("Number of configurations without ImP:", len(anf["Configuration"].unique()))

print("Number of configurations with ImP and PIP:", len(default.loc[default["Configuration"].str.contains("PIP"), "Configuration"].unique()))
print(default["Configuration"].unique())
