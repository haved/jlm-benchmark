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

def make_file_data(folder, configuration):
    file_datas = []

    for fil in os.listdir(folder):
        if not fil.endswith("-rvsdgTree.txt"):
            continue

        file_data = {}
        file_data["cfile"] = fil[:-len("-rvsdgTree.txt")]
        file_data["Configuration"] = configuration

        with open(os.path.join(folder, fil), "r", encoding="utf-8") as fd:
            for line in fd:
                # Example line:
                # ------------Region[1] NumStoreNodes:3 NumLoadNodes:5 NumMemoryStateTypeArguments:6 NumMemoryStateTypeResults:6

                if "Region" not in line:
                    continue

                parts = line.split(" ")[1:]
                for part in parts:
                    name, value = part.split(":")
                    file_data[name] = file_data.get(name, 0) + int(value)

        file_datas.append(file_data)

    return pd.DataFrame(file_datas)


def count_memstates(file_data, configuration):
    data_for_conf = file_data[file_data["Configuration"] == configuration]
    data_for_conf = data_for_conf.set_index("cfile")
    return data_for_conf["NumMemoryStateTypeArguments"] + data_for_conf["NumMemoryStateTypeResults"]


def plot_difference(num_memsates, conf, baseline_conf, savefig=None):
    num_memsates.sort_values(baseline_conf, ascending=True, inplace=True)

    plt.figure(figsize=(7,3))

    data = pd.DataFrame({"x": range(len(num_memsates)), "ratio": num_memsates[conf] / num_memsates[baseline_conf]})
    sns.scatterplot(data=data, x="x", y="ratio")

    plt.ylabel(f"{conf} / {baseline_conf}")
    plt.xlabel(f"Files sorted by {baseline_conf}")

    def xline(i):
        if i >= len(num_memsates):
            return
        plt.gca().axvline(i, linewidth=1, zorder=3, color='#444')
        text = f"{num_memsates[baseline_conf].iloc[i]}"
        plt.gca().text(i, 0.1, s=text)

    xline(100)
    xline(200)
    xline(300)
    xline(400)
    xline(500)

    plt.tight_layout(pad=0.2)

    if savefig is not None:
        plt.savefig(savefig)

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

    raware_data = make_file_data(os.path.join(args.stats_in, "raware"), "RegionAwareModRef")
    agnostic_data = make_file_data(os.path.join(args.stats_in, "agnostic"), "AgnosticModRef")

    file_data = pd.concat((raware_data, agnostic_data))
    file_data.to_csv(stats_out("memstate-file-data.csv"))

    num_memstates = pd.DataFrame({
        "RegionAwareModRef": count_memstates(file_data, "RegionAwareModRef"),
        "AgnosticModRef": count_memstates(file_data, "AgnosticModRef")
    })
    plot_difference(num_memstates, "RegionAwareModRef", "AgnosticModRef", savefig="results/memrefs-raware-vs-agnostic.pdf")

if __name__ == "__main__":
    main()
