#!/usr/bin/env python3

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

runtimes = pd.read_csv("runtimes2.csv", index_col=0)

print(runtimes.describe())

# Remove very small and very large tests
#runtimes = runtimes[runtimes.index != "floyd-warshall"]
#runtimes = runtimes[runtimes.index != "atax"]
#runtimes = runtimes[runtimes.index != "bicg"]
#runtimes = runtimes[runtimes.index != "mvt"]
#runtimes = runtimes[runtimes.index != "durbin"]
#runtimes = runtimes[runtimes.index != "gemver"]
#runtimes = runtimes[runtimes.index != "gesummv"]
#runtimes = runtimes[runtimes.index != "trisolv"]
#runtimes = runtimes[runtimes.index != "deriche"]
#runtimes = runtimes[runtimes.index != "jacobi-1d"]

# Only care about certain columns
columns = ["clang_O0", "jlm_opt_O3", "jlm_opt_andersen_O3", "jlm_opt_steensgaard_O3", "mem2reg_only", "clang_O3"]
#columns = ["mem2reg_only", "mem2reg_jlm_opt_O3", "mem2reg_jlm_opt_andersen_O3", "mem2reg_jlm_opt_steensgaard_O3"]
runtimes = runtimes[columns]

runtimes_flat = pd.DataFrame()

configurations = runtimes.columns
for benchmark in runtimes.index:
    times = runtimes.loc[benchmark, configurations]

    # Normalize bar length
    # times = times / times.max()

    added_df = pd.DataFrame({"benchmark": benchmark, "configuration": configurations, "runtime": times})
    runtimes_flat = pd.concat([runtimes_flat, added_df])

# add geometric mean column
gmean_runtime = runtimes_flat.groupby("configuration")["runtime"].prod().pow(1/len(runtimes.index))
gmean_df = gmean_runtime.to_frame().reset_index().rename(columns={'index': 'configuration'})
gmean_df["benchmark"] = "gmean"
print(gmean_df)

# runtimes_flat = pd.concat([runtimes_flat, gmean_df])

plt.figure(figsize=(6,4))
sns.barplot(runtimes_flat, x="benchmark", y="runtime", hue="configuration")
plt.legend()
plt.gca().tick_params(axis='x', rotation=90)
plt.tight_layout()
# plt.savefig("polybench_mem2reg.pdf")
plt.show()
