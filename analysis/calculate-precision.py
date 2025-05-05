#!/usr/bin/env python3

import pandas as pd

file_data = pd.read_csv("statistics-out/file_data.csv")

print("PrecisionEvaluationMode:", file_data["PrecisionEvaluationMode"].unique())

module_num_uses = file_data["ModuleNumUseOperations"]

def calculate_average_for_aa(aaName):
    aaPrefix = aaName + "-"
    module_use_average_may_alias = file_data[aaPrefix + "ModuleAverageMayAliasRate"].fillna(0)

    # Create a column of how much uses are clobbered in total
    file_data[aaPrefix + "clobber_amount"] = module_num_uses * module_use_average_may_alias
    # Calculate weighted average per program
    per_program = file_data.groupby("program").sum()
    total_may_alias = per_program[aaPrefix + "clobber_amount"] / per_program["ModuleNumUseOperations"]

    return total_may_alias

def calculate_total_query_responses_for_aa(aaName):
    aaPrefix = aaName + "-"
    per_program = file_data.groupby("program").sum()

    result = pd.DataFrame({
        "NoAlias": per_program[aaPrefix + "#NoAlias"],
        "MayAlias": per_program[aaPrefix + "#MayAlias"],
        "MustAlias": per_program[aaPrefix + "#MustAlias"]
                  })
    result["MayRate"] = result["MayAlias"] / result.sum(axis=1)

    return result

def print_aa(aa):
    print()
    print(aa)
    print("Average use is MayAlias with the given percent of its function's clobbers")
    print(calculate_average_for_aa(aa))
    print("Total no / may / must alias query responses:")
    totals = calculate_total_query_responses_for_aa(aa)
    print(totals)
    print("Time spent on alias queries:",
          file_data[aa + "-PrecisionEvaluationTimer[ns]"].sum() / 1.e9, "seconds")

print_aa("BasicAA")
print_aa("PointsToGraphAA")
print_aa("ChainedAA(PointsToGraphAA,BasicAA)")
