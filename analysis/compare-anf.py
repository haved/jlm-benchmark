#!/usr/bin/env python3
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import seaborn as sns
import numpy as np
import argparse
import os

# This file makes plots and tables with general information about the different configurations
# "anf" refers to ANDERSEN_NO_FLAGS, and is equivalent to the EP representation, btw.

# These configs are supposed to be the fastest in their respective categories
# If they are not, this script will print out how large the difference is.
BEST_CONFIG = "IP_Solver=Worklist_Policy=FirstInFirstOut_PIP"
BEST_CONFIG_SANS_PIP = "IP_Solver=Worklist_Policy=FirstInFirstOut_LazyCD_DP"
BEST_CONFIG_JUST_WITHOUT_PIP = "IP_Solver=Worklist_Policy=FirstInFirstOut"
BEST_CONFIG_WITH_EP = "EP_OVS_Solver=Worklist_Policy=LeastRecentlyFired_OnlineCD"

# Prettier names for the above configs
BEST_CONFIG_PRETTY = "IP+WL(FIFO)+PIP"
BEST_CONFIG_SANS_PIP_PRETTY = "IP+WL(FIFO)+LCD+DP"
BEST_CONFIG_JUST_WITHOUT_PIP_PRETTY = "IP+WL(FIFO)"
BEST_CONFIG_WITH_EP_PRETTY = "EP+OVS+WL(LRF)+OCD"

parser = argparse.ArgumentParser(description='Make figures and tables about solver runtime')
parser.add_argument('--stats', dest='stats', action='store', required=True,
                    help='Specify the folder for aggregated statistics')
parser.add_argument('--out', dest='out_dir', action='store', required=True,
                    help='The output folder for plots and tables')
args = parser.parse_args()

def out_path(filename):
    return os.path.join(args.out_dir, filename)

file_data = pd.read_csv(os.path.join(args.stats, "file_data.csv"))
all_configs = pd.read_csv(os.path.join(args.stats, "file_config_data.csv"))

# Remove empty files
file_data = file_data[file_data["#RvsdgNodes"] > 0]
all_configs = all_configs[all_configs["#RvsdgNodes"] > 0]
assert len(file_data) == all_configs["cfile"].nunique()

print("Num non-empty C files:", len(file_data))
print("Number of configurations:", len(all_configs["Configuration"].unique()))
all_ip_configs = all_configs[all_configs["Configuration"].str.startswith("IP_")]
all_ep_configs = all_configs[all_configs["Configuration"].str.startswith("EP_")]
print("Number of configurations with IP:", len(all_ip_configs["Configuration"].unique()))
print("Number of configurations with EP:", len(all_ep_configs["Configuration"].unique()))

# All IP configuration should have exactly the same sets of cfiles
cfiles_of_ip_configs = all_ip_configs["cfile"].unique()
assert (all_ip_configs.groupby("Configuration")["cfile"].nunique() == len(cfiles_of_ip_configs)).all()

# Remove any cfiles that have only been solved by EP configs
all_configs = all_configs[all_configs["cfile"].isin(cfiles_of_ip_configs)]

# Find configurations that solved every cfile solved by the IP configs
solved_all_cfiles = all_configs.groupby("Configuration")["cfile"].nunique() == len(cfiles_of_ip_configs)
solved_all_cfiles = solved_all_cfiles[solved_all_cfiles]

# Among configurations that have successfully solved all cfiles, add up their total runtime
total_runtime_per_config = all_configs.groupby("Configuration")["TotalTime[ns]"].sum()
total_runtime_per_config = total_runtime_per_config[total_runtime_per_config.index.isin(solved_all_cfiles.index)]
print("Number of configs left after skipping half-finished:", len(total_runtime_per_config))
assert len(total_runtime_per_config) > 0

has_ep = True
if total_runtime_per_config.index.str.startswith("EP_").sum() == 0:
    print("WARNING: there is not a single EP configuration that has solved every file!")
    print("All EP results are therefore skipped.")
    print()
    has_ep = False

