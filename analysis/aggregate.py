#!/usr/bin/env python3
import os
import os.path
import sys
import shutil
import pandas as pd
import argparse

def line_to_dict(stats_line):
    statistic, _, *stats = stats_line.split(" ")
    assert statistic == "AndersenAnalysis"

    stats_dict = {}

    for stat in stats:
        stat_name, stat_value = stat.split(":")
        try:
            stat_value = int(stat_value)
        except:
            pass

        stats_dict[stat_name] = stat_value
    return stats_dict

def extract_statistics(stats_folder):
    """
    Create one dataframe with one row for each cfile
    and one dataframe with one row for each (cfile, configuration) combination.
    @return file_data, file_config_data
    """

    files = os.listdir(stats_folder)
    file_datas = []
    file_config_datas = []

    for filename in files:
        if "+" not in filename or not filename.endswith(".log"):
            print(f"Ignoring file {filename}", file=sys.stderr)
            continue

        cfile = filename[:-4] # Remove .log
        if "+" in cfile:
            program = cfile.split("+")[0]
        else:
            program = ""

        file_config_rows = []

        with open(os.path.join(stats_folder, filename), encoding='utf-8') as stats_file:
            line_iter = iter(stats_file)

            file_stats = {"cfile": cfile, "program": program}

            # The first line are statistics from analyzing and solving and making the PointsToGraph
            first_line = next(line_iter)
            file_stats.update(line_to_dict(first_line))

            file_datas.append(file_stats)

            # All other lines are statistics from just solving
            for line in line_iter:
                file_config_rows.append(line_to_dict(line))

        file_config_data = pd.DataFrame(file_config_rows)

        file_config_data = file_config_data.groupby("Configuration").mean(numeric_only=True)
        file_config_data = file_config_data.groupby("Configuration").mean(numeric_only=True)

        with_nan0 = file_config_data.fillna(0)
        file_config_data["TotalTime[ns]"] = (
            with_nan0["OVSTimer[ns]"]
            + with_nan0["OfflineNormTimer[ns]"]
            + with_nan0["ConstraintSolvingWorklistTimer[ns]"]
            + with_nan0["ConstraintSolvingNaiveTimer[ns]"])

        file_config_data.reset_index(inplace=True)
        file_config_data["cfile"] = cfile
        file_config_datas.append(file_config_data)

    file_datas = pd.DataFrame(file_datas).set_index("cfile")
    file_config_datas = pd.concat(file_config_datas)
    file_config_datas = file_config_datas.join(file_datas, on="cfile", how="left", rsuffix="_collision")
    file_config_datas.drop(list(file_config_datas.filter(regex="_collision")), axis=1, inplace=True)
    return file_datas, file_config_datas


def extract_or_load(stats_in, file_data_out, file_config_data_out):
    if os.path.exists(file_data_out) and os.path.exists(file_config_data_out):
        file_data = pd.read_csv(file_data_out)
        file_config_data = pd.read_csv(file_config_data_out)
    else:
        file_data, file_config_data = extract_statistics(stats_in)
        file_data.to_csv(file_data_out)
        file_config_data.to_csv(file_config_data_out, index=False)

    return file_data, file_config_data


def get_mean_time_per_config(file_config_data):
    # Calculate the average time spent by each technique
    mean_by_config = file_config_data.groupby("Configuration").mean(numeric_only=True)
    total_time = mean_by_config["TotalTime[ns]"].sort_values()
    return total_time


def main():
    parser = argparse.ArgumentParser(description='Process raw benchmark statistics from the given folder.'
                                     'Mainly creates two aggregation files, plus some extra statistics files.')
    parser.add_argument('--stats-in', dest='stats_in', action='store', required=True,
                        help='The folder where raw .log files are located')
    parser.add_argument('--stats-out', dest='stats_out', action='store', required=True,
                        help='Where aggregated statistics files should be placed')
    parser.add_argument('--clean', dest='clean', action='store_true',
                        help='Remove previous extracted aggregation files before running')
    args = parser.parse_args()

    if args.clean:
        shutil.rmtree(args.stats_out, ignore_errors=True)

    if not os.path.exists(args.stats_out):
        os.mkdir(args.stats_out)
    def stats_out(filename=""):
        return os.path.join(args.stats_out, filename)

    file_data, file_config_data = extract_or_load(args.stats_in,
                                                  stats_out("file_data.csv"),
                                                  stats_out("file_config_data.csv"))

    mean_time_per_config = get_mean_time_per_config(file_config_data)
    mean_time_per_config.to_csv(stats_out("mean_time_per_config.csv"))

if __name__ == "__main__":
    main()
