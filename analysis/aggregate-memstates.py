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
import json
from pathlib import Path

def get_memory_node_counts(suffix):
    return [
        "#TotalRefOnlyState" + suffix,
        "#TotalModOnlyState" + suffix,
        "#TotalModRefState" + suffix,

        "#TotalAllocaState" + suffix,
        "#TotalMallocState" + suffix,
        "#TotalDeltaState" + suffix,
        "#TotalImportState" + suffix,
        "#TotalLambdaState" + suffix,
        "#TotalExternalNodeState" + suffix,

        "#TotalNonEscapedState" + suffix,

        "#MaxMemoryState" + suffix,
        "#MaxNonEscapedMemoryState" + suffix,
    ]

def map_optimization_statistic(original_name):
    if original_name == "Time[ns]":
        return "OptimizationTime[ns]"
    elif original_name in ["#RvsdgNodesBefore", "#RvsdgNodesAfter"]:
        return original_name + "Sequence"

    return "TransformationPass-" + original_name

# For each statistic, this dict contains which values to keep
# If the entry is a tuple (name, rename), the statistic called `name` will be kept, but be called `rename`
# If the entry is a function, it takes the old name and provides the new name, or None to discard
METRICS_MAPPING = {
    "AggregateAllocaSplitting": [
        "#AggregateAllocaNodes",
        "#AggregateStructAllocaNodes",
        "#SplitableAggregateAllocaNodes",
        "AggregateAllocaSplittingTime[ns]"
    ],
    "AndersenAnalysis": [
        "#RvsdgNodes",
        "#PointsToGraphAllocaNodes", "#PointsToGraphMallocNodes", "#PointsToGraphDeltaNodes", "#PointsToGraphImportNodes", "#PointsToGraphLambdaNodes",
        "#PointsToGraphMemoryNodes", "#PointsToGraphRegisterNodes", "#PointsToGraphEscapedNodes", "#PointsToGraphNodes", "#PointsToGraphEdges",
        ("AnalysisTimer[ns]", "AndersenAnalysisTimer[ns]"),
        ("SetAndConstraintBuildingTimer[ns]", "AndersenSetBuildingTimer[ns]"), ("OVSTimer[ns]", "AndersenOVSTimer[ns]"),
        ("ConstraintSolvingWorklistTimer[ns]", "AndersenWorklistTimer[ns]"), "PointsToGraphConstructionTimer[ns]",
    ],
    "AgnosticModRefSummarizer": [
        "MemoryStateDistribution",
        ("Time[ns]", "AgnosticModRefSummarizerTime[ns]")
    ],
    "RegionAwareModRefSummarizer": [
        "#SimpleAllocas",
        "#Functions",
        "#FunctionsCallingSetjmp",
        "#ReadOnlyMemoryNodesDetected",

        "#ModRefSetsMaterialized",
        "ModRefSetSizeBeforeMaterialization",
        "ModRefSetSizeAfterFiltering",
        "#ModRefSetsWithEffectOnExternal",
        "#ModRefSetsCallingExternalFunction",
        "ModRefSetSizeAfterMaterialization",

        "MemoryStateDistribution",

        "SimpleAllocasSetTimer[ns]",
        "AnnotationTimer[ns]",
        "SolvingTimer[ns]",
        "ReadOnlyDetectionTimer[ns]",
        "ModRefSetMaterializationTimer[ns]"
    ],
    "MemoryStateEncoder": [
        "#IntraProceduralRegions",
        *get_memory_node_counts("Arguments"),
        "#LoadOperations",
        *get_memory_node_counts("sThroughLoad"),
        "#StoreOperations",
        *get_memory_node_counts("sThroughStore"),
        "#CallEntryMergeOperations",
        *get_memory_node_counts("sIntoCallEntryMerge"),
        "#ModRefSetOperations",
        "#TotalModRefSetIntervals",
        "#TotalLiveIntervals",
        ("EncodingTime[ns]", "MemoryStateEncodingTime[ns]"),
        ("PruningTime[ns]", "MemoryStateEncoderPruningTime[ns]")
    ],
    "InterProceduralGraphToRvsdg": [
        ("Time[ns]", "RvsdgConstructionTime[ns]")
    ],
    "StoreValueForwarding": [
        "#LoadsWithMemoryState",
        "#ForwardedLoadsWithMemoryState",

        "#LoadsWithoutMemoryState",
        "#LoadsTracedToDeltaNode",
        "#ForwardedLoadsWithoutMemoryState",

        "#NoAliasStore",
        "#MayAliasStore",
        "#MustAliasStore",
        "#NoAliasLoad",
        "#MayAliasLoad",
        "#MustAliasLoad",
        ("TracingTime[ns]", "SvfTracingTime[ns]"),
        ("ForwardingTime[ns]", "SvfForwardingTime[ns]"),
        ("Time[ns]", "StoreValueForwardingTime[ns]")
    ],
    "DeadNodeElimination": [
        ("MarkTime[ns]", "DNEMarkTime[ns]"),
        ("SweepTime[ns]", "DNESweepTime[ns]"),
    ],
    "RvsdgTreePrinter": lambda x: f"{x}-Tree",
    "NodeReduction": lambda x: x, # Include every statistic from node reduction
    "RED": lambda x: x, # TODO: This is the old name for NodeReduction
    "RVSDGOPTIMIZATION": map_optimization_statistic,
    "RVSDGDESTRUCTION": [
        ("Time[ns]", "RvsdgDestructionTime[ns]")
    ]
}