# Double check that these "best" configurations are actually the best
best_config = total_runtime_per_config.idxmin()
if best_config != BEST_CONFIG:
    print(f"WARNING: In the paper, the on average fastest config is {BEST_CONFIG}, but in your results it is {best_config}")
    print(f"The discrepency is hopefully small enough that this does not really matter:")
    print(f"{BEST_CONFIG} has total runtime: {total_runtime_per_config[BEST_CONFIG]/1e9:.5f} seconds")
    print(f"{best_config} has total runtime: {total_runtime_per_config[best_config]/1e9:.5f} seconds")
    print()

best_config_sans_pip = total_runtime_per_config[~total_runtime_per_config.index.str.contains("_PIP")].idxmin()
if best_config_sans_pip != BEST_CONFIG_SANS_PIP:
    print(f"WARNING: In the paper, the on average fastest config without PIP is {BEST_CONFIG_SANS_PIP}, but in your results it is {best_config_sans_pip}")
    print(f"The discrepency is hopefully small enough that this does not really matter:")
    print(f"{BEST_CONFIG_SANS_PIP} has total runtime: {total_runtime_per_config[BEST_CONFIG_SANS_PIP]/1e9:.5f} seconds")
    print(f"{best_config_sans_pip} has total runtime: {total_runtime_per_config[best_config_sans_pip]/1e9:.5f} seconds")
    print()

if has_ep:
    best_with_ep = total_runtime_per_config[total_runtime_per_config.index.str.startswith("EP_")].idxmin()
    if best_with_ep != BEST_CONFIG_WITH_EP:
        print(f"WARNING: In the paper, the on average fastest EP config is {BEST_CONFIG_WITH_EP}, but in your results it is {best_config_with_ep}")
        print(f"The discrepency is hopefully small enough that this does not really matter:")
        print(f"{BEST_CONFIG_WITH_EP} has total runtime: {total_runtime_per_config[BEST_CONFIG_WITH_EP]/1e9:.5f} seconds")
        print(f"{best_config_with_ep} has total runtime: {total_runtime_per_config[best_config_with_ep]/1e9:.5f} seconds")
        print()

# This dataframe contains one column with the total time per interesting choice of configuration
total_time_ns = file_data.set_index("cfile")

def add_column_to_total_time(data, column_name):
    data = data.set_index("cfile")
    total_time_ns[column_name] = data["TotalTime[ns]"]

# Adds the TotalTime from all_configs where the configuration matches the given config
def add_column_with_config(config_name, column_name):
    only_given_config = all_configs[all_configs["Configuration"] == config_name]
    add_column_to_total_time(only_given_config, column_name)
    return only_given_config.set_index("cfile")

best_config_data = add_column_with_config(BEST_CONFIG, "best_config")
add_column_with_config(BEST_CONFIG_SANS_PIP, "best_config_sans_pip")
add_column_with_config(BEST_CONFIG_JUST_WITHOUT_PIP, "best_config_just_without_pip")
if has_ep:
    best_config_with_ep_data = add_column_with_config(BEST_CONFIG_WITH_EP, "best_config_with_ep")

# Among all rows in data, picks the fastest TotalTime per cfile and uses that
def add_oracle_config_per_cfile(data, column_name):
    idx_per_cfile = data.groupby("cfile")["TotalTime[ns]"].idxmin()
    data = data.loc[idx_per_cfile, :]
    add_column_to_total_time(data, column_name)
    return data.set_index("cfile")

#all_configs_sans_pip = all_configs[~all_configs["Configuration"].str.contains("PIP")]
#all_configs_sans_naive = all_configs[~all_configs["Configuration"].str.contains("Naive")]
#all_configs_sans_pip_or_naive = all_configs_sans_naive[~all_configs_sans_naive["Configuration"].str.contains("PIP")]
#all_configs_only_naive = all_configs[all_configs["Configuration"].str.contains("Naive")]

