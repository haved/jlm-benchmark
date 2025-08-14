#!/usr/bin/env python3
import os
import os.path
import sys
import shutil
import pandas as pd
import argparse
import re

# Values from the AndersenAnalysis that should be the same for all configuration
PER_FILE_STATS = [
    "#RvsdgNodes", "#PointerObjects", "#MemoryPointerObjects", "#MemoryPointerObjectsCanPoint",
    "#RegisterPointerObjects", "#RegistersMappedToPointerObject",
    "#AllocaPointerObjects", "#MallocPointerObjects", "#GlobalPointerObjects",
    "#FunctionPointerObjects", "#ImportPointerObjects",
    "#BaseConstraints", "#SupersetConstraints", "#StoreConstraints",
    "#LoadConstraints", "#FunctionCallConstraints", "#ScalarFlagConstraints",
    "#OtherFlagConstraints"
]
PER_FILE_STATS_OPTIONAL = [
    "#PointsToGraphNodes", "#PointsToGraphAllocaNodes", "#PointsToGraphDeltaNodes",
    "#PointsToGraphImportNodes", "#PointsToGraphLambdaNodes", "#PointsToGraphMallocNodes",
    "#PointsToGraphMemoryNodes" "#PointsToGraphRegisterNodes", "#PointsToGraphEscapedNodes",
    "#PointsToGraphExternalMemorySources", "#PointsToGraphEdges", "#PointsToGraphPointsToRelations",
    "SetAndConstraintBuildingTimer[ns]", "PointsToGraphConstructionTimer[ns]",
    "PointsToGraphConstructionExternalToEscapedTimer[ns]",

    # Included to enable calculation of average amount of pointer objects pointing to external
    # Without merging unified pointer objects
    "#PointsToExternalRelations"
]

PRECISION_EVALUATION_KEEP_PER_AA = [
    "IsRemovingDuplicatePointers", "PrecisionEvaluationMode",

    # Counts total instances of each response type, no matter the precision evaluation mode
    "#TotalNoAlias", "#TotalMayAlias", "#TotalMustAlias",

    # Used for load/store conflict queries
    "ModuleNumClobbers",
    # The following three values sum up to 1
    "ClobberAverageNoAlias", "ClobberAverageMayAlias", "ClobberAverageMustAlias",

    "PrecisionEvaluationTimer[ns]"]

def line_to_dict(stats_line):
    """
    Splits the given line into a tuple (statistic, {key:value})
    """
    statistic, _, *stats = stats_line.split(" ")

    stats_dict = {}

    for stat in stats:
        stat_name, stat_value = stat.split(":")
        try:
            stat_value = int(stat_value)
        except:
            pass

        stats_dict[stat_name] = stat_value
    return statistic, stats_dict

def keep_file_stats(program, cfile, line_stats):
    """
    Takes the first line of statistics and only keeps statistics that are based on the file itself
    """
    stats = {
        "cfile": cfile,
        "program": program
    }
    for stat in PER_FILE_STATS:
        if stat in line_stats:
            stats[stat] = line_stats[stat]
        else:
            raise ValueError(f"Statistics file is missing mandatory stat: {stat}")

    for stat in PER_FILE_STATS_OPTIONAL:
        if stat in line_stats:
            stats[stat] = line_stats[stat]

    return stats

