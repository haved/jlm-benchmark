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
    "LoadsConsideredClobbers", "DeduplicatingPointers",
    # "PerFunctionOutputFile", "AliasingGraphOutputFile",

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
def handle_statistics_file(stats_filename, cfile, file_datas):
    file_precision_stats = {}
    file_andersen_stats = None

    program = cfile.split("+")[0]

    with open(stats_filename, encoding='utf-8') as stats_file:
        for line in stats_file:
            statistic, line_stats = line_to_dict(line)

            if statistic == "AndersenAnalysis":
                # If we have not captured file statistics for this file yet
                if file_andersen_stats is None:
                    file_andersen_stats = keep_file_stats(program, cfile, line_stats)

            elif statistic == "AliasAnalysisPrecisionEvaluation":
                aaType = line_stats["PairwiseAliasAnalysisType"] + "-"
                for col in PRECISION_EVALUATION_KEEP_PER_AA:
                    line_stats[aaType + col] = line_stats[col]
                file_precision_stats.update(line_stats)

            else:
                print("Ignoring unknown statistic:", statistic)

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

def extract_statistics(stats_folder):
    """
    Create one dataframe with one row for each cfile.
    @return file_data, file_config_data
    """

    if not os.path.exists(stats_folder):
        return pd.DataFrame(), pd.DataFrame()

    files = os.listdir(stats_folder)
    file_datas = {}

    for filename in files:
        if "+" not in filename or not filename.endswith(".log"):
            continue

        # remove .log suffix
        cfile = filename[:-4]

        stats_filename = os.path.join(stats_folder, filename)
        handle_statistics_file(stats_filename, cfile, file_datas)

    # Skip files that did not actually have statistics
    file_datas = { cfile: data for cfile, data in file_datas.items() if "cfile" in data }

    if len(file_datas) == 0:
        return pd.DataFrame()

    file_datas = pd.DataFrame(file_datas.values()).set_index("cfile")

    # Calculate a TotalTime column, using 0 where values are missing
    #with_nan0 = file_config_datas.fillna(0)
    #total_time = 0
    #if "OVSTimer[ns]" in with_nan0:
    #    total_time += with_nan0["OVSTimer[ns]"]
    #if "OfflineNormTimer[ns]" in with_nan0:
    #    total_time += with_nan0["OfflineNormTimer[ns]"]
    #if "ConstraintSolvingWorklistTimer[ns]" in with_nan0:
    #    total_time += with_nan0["ConstraintSolvingWorklistTimer[ns]"]
    #if "ConstraintSolvingNaiveTimer[ns]" in with_nan0:
    #    total_time += with_nan0["ConstraintSolvingNaiveTimer[ns]"]
    #if "ConstraintSolvingWavePropagationTimer[ns]" in with_nan0:
    #    total_time += with_nan0["ConstraintSolvingWavePropagationTimer[ns]"]
    #if "ConstraintSolvingDeepPropagationTimer[ns]" in with_nan0:
    #    total_time += with_nan0["ConstraintSolvingDeepPropagationTimer[ns]"]
    #file_config_datas["TotalTime[ns]"] = total_time

    return file_datas


def extract_or_load(stats_in, file_data_out):
    if os.path.exists(file_data_out):
        file_data = pd.read_csv(file_data_out)

    else:
        file_data_raware = extract_statistics(os.path.join(stats_in, "raware"))

        file_data = pd.concat([file_data_raware.reset_index()], axis="rows")
        file_data.drop_duplicates(subset="cfile", inplace=True)
        file_data.set_index("cfile", inplace=True)

        file_data.to_csv(file_data_out)

    return file_data

def main():
    parser = argparse.ArgumentParser(description='Process raw benchmark statistics from the given folders.')
    parser.add_argument('--stats-in', dest='stats_in', action='store', required=True,
                        help='The folder where statistics directories with log files are located')
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

    file_data = extract_or_load(args.stats_in,
                                stats_out("file_data.csv"))


if __name__ == "__main__":
    main()
