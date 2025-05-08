#!/usr/bin/env python3

import pandas as pd

file_data = pd.read_csv("statistics-out/file_data.csv")

print("PrecisionEvaluationMode:", file_data["PrecisionEvaluationMode"].unique())
print("IsRemovingDuplicatePointers:", file_data["IsRemovingDuplicatePointers"].unique())

module_num_clobbers = file_data["ModuleNumClobbers"]

def calculate_average_for_aa(aaName):
    aaPrefix = aaName + "-"
    clobber_average_no_alias = file_data[aaPrefix + "ClobberAverageNoAlias"].fillna(0)
    clobber_average_may_alias = file_data[aaPrefix + "ClobberAverageMayAlias"].fillna(0)
    clobber_average_must_alias = file_data[aaPrefix + "ClobberAverageMustAlias"].fillna(0)

    # Create a column of total weighted response ratios
    file_data[aaPrefix + "CA_NoAlias"] = module_num_clobbers * clobber_average_no_alias
    file_data[aaPrefix + "CA_MayAlias"] = module_num_clobbers * clobber_average_may_alias
    file_data[aaPrefix + "CA_MustAlias"] = module_num_clobbers * clobber_average_must_alias

    # Calculate weighted average per program
    per_program = file_data.groupby("program").sum()
    program_no_alias = per_program[aaPrefix + "CA_NoAlias"] / per_program["ModuleNumClobbers"]
    program_may_alias = per_program[aaPrefix + "CA_MayAlias"] / per_program["ModuleNumClobbers"]
    program_must_alias = per_program[aaPrefix + "CA_MustAlias"] / per_program["ModuleNumClobbers"]

    res = pd.DataFrame({
        "NoAlias": program_no_alias,
        "MayAlias": program_may_alias,
        "MustAlias": program_must_alias
    })
    return res

def calculate_total_query_responses_for_aa(aaName):
    aaPrefix = aaName + "-"
    per_program = file_data.groupby("program").sum()

    result = pd.DataFrame({
        "NoAlias": per_program[aaPrefix + "#TotalNoAlias"],
        "MayAlias": per_program[aaPrefix + "#TotalMayAlias"],
        "MustAlias": per_program[aaPrefix + "#TotalMustAlias"]
                  })
    result["MayRate"] = result["MayAlias"] / result.sum(axis=1)

    return result

def print_aa(aa):
    print()
    print(aa)
    print("Statistics for average clobber operation")
    print(calculate_average_for_aa(aa))
    print("Total no / may / must alias query responses:")
    totals = calculate_total_query_responses_for_aa(aa)
    print(totals)
    print("Time spent on alias queries:",
          file_data[aa + "-PrecisionEvaluationTimer[ns]"].sum() / 1.e9, "seconds")

print_aa("BasicAA")
print_aa("PointsToGraphAA")
print_aa("ChainedAA(PointsToGraphAA,BasicAA)")
