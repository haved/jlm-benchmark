#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

file_data = pd.read_csv("statistics-out/file_data.csv")
all_configs = pd.read_csv("statistics-out/file_config_data.csv")

# Check that all cfiles have been tested with all 212 configurations
configs_per_cfile = all_configs.groupby("cfile")["Configuration"].nunique()
missing_configs = configs_per_cfile[configs_per_cfile != 212]
if len(missing_configs) != 0:
    print("WARNING: Some cfiles have not been evaluated with all configs!")
    print(missing_configs)

def ensure_consistent_per_cfile(column):
    num_different_counts = all_configs.groupby("cfile")[column].nunique()
    non_unique_cfiles = num_different_counts[num_different_counts > 1].index
    for cfile in non_unique_cfiles:
        print(f"ERROR: Different configurations have different values of {column} in {cfile}")
    if len(non_unique_cfiles) > 0:
        exit(1)
#ensure_consistent_per_cfile("#PointsToRelations")
#ensure_consistent_per_cfile("#PointsToExternalRelations")
#ensure_consistent_per_cfile("#CanPointsEscaped")
#ensure_consistent_per_cfile("#CantPointsEscaped")

# Remove empty files
file_data = file_data[file_data["#RvsdgNodes"] > 0]
all_configs = all_configs[all_configs["#RvsdgNodes"] > 0]

# Remove NORM to see what effect it has. Answer: VERY little effect on oracle
all_configs = all_configs[~all_configs["Configuration"].str.contains("NORM")]

# Use the config that is fastest on average with flags
BEST_CONFIG = "IP_Solver=Worklist_Policy=FirstInFirstOut_PIP"
BEST_CONFIG_SANS_PIP = "IP_Solver=Worklist_Policy=FirstInFirstOut"
BEST_CONFIG_WITH_EP = "EP_OVS_Solver=Worklist_Policy=LeastRecentlyFired_OnlineCD"

# This dataframe contains one column with the total time per interesting choice of configuration
total_time_ns = file_data.set_index("cfile")

def add_column_to_total_time(data, column_name):
    data = data.set_index("cfile")
    total_time_ns[column_name] = data["TotalTime[ns]"]

# Adds the TotalTime from all_configs where the configuration matches the given config
def add_column_with_config(config_name, column_name):
    only_given_config = all_configs[all_configs["Configuration"] == config_name]
    add_column_to_total_time(only_given_config, column_name)

add_column_with_config(BEST_CONFIG, "best_config")
add_column_with_config(BEST_CONFIG_SANS_PIP, "best_config_sans_pip")
add_column_with_config(BEST_CONFIG_WITH_EP, "best_config_with_ep")

# Among all rows in data, picks the fastest TotalTime per cfile and uses that
def add_oracle_config_per_cfile(data, column_name):
    idx_per_cfile = data.groupby("cfile")["TotalTime[ns]"].idxmin()
    add_column_to_total_time(data.loc[idx_per_cfile, :], column_name)

all_configs_sans_pip = all_configs[~all_configs["Configuration"].str.contains("PIP")]
all_configs_sans_naive = all_configs[~all_configs["Configuration"].str.contains("Naive")]
all_configs_sans_pip_or_naive = all_configs_sans_naive[~all_configs_sans_naive["Configuration"].str.contains("PIP")]
all_configs_with_ep = all_configs[all_configs["Configuration"].str.contains("EP_")]
all_configs_only_naive = all_configs[all_configs["Configuration"].str.contains("Naive")]

add_oracle_config_per_cfile(all_configs, "oracle")
add_oracle_config_per_cfile(all_configs_sans_pip, "oracle_sans_pip")
add_oracle_config_per_cfile(all_configs_sans_naive, "oracle_sans_naive")
add_oracle_config_per_cfile(all_configs_sans_pip_or_naive, "oracle_sans_pip_or_naive")
add_oracle_config_per_cfile(all_configs_with_ep, "oracle_with_ep")
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
print_table_row("\\texttt{IP+WL(FIFO)+PIP}", "best_config")
#print_table_row("Oracle without \\texttt{PIP}", "oracle_sans_pip")
#print_table_row("Oracle without \\texttt{Naive}", "oracle_sans_naive")
#print_table_row("Oracle with \\texttt{Naive}", "oracle_only_naive")
#print_table_row("Oracle without \\texttt{PIP} or \\texttt{Naive}", "oracle_sans_pip_or_naive")
#print_table_row("\\texttt{ImP+WL=FIFO}", "best_config_sans_pip")
print_table_row("Oracle with \\texttt{EP}", "oracle_with_ep")
print_table_row("\\texttt{EP+OVS+WL(LRF)+OnlineCD}", "best_config_with_ep")

CUTOFF = 1e4
total_time_cutoff = total_time_ns[(total_time_ns["best_config"] > CUTOFF) | (total_time_ns["oracle_with_ep"] > CUTOFF)]