def get_metric_name(statistic, original_name):
    if statistic not in METRICS_MAPPING:
        return None

    mapping = METRICS_MAPPING[statistic]

    if callable(mapping):
        return mapping(original_name)

    for entry in mapping:
        if isinstance(entry, tuple):
            old, new = entry
            if original_name == old:
                return new
        elif original_name == entry:
            return entry

    return None

def extract_file_data(folder):
    file_datas = []

    files = os.listdir(folder)

    for fil in files:
        if not fil.endswith(".log"):
            continue

        file_data = {}
        cfile = fil[:-4]
        file_data["cfile"] = cfile

        # Keep track of how many times the same statstic line has been seen
        statistic_line_counts = {}

        with open(os.path.join(folder, fil), "r", encoding="utf-8") as fd:
            for line in fd:
                statistic, _, *parts = line.split(" ")

                # If this statistic line has been seen before, give it a suffix
                statistic_num = statistic_line_counts.get(statistic, 0)
                statistic_line_counts[statistic] = statistic_num + 1
                statistic_suffix = "" if statistic_num == 0 else f"--{statistic_num:02}"

                for part in parts:
                    colon = part.find(":")
                    original_name, value = part[:colon], part[colon+1:]

                    metric_name = get_metric_name(statistic, original_name)
                    if not metric_name:
                        continue

                    metric_name = metric_name + statistic_suffix

                    if metric_name in file_data:
                        raise ValueError(f"Multiple statistics provide the metric {metric_name}")

                    try:
                        file_data[metric_name] = int(value)
                    except:
                        file_data[metric_name] = value

        file_datas.append(file_data)

    return pd.DataFrame(file_datas)

def calculate_total_ramrs_time(file_data):
    file_data["RegionAwareModRefSummarizerTime[ns]"] = (
        file_data["SimpleAllocasSetTimer[ns]"] +
        file_data["AnnotationTimer[ns]"] +
        file_data["SolvingTimer[ns]"] +
        file_data["ReadOnlyDetectionTimer[ns]"] +
        file_data["ModRefSetMaterializationTimer[ns]"]
    )

def make_file_data(folder, configuration):
    file_data = extract_file_data(folder)
    file_data["Configuration"] = configuration

    return file_data

def main():
    parser = argparse.ArgumentParser(description='Process raw statistics from the given folder.')
    parser.add_argument('--stats-in', dest='stats_in', action='store', default="statistics",
                        help='The folder where statistics files (*.log) are located, or subfolders')
    parser.add_argument('--stats-out', dest='stats_out', action='store', default="statistics-out/data.csv",
                        help='File name for the output file. Creates its folder if missing')
    args = parser.parse_args()

    stats_in = Path(args.stats_in)
    if not stats_in.is_dir():
        raise ValueError("stats-in must be a directory")

    data = []
    stats_in_contents = os.listdir(stats_in)
    stats_in_contents.sort()
    for subfolder_name in stats_in_contents:
        subfolder = stats_in / subfolder_name
        if subfolder.is_dir():
            data.append(make_file_data(subfolder, subfolder_name))

    # If the stats_in folder itself contains .log files, use it as a statistics folder directly
    if any(c.endswith(".log") for c in stats_in_contents):
        data.append(make_file_data(stats_in, stats_in.name))

    file_data = pd.concat(data)
    calculate_total_ramrs_time(file_data)

    stats_out = Path(args.stats_out)
    stats_out.parent.mkdir(parents=True, exist_ok=True)
    file_data.to_csv(stats_out, index=False)

if __name__ == "__main__":
    main()
