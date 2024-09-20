#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

default = pd.read_csv("statistics-out/release/file_config_data.csv")
anf = pd.read_csv("statistics-out/release-anf/file_config_data.csv")

# Use the config that is fastest on average with flags
DEFAULT_BEST_CONFIG = "Solver=Worklist_Policy=FirstInFirstOut_PIP"
DEFAULT_BEST_SANS_PIP_CONFIG = "Solver=Worklist_Policy=FirstInFirstOut"

default_with_best_config = default[default["Configuration"] == DEFAULT_BEST_CONFIG].set_index('llfile').add_suffix("_default")
default_with_best_sans_pip_config = default[default["Configuration"] == DEFAULT_BEST_SANS_PIP_CONFIG].set_index('llfile').add_suffix("_default_sans_pip")

def get_fastest_config_per_llfile(df):
    df_per_llfile = df.groupby('llfile')['TotalTime[ns]'].idxmin()
    return df.loc[df_per_llfile,:].set_index('llfile')

anf_with_fastest_config = get_fastest_config_per_llfile(anf).add_suffix("_anf")
default_with_fastest_config = get_fastest_config_per_llfile(default).add_suffix("_default_fastest")

for llfile in default_with_best_config.index.difference(anf_with_fastest_config.index):
    print(f"llfile in default, not in anf: {llfile}")
for llfile in anf_with_fastest_config.index.difference(default_with_best_config.index):
    print(f"llfile in anf, not in default: {llfile}")

joined = default_with_best_config.join(anf_with_fastest_config, how="inner")
joined = joined.join(default_with_fastest_config, how="inner")
joined = joined.join(default_with_best_sans_pip_config, how="inner")

joined = joined.sort_values("TotalTime[ns]_default", ascending=True)

# CUTOFF = 1e6
# joined = joined[(joined["TotalTime[ns]_default"] > CUTOFF) | (joined["TotalTime[ns]_anf"] > CUTOFF)]

speedup = joined["TotalTime[ns]_anf"] / joined["TotalTime[ns]_default"]
print("Mean speedup:", speedup.mean())

total_time_default = joined["TotalTime[ns]_default"].values
total_time_default_sans_pip = joined["TotalTime[ns]_default_sans_pip"].values
total_time_anf = joined["TotalTime[ns]_anf"].values
total_time_default_fastest = joined["TotalTime[ns]_default_fastest"].values

x = range(len(joined))
plt.figure(figsize=(11,11))
# plt.ylim(-1e7, 0.25 * 1e9)
plt.yscale("log")

def plot_given_config(config, color):
    default_with_given_config = default[default["Configuration"] == config].set_index('llfile').add_suffix("_config")
    given_joined = joined.join(default_with_given_config, how="inner")
    plt.scatter(x=x, y=given_joined["TotalTime[ns]_config"].values, color=color, label=config, alpha=0.3)

plt.scatter(x=x, y=total_time_default, color='blue', alpha=0.3)
plt.scatter(x=x, y=total_time_anf, color='red', alpha=0.3)
plt.scatter(x=x, y=total_time_default_sans_pip, color='green', alpha=0.3)

#speedup =  joined["TotalTime[ns]_default"] / joined["TotalTime[ns]_default_fastest"]
#print("Mean speedup from oracle:", speedup.mean())

#speedup = joined["TotalTime[ns]_default"].sum() / joined["TotalTime[ns]_default_fastest"].sum()
#print("Total speedup: ", speedup)

# plot_given_config("Solver=Naive", 'green')
# plot_given_config("Solver=Worklist_Policy=FirstInFirstOut", 'green')
plt.grid()
# plt.title()

#plt.savefig("above1ms_log.pdf")

plt.figure()

ratio = total_time_anf / total_time_default
ratio.sort()
plt.yscale("log")
plt.plot(np.linspace(0,100,len(ratio)), ratio, color='blue')
plt.grid()
plt.show()