#add_oracle_config_per_cfile(all_configs, "oracle")
#add_oracle_config_per_cfile(all_configs_sans_pip, "oracle_sans_pip")
#add_oracle_config_per_cfile(all_configs_sans_naive, "oracle_sans_naive")
#add_oracle_config_per_cfile(all_configs_sans_pip_or_naive, "oracle_sans_pip_or_naive")

if has_ep:
    all_configs_with_ep = all_configs[all_configs["Configuration"].str.contains("EP_")]
    oracle_ep_data = add_oracle_config_per_cfile(all_configs_with_ep, "oracle_with_ep")

total_time_ns.sort_values("best_config_sans_pip", ascending=True, inplace=True)

def print_table_header(fd):
    us = "\\unit{\\micro\\second}"
    print("\\begin{tabular}{lrrrrrrrr}", file=fd)
    print("\\toprule", file=fd)
    print(" & \\multicolumn{8}{c}{" + f"Solver Runtime [{us}]" + "} \\\\", file=fd)
    print("Configuration & p10 & p25 & p50 & p90 & p99 & Max & Mean & Sum\\\\", file=fd)
    print("\\midrule", file=fd)

def print_table_row(name, column_name, fd):
    print(f"{name:<30}", end=" ", file=fd)

    sum_us = total_time_ns[column_name].sum() / 1000
    average_us = total_time_ns[column_name].mean() / 1000
    p10_us = total_time_ns[column_name].quantile(q=0.1) / 1000
    p25_us = total_time_ns[column_name].quantile(q=0.25) / 1000
    p50_us = total_time_ns[column_name].quantile(q=0.5) / 1000
    p90_us = total_time_ns[column_name].quantile(q=0.9) / 1000
    p99_us = total_time_ns[column_name].quantile(q=0.99) / 1000
    slowest_us = total_time_ns[column_name].max() / 1000

    for number in [p10_us, p25_us, p50_us, p90_us, p99_us, slowest_us, average_us, sum_us]:
        number = f"{number:_.0f}"
        number = number.replace("_", "\\;")
        print(f"& {number:>8}", end=" ", file=fd)
    print("\\\\", file=fd)

configuration_runtimes_table_txt = out_path("configuration-runtimes-table.txt")
with open(configuration_runtimes_table_txt, 'w', encoding='utf-8') as fd:
    print_table_header(fd)
    if has_ep:
        print_table_row("\\texttt{" + BEST_CONFIG_WITH_EP_PRETTY + "}", "best_config_with_ep", fd)
        print_table_row("\\texttt{EP Oracle}", "oracle_with_ep", fd)
    print_table_row("\\texttt{" + BEST_CONFIG_SANS_PIP_PRETTY + "}", "best_config_sans_pip", fd)
    print("\\midrule", file=fd)
    print_table_row(f"\\texttt{{{BEST_CONFIG_JUST_WITHOUT_PIP_PRETTY}}}", "best_config_just_without_pip", fd)
    print_table_row(f"\\texttt{{{BEST_CONFIG_PRETTY}}}", "best_config", fd)
    print("\\bottomrule", file=fd)
    print("\\end{tabular}", file=fd)

if has_ep:
    print(f"Speedup {BEST_CONFIG_WITH_EP_PRETTY} vs {BEST_CONFIG_SANS_PIP_PRETTY}:", total_time_ns["best_config_with_ep"].sum() / total_time_ns["best_config_sans_pip"].sum())
    print(f"Speedup EP Oracle vs {BEST_CONFIG_SANS_PIP_PRETTY}:", total_time_ns["oracle_with_ep"].sum() / total_time_ns["best_config_sans_pip"].sum())
    print(f"Speedup EP Oracle vs {BEST_CONFIG_PRETTY}:", total_time_ns["oracle_with_ep"].sum() / total_time_ns["best_config"].sum())

    #slowest_with_ep = total_time_ns[total_time_ns["oracle_with_ep"] > 1e9]
    #slowest_with_ep.to_csv(out_path("slowest_with_ep.csv"))