print("C files before cutoff:", len(total_time_ns), "after cutoff:", len(total_time_cutoff))
print("Mean speedup:", (total_time_ns["oracle_with_ep"] / total_time_ns["best_config"]).mean())
print("Mean speedup (with cutoff):", (total_time_cutoff["oracle_with_ep"] / total_time_cutoff["best_config"]).mean())
print("Total speedup:", total_time_ns["oracle_with_ep"].sum() / total_time_ns["best_config"].sum())
print("Total speedup (with cutoff):", total_time_cutoff["oracle_with_ep"].sum() / total_time_cutoff["best_config"].sum())

# ============== Drawing best config vs Oracle with EP ====================
#x = np.linspace(0, 1, len(total_time_cutoff))
x = range(len(total_time_cutoff))

plt.figure(figsize=(7,3))
plt.yscale("log")

plt.scatter(x=x, y=total_time_cutoff["best_config"]/1000, color="blue", marker=".", alpha=0.3, label="IP+WL(FIFO)+PIP")
plt.scatter(x=x, y=total_time_cutoff["oracle_with_ep"]/1000, color="red", marker=".", alpha=0.3, label="Oracle with EP")

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
print_table_row("\\texttt{IP+WL(FIFO)+PIP}", "best_config")
#print_table_row("Oracle without \\texttt{PIP}", "oracle_sans_pip")
#print_table_row("Oracle without \\texttt{Naive}", "oracle_sans_naive")
#print_table_row("Oracle with \\texttt{Naive}", "oracle_only_naive")
#print_table_row("Oracle without \\texttt{PIP} or \\texttt{Naive}", "oracle_sans_pip_or_naive")
#print_table_row("\\texttt{ImP+WL=FIFO}", "best_config_sans_pip")
#print_table_row("Oracle without \\texttt{PIP}", "oracle_sans_pip_or_naive")
print_table_row("\\texttt{IP+WL(FIFO)}", "best_config_sans_pip")

plt.figure(figsize=(7,3))
plt.yscale("log")

plt.scatter(x=x, y=total_time_cutoff["best_config"]/1000, color="blue", marker=".", alpha=0.3, label="IP+WL(FIFO)+PIP")
plt.scatter(x=x, y=total_time_cutoff["best_config_sans_pip"]/1000, color="green", marker=".", alpha=0.3, label="IP+WL(FIFO)")

plt.ylabel("Solving time [$\\mu$s]")
plt.xlabel("File number")
# plt.margins(x=10)

plt.grid()
plt.legend()
plt.tight_layout(pad=0.2)
plt.savefig("results/default_best_vs_default_best_sans_pip.pdf")


# ========== Make boxplot of runtimes with and without PIP ==============================
sns.set_theme(style="whitegrid", palette=None)
plt.figure(figsize=(7,3))

df0 = pd.DataFrame({"TotalTime[us]": total_time_ns["best_config"]/1000, "Config": "IP+WL(FIFO)+PIP" })
df1 = pd.DataFrame({"TotalTime[us]": total_time_ns["best_config_sans_pip"]/1000, "Config": "IP+WL(FIFO)" })
best_data = pd.concat([df0.reset_index(drop=True), df1.reset_index(drop=True)], axis="rows")

sns.boxplot(data=best_data, x="TotalTime[us]", y="Config", showmeans=True, meanline=True, meanprops={"color": ".1"},
                color=".8", linecolor=".1", fliersize="5")

#plt.xscale("log")
plt.tight_layout(pad=0.2)
plt.savefig("results/best_config_with_and_without_pip.pdf")

# ========== Make scatterplot between PIP and not PIP ===============================

print(total_time_cutoff[total_time_cutoff["best_config_sans_pip"]-total_time_cutoff["best_config"] > 2e8])

plt.figure(figsize=(7,7))
plt.scatter(x=total_time_cutoff["#PointerObjects"], y=total_time_cutoff["best_config_sans_pip"]-total_time_cutoff["best_config"], marker=".", color="red")
#plt.scatter(x=total_time_cutoff["#PointerObjects"], y=total_time_cutoff["best_config_sans_pip"], marker=".", color="blue")

def plot_diagonal_line(ax):
    lims = [
        np.min([ax.get_xlim(), ax.get_ylim()]),  # min of both axes
        np.max([ax.get_xlim(), ax.get_ylim()]),  # max of both axes
    ]

    # now plot both limits against eachother
    ax.plot(lims, lims, 'k-', alpha=0.75, zorder=0)
    ax.set_aspect('equal')
    ax.set_xlim(lims)
    ax.set_ylim(lims)

#plot_diagonal_line(plt.gca())
plt.savefig("results/scatterplot_with_vs_without_pip.pdf")


print(" ==== Some final stats ==== ")
print("Number of configurations:", len(all_configs["Configuration"].unique()))
print("Number of configurations with IP:", len(all_configs.loc[all_configs["Configuration"].str.contains("IP_"), "Configuration"].unique()))
print("Number of configurations with EP:", len(all_configs.loc[all_configs["Configuration"].str.contains("EP_"), "Configuration"].unique()))
