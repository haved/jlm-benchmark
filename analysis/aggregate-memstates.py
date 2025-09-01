#!/usr/bin/env python3
import os
import os.path
import sys
import shutil
import pandas as pd
import argparse
import re

def make_file_data(folder):

    file_datas = []

    for fil in os.listdir(folder):
        if not fil.endswith("-rvsdgTree.txt"):
            continue

        file_data = {}
        file_data["cfile"] = fil[:-len("-rvsdgTree.txt")]

        with open(os.path.join(folder, file_data), "r", encoding="utf-8") as fd:
            for line in fd:
                if "Region" not in line:
                    continue



    return pd.DataFrame(file_datas)

def main():
    parser = argparse.ArgumentParser(description='Process raw statistics from the given folder.')
    parser.add_argument('--stats-in', dest='stats_in', action='store', required=True,
                        help='The folder where statistics files are located')
    parser.add_argument('--stats-out', dest='stats_out', action='store', required=True,
                        help='Folder where aggregated statistics should be placed')
    args = parser.parse_args()

    if not os.path.exists(args.stats_out):
        os.mkdir(args.stats_out)
    def stats_out(filename=""):
        return os.path.join(args.stats_out, filename)

    file_data = make_file_data(args.stats_in)
    file_data.to_csv(stats_out("memstate-file-data.csv"))

if __name__ == "__main__":
    main()
