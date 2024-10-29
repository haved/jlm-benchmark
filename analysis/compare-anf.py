#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import seaborn as sns
import numpy as np

file_data = pd.read_csv("statistics-out/file_data.csv")
all_configs = pd.read_csv("statistics-out/file_config_data.csv")

# Check that all cfiles have been tested with all 212 configurations
configs_per_cfile = all_configs.groupby("cfile")["Configuration"].nunique()
missing_configs = configs_per_cfile[configs_per_cfile != 180]
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
BEST_CONFIG_WITH_OVS = "IP_OVS_Solver=Worklist_Policy=FirstInFirstOut_PIP"
BEST_CONFIG_SANS_PIP = "IP_Solver=Worklist_Policy=FirstInFirstOut_LazyCD_DP" #"IP_Solver=Worklist_Policy=FirstInFirstOut"
BEST_CONFIG_JUST_WITHOUT_PIP = "IP_Solver=Worklist_Policy=FirstInFirstOut"
BEST_CONFIG_WITH_EP = "EP_OVS_Solver=Worklist_Policy=LeastRecentlyFired_OnlineCD"

BEST_CONFIG_PRETTY = "IP+WL(FIFO)+PIP"
BEST_CONFIG_SANS_PIP_PRETTY = "IP+WL(FIFO)+LCD+DP"
BEST_CONFIG_JUST_WITHOUT_PIP_PRETTY = "IP+WL(FIFO)"

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
best_config_with_ovs_data = add_column_with_config(BEST_CONFIG_WITH_OVS, "best_config_with_ovs")
add_column_with_config(BEST_CONFIG_SANS_PIP, "best_config_sans_pip")
add_column_with_config(BEST_CONFIG_JUST_WITHOUT_PIP, "best_config_just_without_pip")
add_column_with_config("IP_Solver=Worklist_Policy=FirstInFirstOut", "ip_fifo")
best_config_with_ep_data = add_column_with_config(BEST_CONFIG_WITH_EP, "best_config_with_ep")

# Among all rows in data, picks the fastest TotalTime per cfile and uses that
def add_oracle_config_per_cfile(data, column_name):
    idx_per_cfile = data.groupby("cfile")["TotalTime[ns]"].idxmin()
    data = data.loc[idx_per_cfile, :]
    add_column_to_total_time(data, column_name)
    return data.set_index("cfile")

all_configs_sans_pip = all_configs[~all_configs["Configuration"].str.contains("PIP")]
all_configs_sans_naive = all_configs[~all_configs["Configuration"].str.contains("Naive")]
all_configs_sans_pip_or_naive = all_configs_sans_naive[~all_configs_sans_naive["Configuration"].str.contains("PIP")]
all_configs_with_ep = all_configs[all_configs["Configuration"].str.contains("EP_")]
all_configs_only_naive = all_configs[all_configs["Configuration"].str.contains("Naive")]

add_oracle_config_per_cfile(all_configs, "oracle")
add_oracle_config_per_cfile(all_configs_sans_pip, "oracle_sans_pip")
add_oracle_config_per_cfile(all_configs_sans_naive, "oracle_sans_naive")
add_oracle_config_per_cfile(all_configs_sans_pip_or_naive, "oracle_sans_pip_or_naive")
oracle_ep_data = add_oracle_config_per_cfile(all_configs_with_ep, "oracle_with_ep")
add_oracle_config_per_cfile(all_configs_only_naive, "oracle_only_naive")

total_time_ns.sort_values("best_config_sans_pip", ascending=True, inplace=True)

def print_table_header():
    us = "\\unit{\\micro\\second}"
    print(" & \\multicolumn{8}{c}{" + f"Solver Runtime [{us}]" + "} \\\\")
    print("Configuration & p10 & p25 & p50 & p90 & p99 & Max & Mean & Sum\\\\")
    print("\\midrule")

def print_table_row(name, column_name):
    print(f"{name:<30}", end=" ")

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
        print(f"& {number:>8}", end=" ")
    print("\\\\")