print(f"Speedup {BEST_CONFIG_PRETTY} vs {BEST_CONFIG_SANS_PIP_PRETTY}:", total_time_ns["best_config_sans_pip"].sum() / total_time_ns["best_config"].sum())
print(f"Speedup {BEST_CONFIG_PRETTY} vs {BEST_CONFIG_JUST_WITHOUT_PIP_PRETTY}:", total_time_ns["best_config_just_without_pip"].sum() / total_time_ns["best_config"].sum())

# =========== Drawing in absolute numbers =====================
x = range(len(total_time_ns))

# =========== Make csv showing files where the EP oracle is faster than the best_sans_pip config =================

if has_ep:
    oracle_better = pd.DataFrame({"BestSansPip": total_time_ns["best_config_sans_pip"], "OracleEP": total_time_ns["oracle_with_ep"]})
    oracle_better["Diff"] = oracle_better["BestSansPip"] - oracle_better["OracleEP"]
    oracle_better["EPConfiguration"] = oracle_ep_data["Configuration"]

    for cfile in oracle_better.index:
        if cfile in total_time_ns.index:
            oracle_better.loc[cfile, "Index"] = total_time_ns.index.get_loc(cfile)

    oracle_better = oracle_better[oracle_better["Diff"] >= 0]
    oracle_better.to_csv(out_path("ep_oracle_faster_than_bsp.csv"))

# ============== Drawing best config without PIP ratio Oracle with EP ====================
if has_ep:
    total_time_ns.sort_values("best_config_sans_pip", ascending=True, inplace=True)

    plt.figure(figsize=(7,3))

    data = pd.DataFrame({"x": range(len(total_time_ns)), "ratio": (total_time_ns["best_config_sans_pip"]/total_time_ns["oracle_with_ep"])})
    data_above = data[data["ratio"] > 1]
    data_below = data[data["ratio"] <= 1]

    sns.scatterplot(data=data_above, x="x", y="ratio", color="red", marker=".", edgecolor=None, alpha=0.3, label="EP Oracle is faster", zorder=10)
    sns.scatterplot(data=data_below, x="x", y="ratio", color="blue", marker=".", edgecolor=None, alpha=0.3, label=BEST_CONFIG_SANS_PIP_PRETTY + " is faster", zorder=10)

    plt.ylabel("Runtime ratio \n" + BEST_CONFIG_SANS_PIP_PRETTY + " / EP Oracle")
    plt.xlabel("Files sorted by " + BEST_CONFIG_SANS_PIP_PRETTY + " solving time")

    plt.grid(zorder=0)
    plt.gca().axvline(1000, linewidth=1, zorder=3, color='#444')
    lim_1000 = total_time_ns["best_config_sans_pip"].iloc[1000]/1000
    plt.gca().text(660, 4.2, s=f"$< {lim_1000:.0f}\\mu$s")
    plt.gca().axvline(2000, linewidth=1, zorder=3, color='#444')
    lim_2000 = total_time_ns["best_config_sans_pip"].iloc[2000]/1000
    plt.gca().text(1600, 4.2, s=f"$< {lim_2000:.0f}\\mu$s")
    plt.gca().axvline(3000, linewidth=1, zorder=3, color='#444')
    lim_3000 = total_time_ns["best_config_sans_pip"].iloc[3000]/1000
    plt.gca().text(2550, 4.2, s=f"$< {lim_3000:.0f}\\mu$s")

    plt.gca().axhline(1, linewidth=1, zorder=3, color='black')
    plt.legend(loc='upper center')
    plt.tight_layout(pad=0.2)
    plt.savefig(out_path("ip_sans_pip_vs_ep_oracle_ratio.pdf"))

