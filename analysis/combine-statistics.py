#!/usr/bin/env python3

import argparse
import pandas as pd
import re
import os
from pathlib import Path
from collections import defaultdict

def main():
    parser = argparse.ArgumentParser(description='Combine statistics files into a single file')
    parser.add_argument('--stats-in', dest='stats_in', action='store', default="statistics-out",
                        help='The folder where statistics csv files are located')
    parser.add_argument('--stats-out', dest='stats_out', action='store', default="statistics-out/file-data.csv",
                        help='File name for the output file. Creates its folder if missing')
    args = parser.parse_args()

    stats_in = Path(args.stats_in)
    if not stats_in.is_dir():
        raise ValueError("stats-in must be a directory")
    stats_out = Path(args.stats_out)

    main_data = []
    all_data = []

    # Match file names like a-b-c-45
    iteration_file_regex = re.compile(r"(.*)-(\d+)")

    stats_in_contents = os.listdir(stats_in)
    stats_in_contents.sort()
    for filename in stats_in_contents:
        subfile = stats_in / filename

        if not subfile.is_file():
            continue
        if subfile.suffix != ".csv":
            continue
        # Avoid include the output file itself
        if subfile == stats_out:
            continue

        config_iteration_data = pd.read_csv(subfile)

        # Extract the configuration name and iteration number, if possible
        config_name = subfile.stem
        iteration = 0
        name_match = iteration_file_regex.fullmatch(config_name)
        if name_match:
            config_name = name_match.group(1)
            iteration = int(name_match.group(2))

            # Remove the iteration suffix in the data
            assert (config_iteration_data["Configuration"] == subfile.stem).all()
            config_iteration_data["Configuration"] = config_name

        if iteration == 0:
            main_data.append(config_iteration_data)
        all_data.append(config_iteration_data)

    # When configurations end in a number (iteration), only keep the -0 iteration
    # Except for timing, there we use every value and take the mean and std
    main_data_df = pd.concat(main_data)
    all_data_df = pd.concat(all_data)

    print("len main data df: ", len(main_data_df))
    print("len all data df: ", len(all_data_df))

    main_data_df.set_index(["cfile", "Configuration"], inplace=True)

    added_columns = [main_data_df]
    for column in main_data_df.columns:
        if not column.endswith("[ns]"):
            continue

        all_data_grouped = all_data_df.groupby(["cfile", "Configuration"])[column]
        added_columns.append(all_data_grouped.mean().rename(column + "-mean"))
        added_columns.append(all_data_grouped.min().rename(column + "-min"))
        added_columns.append(all_data_grouped.max().rename(column + "-max"))
        added_columns.append(all_data_grouped.std().rename(column + "-std"))

    main_data_df = pd.concat(added_columns, axis=1)

    stats_out.parent.mkdir(parents=True, exist_ok=True)
    main_data_df.to_csv(stats_out, index=True)

if __name__ == "__main__":
    main()