print_table_header()
#print_table_row("Oracle", "oracle")
#print_table_row("\\texttt{IP+WL(FIFO)+PIP}", "best_config")
#print_table_row("Oracle without \\texttt{PIP}", "oracle_sans_pip")
#print_table_row("Oracle without \\texttt{Naive}", "oracle_sans_naive")
#print_table_row("Oracle with \\texttt{Naive}", "oracle_only_naive")
#print_table_row("Oracle without \\texttt{PIP} or \\texttt{Naive}", "oracle_sans_pip_or_naive")
print_table_row("\\texttt{" + BEST_CONFIG_SANS_PIP_PRETTY + "}", "best_config_sans_pip")
print_table_row("\\texttt{EP} Oracle", "oracle_with_ep")
print_table_row("\\texttt{EP+OVS+WL(LRF)+OCD}", "best_config_with_ep")

x = range(len(total_time_ns))

print("C files:", len(total_time_ns))
print("Mean speedup:", (total_time_ns["oracle_with_ep"] / total_time_ns["best_config"]).mean())
print("Total speedup:", total_time_ns["oracle_with_ep"].sum() / total_time_ns["best_config"].sum())

# =========== Drawing in absolute numbers =====================

plt.figure(figsize=(7,3))
plt.yscale("log")

sns.scatterplot(x=range(len(total_time_ns)), y=total_time_ns["best_config_sans_pip"]/1000, color="blue", marker=".", edgecolor=None, alpha=0.3, label=BEST_CONFIG_SANS_PIP_PRETTY, zorder=10) #IP+WL(FIFO)")
sns.scatterplot(x=range(len(total_time_ns)), y=total_time_ns["oracle_with_ep"]/1000, color="red", marker=".", edgecolor=None, alpha=0.3, label="EP Oracle", zorder=10)

plt.ylabel("Solving time [$\\mu$s]")
plt.xlabel("Files sorted by " + BEST_CONFIG_SANS_PIP_PRETTY + " solving time")
# plt.margins(x=10)

plt.grid()
plt.legend()
plt.tight_layout(pad=0.2)
plt.savefig("results/ip_vs_ep_oracle_absolute.pdf")

# =========== Make csv showing best oracle choice =================
oracle_better = pd.DataFrame({"BestSansPip": total_time_ns["best_config_sans_pip"], "OracleEP": total_time_ns["oracle_with_ep"]})
oracle_better["Diff"] = oracle_better["BestSansPip"] - oracle_better["OracleEP"]
oracle_better["EPConfiguration"] = oracle_ep_data["Configuration"]

print(oracle_better)
for cfile in oracle_better.index:
    if cfile in total_time_ns.index:
        oracle_better.loc[cfile, "Index"] = total_time_ns.index.get_loc(cfile)

oracle_better = oracle_better[oracle_better["Diff"] >= 0]
oracle_better.to_csv("results/oracle_better.csv")

# ============== Drawing best config without PIP ratio Oracle with EP ====================
#x = np.linspace(0, 1, len(total_time_cutoff))
plt.figure(figsize=(7,3))

data = pd.DataFrame({"x": range(len(total_time_ns)), "ratio": (total_time_ns["best_config_sans_pip"]/total_time_ns["oracle_with_ep"])*100})
data_above = data[data["ratio"] > 100]
data_below = data[data["ratio"] <= 100]

sns.scatterplot(data=data_above, x="x", y="ratio", color="red", marker=".", alpha=0.8, label="EP Oracle is faster", zorder=10)
sns.scatterplot(data=data_below, x="x", y="ratio", color="blue", marker=".", alpha=0.8, label=BEST_CONFIG_SANS_PIP_PRETTY + " is faster", zorder=10)

plt.ylabel("Runtime ratio \n" + BEST_CONFIG_SANS_PIP_PRETTY + " / EP Oracle")
plt.xlabel("Files sorted by " + BEST_CONFIG_SANS_PIP_PRETTY + " solving time")
plt.gca().yaxis.set_major_formatter(mtick.PercentFormatter())

plt.grid(zorder=0)
plt.gca().axhline(100, linewidth=1, zorder=3, color='black')
plt.tight_layout(pad=0.2)
plt.savefig("results/ip_vs_ep_oracle_ratio.pdf")