# ================== Default best (with PIP) ratio against default best without pip ========================
total_time_ns.sort_values("best_config_just_without_pip", ascending=True, inplace=True)

slow_best_config_just_without_pip = total_time_ns[total_time_ns["best_config_just_without_pip"] > 1e9]
slow_best_config_just_without_pip.to_csv(out_path("slow_best_config_just_without_pip.csv"))

plt.figure(figsize=(7,3))

data = pd.DataFrame({"x": range(len(total_time_ns)), "y": (total_time_ns["best_config"]/total_time_ns["best_config_just_without_pip"])*1})
data_above = data[data["y"] > 1]
data_below = data[data["y"] <= 1]

plt.scatter(x=data_above["x"], y=data_above["y"], color="red", marker=".", alpha=0.3, label=f"{BEST_CONFIG_JUST_WITHOUT_PIP_PRETTY} is faster", zorder=100)
plt.scatter(x=data_below["x"], y=data_below["y"], color="blue", marker=".", alpha=0.3, label=f"{BEST_CONFIG} is faster", zorder=100)
plt.xlabel("Files sorted by " + BEST_CONFIG_JUST_WITHOUT_PIP_PRETTY + " solving time")
plt.ylabel("Runtime ratio\n" + BEST_CONFIG_PRETTY + " / " + BEST_CONFIG_JUST_WITHOUT_PIP_PRETTY)

plt.grid(zorder=0)
plt.gca().axvline(1000, linewidth=1, zorder=3, color='#444')
lim_1000 = total_time_ns["best_config_just_without_pip"].iloc[1000]/1000
plt.gca().text(660, 0.05, s=f"$< {lim_1000:.0f}\\mu$s")
plt.gca().axvline(2000, linewidth=1, zorder=3, color='#444')
lim_2000 = total_time_ns["best_config_just_without_pip"].iloc[2000]/1000
plt.gca().text(1600, 0.05, s=f"$< {lim_2000:.0f}\\mu$s")
plt.gca().axvline(3000, linewidth=1, zorder=3, color='#444')
lim_3000 = total_time_ns["best_config_just_without_pip"].iloc[3000]/1000
plt.gca().text(2550, 0.05, s=f"$< {lim_3000:.0f}\\mu$s")

plt.gca().axhline(1, linewidth=1, zorder=3, color='black')
plt.legend()
#plt.gca().yaxis.set_major_formatter(mtick.PercentFormatter())
plt.tight_layout(pad=0.2)
plt.savefig(out_path("pip_vs_best_just_without_pip_ratio.pdf"))

print(f" ==== Printing statistics about {BEST_CONFIG_PRETTY} vs {BEST_CONFIG_JUST_WITHOUT_PIP_PRETTY} ======")

print(f"Using {BEST_CONFIG_PRETTY}: Percentage of total runtime left when ignoring the 3000 fastest files: ", total_time_ns["best_config"].iloc[3000:].sum() / total_time_ns["best_config"].sum())

slower_with_pip = total_time_ns["best_config"] > total_time_ns["best_config_just_without_pip"]
slowdown = total_time_ns["best_config"] / total_time_ns["best_config_just_without_pip"] - 1
speedup = total_time_ns["best_config_just_without_pip"] / total_time_ns["best_config"]

print(f"Looking at files where {BEST_CONFIG_PRETTY} is slower than {BEST_CONFIG_JUST_WITHOUT_PIP_PRETTY}")
print(f"Number of files slower with {BEST_CONFIG_PRETTY}:", sum(slower_with_pip))
print("Average slowdown:", slowdown[slower_with_pip].mean())
print("Largest slowdown after 1000:", slowdown.iloc[1000:].max())

slowdown_after_3000 = slowdown.iloc[3000:]
print("Num slowdowns after 3000:", (slowdown_after_3000 > 0).sum())
print("Average slowdown after 3000:", slowdown_after_3000[slowdown_after_3000 > 0].mean())
print("Largest slowdown after 3000:", slowdown_after_3000.max())