# Due to splitting workloads, the same cfile can have multiple statistics files
def handle_statistics_file(stats_filename, cfile, file_datas, file_config_datas):
    file_precision_stats = {}
    file_andersen_stats = None
    file_config_rows = []

    program = cfile.split("+")[0]

    with open(stats_filename, encoding='utf-8') as stats_file:
        for line in stats_file:
            statistic, line_stats = line_to_dict(line)

            if statistic == "AndersenAnalysis":
                # If we have not captured file statistics for this file yet
                if file_andersen_stats is None:
                    file_andersen_stats = keep_file_stats(program, cfile, line_stats)

                file_config_stats = file_andersen_stats.copy()
                file_config_stats.update(line_stats)
                file_config_rows.append(file_config_stats)
            elif statistic == "AliasAnalysisPrecisionEvaluation":
                aaType = line_stats["PairwiseAliasAnalysisType"] + "-"
                for col in PRECISION_EVALUATION_KEEP_PER_AA:
                    line_stats[aaType + col] = line_stats[col]
                file_precision_stats.update(line_stats)

            else:
                print("Ignoring unknown statistic:", statistic)

    # The first AndersenAnalysis statistic line is always the standard solver,
    # so it can be skipped
    if len(file_config_rows) >= 1:
        file_config_rows = file_config_rows[1:]
    else:
        print(f"WARNING: Statistics file {stats_filename} contained no AndersenAnalysis at all")

    # Avoid confusion by only keeping the columns that are prefixed with AA name
    for col in PRECISION_EVALUATION_KEEP_PER_AA:
        if col in file_precision_stats:
            del file_precision_stats[col]

    if cfile not in file_datas:
        file_datas[cfile] = {}
    if file_andersen_stats is not None:
        file_datas[cfile].update(file_andersen_stats)
    if file_precision_stats is not None:
        file_datas[cfile].update(file_precision_stats)

    if len(file_config_rows) > 0:
        file_config_data = pd.DataFrame(file_config_rows)
        file_config_data = file_config_data.groupby("Configuration").mean(numeric_only=True)

        file_config_data.reset_index(inplace=True)
        file_config_data["cfile"] = cfile
        file_config_datas.append(file_config_data)

def extract_statistics(stats_folder):
    """
    Create one dataframe with one row for each cfile
    and one dataframe with one row for each (cfile, configuration) combination.
    @return file_data, file_config_data
    """

    if not os.path.exists(stats_folder):
        return pd.DataFrame(), pd.DataFrame()

    files = os.listdir(stats_folder)
    file_datas = {}
    file_config_datas = []

    for filename in files:
        if "+" not in filename or not filename.endswith(".log"):
            print(f"Ignoring file {filename}", file=sys.stderr)
            continue

        # remove .log suffix
        cfile = filename[:-4]

        # Remove _onlyconfigXX suffix
        match_config_suffix = re.search("_onlyconfig[0-9]+$", cfile)
        if match_config_suffix is not None:
            cfile = cfile[:match_config_suffix.start()]
        match_precision_suffix = re.search("_onlyprecision$", cfile)
        if match_precision_suffix is not None:
            cfile = cfile[:match_precision_suffix.start()]

        stats_filename = os.path.join(stats_folder, filename)
        handle_statistics_file(stats_filename, cfile, file_datas, file_config_datas)

    # Skip files that did not actually have statistics
    file_datas = { cfile: data for cfile, data in file_datas.items() if "cfile" in data }

    if len(file_datas) == 0:
        return pd.DataFrame(), pd.DataFrame()

    file_datas = pd.DataFrame(file_datas.values()).set_index("cfile")
    file_config_datas = pd.concat(file_config_datas)

    # Check that no cfile has multiple occurances of the same configuration
    # This could happen if a file has analyzed both regularly, and individually per config
    num_cfile_config_pairs = file_config_datas.groupby(['cfile', 'Configuration']).size()
    num_cfile_config_pairs = num_cfile_config_pairs[num_cfile_config_pairs > 1]
    for cfile, config in num_cfile_config_pairs.index:
        print(f"WARNING: Multiple files provide the following combination: ({cfile}, {config})")
    if len(num_cfile_config_pairs) > 0:
        print("NOTE: You should not run the same files both using and not using --jlmExactConfig")
        file_config_data = file_config_data.groupby(["cfile", "Configuration"]).mean(numeric_only=True).reset_index()

    # Calculate a TotalTime column, using 0 where values are missing
    with_nan0 = file_config_datas.fillna(0)
    total_time = 0
    if "OVSTimer[ns]" in with_nan0:
        total_time += with_nan0["OVSTimer[ns]"]
    if "OfflineNormTimer[ns]" in with_nan0:
        total_time += with_nan0["OfflineNormTimer[ns]"]
    if "ConstraintSolvingWorklistTimer[ns]" in with_nan0:
        total_time += with_nan0["ConstraintSolvingWorklistTimer[ns]"]
    if "ConstraintSolvingNaiveTimer[ns]" in with_nan0:
        total_time += with_nan0["ConstraintSolvingNaiveTimer[ns]"]
    if "ConstraintSolvingWavePropagationTimer[ns]" in with_nan0:
        total_time += with_nan0["ConstraintSolvingWavePropagationTimer[ns]"]
    if "ConstraintSolvingDeepPropagationTimer[ns]" in with_nan0:
        total_time += with_nan0["ConstraintSolvingDeepPropagationTimer[ns]"]
    file_config_datas["TotalTime[ns]"] = total_time

    return file_datas, file_config_datas


