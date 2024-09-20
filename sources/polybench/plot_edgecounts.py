#!/usr/bin/env python3

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

edgecounts = pd.read_csv("edgecounts.csv", index_col=0)

edgecounts_flat = pd.DataFrame()

configurations = edgecounts.columns
for benchmark in edgecounts.index:
    edges = edgecounts.loc[benchmark, configurations]

    # Normalize bar length
    # times = times / times.max()

    added_df = pd.DataFrame({"benchmark": benchmark, "configuration": configurations, "edge count": edges})
    edgecounts_flat = pd.concat([edgecounts_flat, added_df])

# add geometric mean column
print(len(edgecounts.index))
gmean_runtime = edgecounts_flat.groupby("configuration")["edge count"]
print(gmean_runtime.describe())
gmean_runtime = gmean_runtime.sum() * (1/len(edgecounts.index))
gmean_df = gmean_runtime.to_frame().reset_index().rename(columns={'index': 'configuration'})
gmean_df["benchmark"] = "gmean"
print(gmean_df)

# edgecounts_flat = pd.concat([edgecounts_flat, gmean_df])

plt.figure(figsize=(6,4))
sns.barplot(edgecounts_flat, x="benchmark", y="edge count", hue="configuration")
plt.legend()
plt.gca().tick_params(axis='x', rotation=90)
plt.tight_layout()
plt.savefig("polybench_edges.pdf")
plt.show()