speedup_after_3000 = speedup.iloc[3000:]
print("Num speedups after 3000:", (speedup_after_3000 > 1).sum())
print("Average speedup after 3000:", speedup_after_3000[speedup_after_3000 > 1].mean())

patalogical = total_time_ns["best_config_just_without_pip"].idxmax()
print(f"Slowest file with {BEST_CONFIG_JUST_WITHOUT_PIP_PRETTY}", patalogical)
print("Pathalogical", BEST_CONFIG_PRETTY, total_time_ns.loc[patalogical, "best_config"] / 1000, "us")
print("Pathalogical", BEST_CONFIG_JUST_WITHOUT_PIP_PRETTY, total_time_ns.loc[patalogical, "best_config_just_without_pip"] / 1000, "us")
print("Pathalogical", BEST_CONFIG_SANS_PIP_PRETTY, total_time_ns.loc[patalogical, "best_config_sans_pip"] / 1000, "us")

#if has_ep:
#    print(" ==== NOW COMPARING PIP AGAINST OracleEP ==== ")

#    plt.figure(figsize=(7,3))
#    ratio = (total_time_ns["best_config"]/total_time_ns["oracle_with_ep"]-1)*1
#    plt.scatter(x=range(len(total_time_ns)), y=ratio, color="blue", marker=".", alpha=0.3, label="IP+WL(FIFO)+PIP")
#    print("Slower with PIP than OracleEP:", ratio[ratio > 1.5])

#    plt.xlabel("File number")

#    plt.grid()
#    plt.legend()
#    plt.tight_layout(pad=0.2)
#    plt.savefig(out_path("default_best_ratio_oracle_with_ep.pdf"))


# ========== Make boxplot of runtimes with and without PIP ==============================
#sns.set_theme(style="whitegrid", palette=None)
#plt.figure(figsize=(7,3))

#df0 = pd.DataFrame({"TotalTime[us]": total_time_ns["best_config"]/1000, "Config": "IP+WL(FIFO)+PIP" })
#df1 = pd.DataFrame({"TotalTime[us]": total_time_ns["best_config_sans_pip"]/1000, "Config": "IP+WL(FIFO)" })
#best_data = pd.concat([df0.reset_index(drop=True), df1.reset_index(drop=True)], axis="rows")

#sns.boxplot(data=best_data, x="TotalTime[us]", y="Config", showmeans=True, meanline=True, meanprops={"color": ".1"},
#                color=".8", linecolor=".1", fliersize="5")

#plt.xscale("log")
#plt.tight_layout(pad=0.2)
#plt.savefig(out_path("best_config_with_and_without_pip.pdf"))

# ========== Make scatterplot between PIP and not PIP ===============================

#plt.figure(figsize=(7,7))
#plt.scatter(x=total_time_ns["#PointerObjects"], y=total_time_ns["best_config_sans_pip"]-total_time_ns["best_config"], marker=".", color="red")
#plt.scatter(x=total_time_cutoff["#PointerObjects"], y=total_time_cutoff["best_config_sans_pip"], marker=".", color="blue")

#def plot_diagonal_line(ax):
#    lims = [
#        np.min([ax.get_xlim(), ax.get_ylim()]),  # min of both axes
#        np.max([ax.get_xlim(), ax.get_ylim()]),  # max of both axes
#    ]

    # now plot both limits against eachother
#    ax.plot(lims, lims, 'k-', alpha=0.75, zorder=0)
#    ax.set_aspect('equal')
#    ax.set_xlim(lims)
#    ax.set_ylim(lims)

#plot_diagonal_line(plt.gca())
#plt.savefig(out_path("scatterplot_with_vs_without_pip.pdf"))


