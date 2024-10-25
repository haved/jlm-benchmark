#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import argparse
import os.path

parser = argparse.ArgumentParser(description='Analyze statistics about file sizes')
parser.add_argument('--stats', dest='stats', action='store', required=True,
                    help='Specify the folder for aggregated statistics, e.g., statistics-out/release')
parser.add_argument('--out', dest='out', action='store', required=True,
                        help='The output file for results, e.g., results/terrible-configs.csv')
args = parser.parse_args()

file_config_data = pd.read_csv(os.path.join(args.stats, "file_config_data.csv"))

def find_always_bad_configs(file_config_data):
    min_time_rows = file_config_data.groupby('cfile')["TotalTime[ns]"].idxmin()
    min_time_configs = file_config_data.loc[min_time_rows, ["cfile", "TotalTime[ns]"]].set_index("cfile")

    file_config_data_with_min_config = file_config_data.join(min_time_configs, on="cfile", rsuffix="_best_cfg")
    # Add a bias of 10 us to avoid very small files preventing ratio from being high
    file_config_data_with_min_config["ratio"] = (file_config_data_with_min_config["TotalTime[ns]"]) / file_config_data_with_min_config["TotalTime[ns]_best_cfg"]

    min_ratios = file_config_data_with_min_config.groupby("Configuration")["ratio"].min()
    min_ratios = min_ratios.sort_values()
    return min_ratios

default_min_ratios = find_always_bad_configs(file_config_data)
default_min_ratios.to_csv(args.out)
