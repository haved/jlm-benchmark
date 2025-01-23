#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import seaborn as sns
import numpy as np
import sys

CONFIG_A = "IP_Solver=Worklist_Policy=FirstInFirstOut_PIP"
CONFIG_B = "IP_Solver=Wave"

file_data = pd.read_csv("statistics-out/file_data.csv")
all_configs = pd.read_csv("statistics-out/file_config_data.csv")

# Remove empty files
file_data = file_data[file_data["#RvsdgNodes"] > 0]
all_configs = all_configs[all_configs["#RvsdgNodes"] > 0]

config_a = all_configs[all_configs["Configuration"] == CONFIG_A].set_index("cfile")
config_b = all_configs[all_configs["Configuration"] == CONFIG_B].set_index("cfile")

if len(config_a) == 0:
    print(f"No file is solved with CONFIG_A: {CONFIG_A}")
    sys.exit(1)

if len(config_b) == 0:
    print(f"No file is solved with CONFIG_B: {CONFIG_B}")
    sys.exit(1)

# Check that the set of files solved by each configuration is identical
for cfile in set(config_a.index).symmetric_difference(config_b.index):
    print(f"cfile only solved using one of the two configurations: {cfile}")

print(f"Config A: {CONFIG_A}")
print(f"Config B: {CONFIG_B}")

def print_table_header():
    header_line = f"| {'Config':>10} | {'p10':>10} | {'p25':>10} "
    header_line += f"| {'p50':>10} | {'p90':>10} | {'p99':>10} | {'Max':>10} | {'Mean':>10} | {'Sum':>10} |"
    print(header_line)
    print("-" * len(header_line))

def print_table_row(name, total_time_ns):
    print(f"| {name:>10}", end=" |")

    p10_us = total_time_ns.quantile(q=0.1) / 1000
    p25_us = total_time_ns.quantile(q=0.25) / 1000
    p50_us = total_time_ns.quantile(q=0.5) / 1000
    p90_us = total_time_ns.quantile(q=0.9) / 1000
    p99_us = total_time_ns.quantile(q=0.99) / 1000
    slowest_us = total_time_ns.max() / 1000
    average_us = total_time_ns.mean() / 1000
    sum_us = total_time_ns.sum() / 1000

    for number in [p10_us, p25_us, p50_us, p90_us, p99_us, slowest_us, average_us, sum_us]:
        number = f"{number:_.0f} us"
        print(f" {number:>10}", end=" |")
    print()

print_table_header()
print_table_row("A", config_a["TotalTime[ns]"])
print_table_row("B", config_b["TotalTime[ns]"])

both = pd.DataFrame({"A_Time[ns]": config_a["TotalTime[ns]"], "B_Time[ns]": config_b["TotalTime[ns]"]})
both.sort_values("A_Time[ns]", ascending=True, inplace=True)

# Compare solver runtime per file
delta = both["A_Time[ns]"] - both["B_Time[ns]"]
a_faster = -delta[delta < 0]
b_faster = delta[delta > 0]
print(f"Config A is faster than Config B on {len(a_faster)} files")
if len(a_faster) != 0:
    print(f"On average, it is {a_faster.mean()/1000:_.0f} us faster")
    a_faster_cfile = a_faster.idxmax()
    a_faster_a_time = both.loc[a_faster_cfile, 'A_Time[ns]']
    a_faster_b_time = both.loc[a_faster_cfile, 'B_Time[ns]']
    print(f"The biggest difference is seen on file {a_faster_cfile}:",
          f"{a_faster_a_time/1000:_.0f} us vs {a_faster_b_time/1000:_.0f} us")

print(f"Config B is faster than Config B on {len(b_faster)} files")
if len(b_faster) != 0:
    print(f"On average, it is {b_faster.mean()/1000:_.0f} us faster")
    b_faster_cfile = b_faster.idxmax()
    b_faster_a_time = both.loc[b_faster_cfile, 'A_Time[ns]']
    b_faster_b_time = both.loc[b_faster_cfile, 'B_Time[ns]']
    print(f"The biggest difference is seen on file {b_faster_cfile}:",
          f"{b_faster_a_time/1000:_.0f} us vs {b_faster_b_time/1000:_.0f} us")

# Make a logarithmic solver runtime plot sorted by config a
plt.figure(figsize=(7,3))
plt.yscale("log")
sns.scatterplot(x=range(len(both)), y=both["A_Time[ns]"]/1000, color="blue", marker=".", edgecolor=None, alpha=0.3, label=CONFIG_A, zorder=10)
sns.scatterplot(x=range(len(both)), y=both["B_Time[ns]"]/1000, color="red", marker=".", edgecolor=None, alpha=0.3, label=CONFIG_B, zorder=10)

plt.ylabel("Solving time [$\\mu$s]")
plt.xlabel(f"Files sorted by {CONFIG_A} solving time")

plt.grid()
plt.savefig("quick-compare.pdf")
plt.show()