# ====== Plot how runtime scales against problem size ============
#
plt.figure(figsize=(7,3))
plt.scatter(x=total_time_ns["#PointerObjects"], y=total_time_ns["best_config"] / 1e6, alpha=0.6, marker=".", color="red")
plt.xlabel("#Constraint Variables $V$")
plt.ylabel("Solver runtime [ms]")
# plt.ylim((0,1e8))
plt.tight_layout(pad=0.2)
plt.savefig(out_path("runtime_vs_problem_size.pdf"))

# ===== Memory usage (representational overhead) =============

#def draw_memory_use(data, file_out):
#    plt.figure(figsize=(7,3))
    #memory_use = data["#BaseConstraints"] + data["#SupersetConstraints"] + data["#StoreConstraints"] + data["#LoadConstraints"] + data["#FunctionCallConstraints"]
#    plt.scatter(x=data["#PointerObjects"], y=data["#ExplicitPointees"], marker=".", color="red")
# plt.ylim((0,.5e8))
#    plt.xlabel("#Constraint Variables in $V$")
#    plt.ylabel("#Explicit pointees")
#    plt.tight_layout(pad=0.2)
#    plt.savefig(file_out)

#draw_memory_use(best_config_data, "results/explicit_pointees_best.pdf")
#draw_memory_use(best_config_with_ep_data, "results/explicit_pointees_best_ep.pdf")

# ===== Memory usage table ===============================

def print_explicit_pointees_table_header(fd):
    print("\\begin{tabular}{lrrrrrrr}", file=fd)
    print("\\toprule", file=fd)
    print(" & \\multicolumn{7}{c}{Number of explicit pointees} \\\\", file=fd)
    print("\\cline{2-8}", file=fd)
    print("Configuration & p10 & p25 & p50 & p90 & p99 & Max & Mean \\\\", file=fd)
    print("\\midrule", file=fd)

def print_explicit_pointees_table_row(name, config_name, fd):
    print(f"{name:<30}", end=" ", file=fd)

    explicit_pointees = all_configs.loc[all_configs["Configuration"]==config_name, "#ExplicitPointees"]
    average = explicit_pointees.mean()
    p10 = explicit_pointees.quantile(q=0.1)
    p25 = explicit_pointees.quantile(q=0.25)
    p50 = explicit_pointees.quantile(q=0.5)
    p90 = explicit_pointees.quantile(q=0.9)
    p99 = explicit_pointees.quantile(q=0.99)
    slowest = explicit_pointees.max()

    for number in [p10, p25, p50, p90, p99, slowest, average]:
        number = f"{number:_.0f}"
        number = number.replace("_", "\\;")
        print(f"& {number:>8}", end=" ", file=fd)
    print("\\\\", file=fd)

configuration_memory_usage_table_txt = out_path("configuration-memory-usage-table.txt")
with open(configuration_memory_usage_table_txt, 'w', encoding='utf-8') as fd:
    print_explicit_pointees_table_header(fd)
    if has_ep:
        print_explicit_pointees_table_row("\\texttt{" + BEST_CONFIG_WITH_EP_PRETTY + "}", BEST_CONFIG_WITH_EP, fd)
    print_explicit_pointees_table_row("\\texttt{" + BEST_CONFIG_JUST_WITHOUT_PIP_PRETTY + "}", BEST_CONFIG_JUST_WITHOUT_PIP, fd)
    print_explicit_pointees_table_row("\\texttt{" + BEST_CONFIG_SANS_PIP_PRETTY + "}", BEST_CONFIG_SANS_PIP, fd)
    print_explicit_pointees_table_row("\\texttt{" + BEST_CONFIG_PRETTY + "}", BEST_CONFIG, fd)
    print("\\bottomrule", file=fd)
    print("\\end{tabular}", file=fd)

# print("Most explicit pointers using", BEST_CONFIG_JUST_WITHOUT_PIP_PRETTY, ":", all_configs.loc[all_configs.loc[all_configs["Configuration"]==BEST_CONFIG_JUST_WITHOUT_PIP, "#ExplicitPointees"].idxmax(), "cfile"])