def extract_or_load(stats_in, file_data_out, file_config_data_out):
    if os.path.exists(file_data_out) and os.path.exists(file_config_data_out):
        file_data = pd.read_csv(file_data_out)
        file_config_data = pd.read_csv(file_config_data_out)
    else:
        file_data_release, file_config_data_release = extract_statistics(os.path.join(stats_in, "release"))
        file_data_release_anf, file_config_data_release_anf = extract_statistics(os.path.join(stats_in, "release-anf"))

        file_data = pd.concat([file_data_release.reset_index(), file_data_release_anf.reset_index()], axis="rows")
        file_data.drop_duplicates(subset="cfile", inplace=True)
        file_data.set_index("cfile", inplace=True)

        if len(file_config_data_release) != 0:
            file_config_data_release["Configuration"] = "IP_" + file_config_data_release["Configuration"]
        if len(file_config_data_release_anf) != 0:
            file_config_data_release_anf["Configuration"] = "EP_" + file_config_data_release_anf["Configuration"]

        file_config_data = pd.concat([file_config_data_release, file_config_data_release_anf], axis="rows")

        # Check that all cfiles have been tested with all configurations
        configs_per_cfile = file_config_data.groupby("cfile")["Configuration"].nunique()
        max_number_of_configs = configs_per_cfile.max()
        print(f"C files have been solved with {max_number_of_configs} different configurations")

        missing_configs = configs_per_cfile[configs_per_cfile != max_number_of_configs]
        if len(missing_configs) != 0:
            print(f"WARNING: {len(missing_configs)} cfiles been evaluated with fewer configs!")
            # file_config_data = file_config_data[~(file_config_data["cfile"].isin(missing_configs))]
        if 0 < len(missing_configs) < 10:
            print(missing_configs)

        # Make sure all configurations agree on solution statistics that should be identical
        for column in ["#PointsToRelations", "#PointsToExternalRelations", "#CanPointsEscaped", "#CantPointsEscaped"]:
            num_different_counts = file_config_data.groupby("cfile")[column].nunique()
            non_unique_cfiles = num_different_counts[num_different_counts > 1].index
            for cfile in non_unique_cfiles:
                print(f"ERROR: Different configurations have different values of {column} in {cfile}")
            if len(non_unique_cfiles) > 0:
                exit(1)

        file_data.to_csv(file_data_out)
        file_config_data.to_csv(file_config_data_out, index=False)

    return file_data, file_config_data


def get_mean_time_per_config(file_config_data):
    # Calculate the average time spent by each technique
    # First filter away configurations that have not finished for every single file

    cfiles_per_config = file_config_data.groupby("Configuration")["cfile"].nunique()
    num_cfiles = file_config_data["cfile"].nunique()

    configs_to_keep = cfiles_per_config[cfiles_per_config == num_cfiles].index
    configs_to_discard = cfiles_per_config[cfiles_per_config != num_cfiles].index

    if len(configs_to_discard):
        print("The following Configurations are skipped, due to not being present for all cfiles:")
        print(configs_to_discard)

    print(f"mean_time_per_config contains {len(configs_to_keep)} Configurations")

    mean_by_config = file_config_data.groupby("Configuration").mean(numeric_only=True)
    mean_by_config = mean_by_config[mean_by_config.index.isin(configs_to_keep)]
    total_time = mean_by_config["TotalTime[ns]"].sort_values()
    return total_time


def main():
    parser = argparse.ArgumentParser(description='Process raw benchmark statistics from the given folders.'
                                     'Mainly creates two aggregation files, plus some extra statistics files.')
    parser.add_argument('--stats-in', dest='stats_in', action='store', required=True,
                        help='The folder where release and release_anf with log files are located')
    parser.add_argument('--stats-out', dest='stats_out', action='store', required=True,
                        help='Folder where aggregated statistics files should be placed')
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
