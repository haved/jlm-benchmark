#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

default = pd.read_csv("statistics-out/release/file_config_data.csv")
anf = pd.read_csv("statistics-out/release-anf/file_config_data.csv")

def find_always_bad_configs(file_config_data):
    min_time_rows = file_config_data.groupby('llfile')["TotalTime[ns]"].idxmin()
    min_time_configs = file_config_data.loc[min_time_rows, ["llfile", "TotalTime[ns]"]].set_index("llfile")

    file_config_data_with_min_config = file_config_data.join(min_time_configs, on="llfile", rsuffix="_best_cfg")
    # Add a bias of 10 us to avoid very small files preventing ratio from being high
    file_config_data_with_min_config["ratio"] = (file_config_data_with_min_config["TotalTime[ns]"] + 1e5) / file_config_data_with_min_config["TotalTime[ns]_best_cfg"]

    min_ratios = file_config_data_with_min_config.groupby("Configuration")["ratio"].min()
    min_ratios = min_ratios.sort_values()
    return min_ratios

default_min_ratios = find_always_bad_configs(default)
default_min_ratios.to_csv("statistics-out/release/config_min_ratios.csv")

anf_min_ratios = find_always_bad_configs(anf)
anf_min_ratios.to_csv("statistics-out/release-anf/config_min_ratios.csv")
