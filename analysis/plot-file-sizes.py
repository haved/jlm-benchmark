#!/usr/bin/env python3
import os
import os.path
import sys
import shutil
import pandas as pd
import argparse
import matplotlib.pyplot as plt
from matplotlib import ticker
import seaborn as sns
import numpy as np

def load_aggregated_statistics(stats_folder):
    file_data = pd.read_csv(os.path.join(stats_folder, "file_data.csv"))
    file_config_data = pd.read_csv(os.path.join(stats_folder, "file_config_data.csv"))
    return file_data, file_config_data

def main():
    parser = argparse.ArgumentParser(description='Analyze statistics about file sizes')
    parser.add_argument('--stats', dest='stats', action='store', required=True,
                        help='Specify the folder for aggregated statistics')
    parser.add_argument('--out', dest='out_dir', action='store', required=True,
                        help='The output folder for plots')
    parser.add_argument('--clean', dest='clean', action='store_true',
                        help='Delete output folder first')
    args = parser.parse_args()

    file_data, file_config_data = load_aggregated_statistics(args.stats)

    if args.clean:
        shutil.rmtree(args.out_dir, ignore_errors=True)

    if not os.path.exists(args.out_dir):
        os.mkdir(args.out_dir)

    # Only care about non-empty cfiles
    file_data = file_data[file_data['#RvsdgNodes'] > 0]

    file_data['#Constraints'] = (file_data['#BaseConstraints'] + file_data['#SupersetConstraints'] + file_data['#StoreConstraints'] +
                                 file_data['#LoadConstraints'] + file_data['#FunctionCallConstraints'] + file_data['#ScalarFlagConstraints'] + file_data['#OtherFlagConstraints'])

    file_data.sort_values(by="program", inplace=True)

    grouped = file_data.groupby('program')

    table = pd.DataFrame({
        'C file count': grouped['cfile'].count(),
        'Mean IR instr': grouped['#RvsdgNodes'].mean().astype(int),
        'Max IR instr': grouped['#RvsdgNodes'].max(),
        'Mean Pointer Objects': grouped['#PointerObjects'].mean().astype(int),
        'Max Pointer Objects': grouped['#PointerObjects'].max(),
        'Mean Constraints': grouped['#Constraints'].mean().astype(int),
        'Max Constraints': grouped['#Constraints'].max(),
    })

    file_sizes_txt = os.path.join(args.out_dir, "file-sizes.txt")
    with open(file_sizes_txt, 'w', encoding='utf-8') as fd:
        print(table.columns, file=fd)
        for row in table.index:
            print(f"{row:<13} &" , end=" ", file=fd)
            for c in table.columns:
                number = table.loc[row, c]
                number = f"{number:_}"
                number = number.replace("_", "\\;")
                print(f"& {number:>8}", end=" ", file=fd)
            print("\\\\", file=fd)

    sns.set_theme(style="whitegrid", palette=None)
    fig, ax = plt.subplots(figsize=(10,4))
    sns.boxplot(data=file_data, x="#RvsdgNodes", y="program", showmeans=True, meanline=True, meanprops={"color": ".1"},
                color=".8", linecolor=".1", fliersize="5", ax=ax)

    ax.set_xlabel("IR instruction count")
    ax.set_ylabel(None)

    # ax.set_xlim((0, 500000))
    ax.set_xscale("log")

    plt.tight_layout(pad=1)

    fig.savefig(os.path.join(args.out_dir, "IR-instruction-counts.pdf"))

if __name__ == "__main__":
    main()