# =========== Raito plot with OVS ===================
plt.figure(figsize=(7,3))

data = pd.DataFrame({"x": range(len(total_time_ns)), "ratio": (total_time_ns["best_config_with_ovs"]/total_time_ns["best_config"]-1)*100})
data_above = data[data["ratio"] > 0]
data_below = data[data["ratio"] <= 0]

sns.scatterplot(data=data_above, x="x", y="ratio", color="red", marker=".", alpha=0.8, label="Without OVS is faster")
sns.scatterplot(data=data_below, x="x", y="ratio", color="blue", marker=".", alpha=0.8, label="With OVS is faster")

plt.xlabel("File number")

plt.grid()
plt.tight_layout(pad=0.2)
plt.savefig("results/best_config_with_ovs_ratio_best_config.pdf")

# ======================= Now we wish to compare PIP and no PIP =================================
print(" ==== NOW COMPARING PIP AGAINST NO PIP ==== ")
total_time_ns.sort_values("best_config", ascending=True, inplace=True)

print_table_header()
#print_table_row("Oracle without \\texttt{PIP}", "oracle_sans_pip")
#print_table_row("Oracle without \\texttt{Naive}", "oracle_sans_naive")
#print_table_row("Oracle with \\texttt{Naive}", "oracle_only_naive")
#print_table_row("Oracle without \\texttt{PIP} or \\texttt{Naive}", "oracle_sans_pip_or_naive")
#print_table_row("\\texttt{ImP+WL=FIFO}", "best_config_sans_pip")
#print_table_row("Oracle without \\texttt{PIP}", "oracle_sans_pip_or_naive")
print_table_row(BEST_CONFIG_SANS_PIP, "best_config_sans_pip")
print_table_row("\\texttt{IP+WL(FIFO)}", "ip_fifo")
print_table_row("\\texttt{IP+WL(FIFO)+PIP}", "best_config")

# =================== Default best (with PIP) ratio against default best without pip =============
plt.figure(figsize=(7,3))
#plt.yscale("log")

plt.scatter(x=range(len(total_time_ns)), y=(total_time_ns["best_config"]/total_time_ns["best_config_sans_pip"])*100, color="blue", marker=".", alpha=0.3, label="IP+WL(FIFO)+PIP")
plt.xlabel("File number")

plt.grid()
plt.legend()
plt.tight_layout(pad=0.2)
plt.savefig("results/pip_vs_ip_best_ratio.pdf")

# =================== Default best (with PIP) ratio against default best without pip =============
plt.figure(figsize=(7,3))
#plt.yscale("log")

data = pd.DataFrame({"x": range(len(total_time_ns)), "y": (total_time_ns["best_config"]/total_time_ns["best_config_just_without_pip"])*100})
data_above = data[data["y"] > 100]
data_below = data[data["y"] <= 100]

plt.scatter(x=data_above["x"], y=data_above["y"], color="red", marker=".", alpha=0.3, label="IP+WL(FIFO) is faster", zorder=100)
plt.scatter(x=data_below["x"], y=data_below["y"], color="blue", marker=".", alpha=0.3, label="IP+WL(FIFO)+PIP is faster", zorder=100)
plt.xlabel("Files sorted by " + BEST_CONFIG_PRETTY + " solving time")
plt.ylabel("Runtime ratio\n" + BEST_CONFIG_PRETTY + " / " + BEST_CONFIG_JUST_WITHOUT_PIP_PRETTY)

plt.grid(zorder=0)
plt.gca().axhline(100, linewidth=1, zorder=3, color='black')
plt.legend()
plt.gca().yaxis.set_major_formatter(mtick.PercentFormatter())
plt.tight_layout(pad=0.2)
plt.savefig("results/pip_vs_ip_ratio.pdf")

print(" ==== NOW COMPARING PIP AGAINST OracleEP ==== ")

plt.figure(figsize=(7,3))
ratio = (total_time_ns["best_config"]/total_time_ns["oracle_with_ep"]-1)*100
plt.scatter(x=range(len(total_time_ns)), y=ratio, color="blue", marker=".", alpha=0.3, label="IP+WL(FIFO)+PIP")
print("Slowfile:", ratio[ratio > 150])

