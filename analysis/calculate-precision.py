#!/usr/bin/env python3

import pandas as pd

file_data = pd.read_csv("statistics-out/file_data.csv")

print("PrecisionEvaluationMode:", file_data["PrecisionEvaluationMode"].unique())
print("IsRemovingDuplicatePointers:", file_data["IsRemovingDuplicatePointers"].unique())

def print_average_points_to_external_info():
    # Only includes PointerObjects marked "CanPoint"
    pointer_objects_point_to_external = file_data["#PointsToExternalRelations"]
    pointer_objects_can_point = (
        file_data["#MemoryPointerObjectsCanPoint"] + file_data["#RegisterPointerObjects"])

    rate = pointer_objects_point_to_external.sum() / pointer_objects_can_point.sum()

    print(f"Percentage of pointers that may point to external: {rate*100:.2f}%")


def calculate_average_for_aa(aaName):
    module_num_clobbers = file_data["ModuleNumClobbers"]

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

    # Create an "all"-column weighted by the number of clobbers in each program
    res.loc["all", "NoAlias"] = file_data[aaPrefix + "CA_NoAlias"].sum() / module_num_clobbers.sum()
    res.loc["all", "MayAlias"] = file_data[aaPrefix + "CA_MayAlias"].sum() / module_num_clobbers.sum()
    res.loc["all", "MustAlias"] = file_data[aaPrefix + "CA_MustAlias"].sum() / module_num_clobbers.sum()

    return res

def calculate_total_query_responses_for_aa(aaName):
    """This function is used when considering the total number of alias responses"""
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
    average_rates = calculate_average_for_aa(aa)
    print(average_rates)
    # print("Total no / may / must alias query responses:")
    # totals = calculate_total_query_responses_for_aa(aa)
    # print(totals)
    print("Time spent on alias queries:",
          file_data[aa + "-PrecisionEvaluationTimer[ns]"].sum() / 1.e9, "seconds")

    return average_rates

print_average_points_to_external_info()

basic_aa = print_aa("BasicAA")
ptg_aa   = print_aa("PointsToGraphAA")
both_aa  = print_aa("ChainedAA(PointsToGraphAA,BasicAA)")

program_wise_reduction = (1 -
                          (both_aa.loc[both_aa.index != "all", "MayAlias"] /
                          basic_aa.loc[basic_aa.index != "all", "MayAlias"]).mean())
print("On average reduction across programs:", program_wise_reduction)