#plt.scatter(x=x, y=total_time_cutoff["best_config"]/1000, color="blue", marker=".", alpha=0.3, label="IP+WL(FIFO)+PIP")
#plt.scatter(x=x, y=total_time_cutoff["best_config_sans_pip"]/1000, color="green", marker=".", alpha=0.3, label=BEST_CONFIG_SANS_PIP)
# plt.scatter(x=x, y=total_time_cutoff["ip_fifo"]/1000, color="red", marker=".", alpha=0.3, label="IP+WL(FIFO)")

#plt.ylabel("Solving time [$\\mu$s]")
plt.xlabel("File number")
# plt.margins(x=10)

plt.grid()
plt.legend()
plt.tight_layout(pad=0.2)
plt.savefig("results/default_best_ratio_oracle_with_ep.pdf")


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

plt.figure(figsize=(7,7))
plt.scatter(x=total_time_ns["#PointerObjects"], y=total_time_ns["best_config_sans_pip"]-total_time_ns["best_config"], marker=".", color="red")
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


# ====== Plot scaling ============
#
plt.figure(figsize=(7,3))
plt.scatter(x=total_time_ns["#PointerObjects"], y=total_time_ns["best_config"] / 1e6, alpha=0.6, marker=".", color="red")
plt.xlabel("#Constraint Variables $V$")
plt.ylabel("Solver runtime [ms]")
# plt.ylim((0,1e8))
plt.tight_layout(pad=0.2)
plt.savefig("results/runtime_vs_problem_size.pdf")

# ===== Memory usage (representational overhead) =============

def draw_memory_use(data, file_out):
    plt.figure(figsize=(7,3))
    #memory_use = data["#BaseConstraints"] + data["#SupersetConstraints"] + data["#StoreConstraints"] + data["#LoadConstraints"] + data["#FunctionCallConstraints"]
    plt.scatter(x=data["#PointerObjects"], y=data["#ExplicitPointees"], marker=".", color="red")
# plt.ylim((0,.5e8))
    plt.xlabel("#Constraint Variables in $V$")
    plt.ylabel("#Explicit pointees")
    plt.tight_layout(pad=0.2)
    plt.savefig(file_out)

draw_memory_use(best_config_data, "results/explicit_pointees_best.pdf")
draw_memory_use(best_config_with_ep_data, "results/explicit_pointees_best_ep.pdf")

# ===== Percentage escaped =============

filtered = best_config_data # [best_config_data["#PointerObjects"] > 30]

escaped_ratio = (filtered["#CanPointsEscaped"] + filtered["#CantPointsEscaped"]) / filtered["#MemoryPointerObjects"]
plt.figure(figsize=(7,3))
plt.hist(x=escaped_ratio, bins=20)
plt.savefig("results/escaped_ratio.pdf")

points_to_external_ratio = filtered["#PointsToExternalRelations"] / filtered["#PointerObjectsCanPoint"]
plt.figure(figsize=(7,3))
plt.hist(x=points_to_external_ratio, bins=20)
plt.savefig("results/ptexternal_ratio.pdf")

plt.figure(figsize=(7,7))
data=pd.crosstab(pd.cut(escaped_ratio, 10), pd.cut(points_to_external_ratio, 10))
ax = sns.heatmap(data=data, annot=True, fmt='.6g')
ax.invert_yaxis()
plt.tight_layout()
plt.ylabel("Escape %")
plt.xlabel("PointsToAllEscaped %")
plt.savefig("results/heatmap.pdf")

print(escaped_ratio[escaped_ratio > 0.96])

#print(total_time_ns[total_time_ns["best_config"]>1e8])

print(" ==== Some final stats ==== ")
print("Number of configurations:", len(all_configs["Configuration"].unique()))
print("Number of configurations with IP:", len(all_configs.loc[all_configs["Configuration"].str.contains("IP_"), "Configuration"].unique()))
print("Number of configurations with EP:", len(all_configs.loc[all_configs["Configuration"].str.contains("EP_"), "Configuration"].unique()))
