#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import numpy as np
import re

def plot(data, ylabel, savefig=None):
    """ Takes data in the format
    Benchmark AA        Response    Rate
    ========= ========= =========== ====
    505.gcc   BasicAA   NoAlias     76.0
    505.gcc   BasicAA   MayAlias    14.2
    505.gcc   BasicAA   MustAlias   9.8
    ...

    and plots the MayAlias rate for each benchmark
    """
    data.loc[data["AA"] == "BasicAA", "AA"] = "local"
    data.loc[data["AA"] == "LlvmAA", "AA"] = "LLVM(BasicAA)"
    data.loc[data["AA"] == "PointsToGraphAA", "AA"] = "andersen"
    data.loc[data["AA"] == "ChainedAA(PointsToGraphAA,LlvmAA)", "AA"] = "andersen+LLVM(BasicAA)"

    data = data[data["Response"] != "NoAlias"]
    data = data[data["Response"] != "MustAlias"]

    colors = {
        "local": "#CC9600",
        "LLVM(BasicAA)": "#636EFA",
        "andersen": "#EF553B",
        "andersen+LLVM(BasicAA)": "#00CC96"
    }

    benchmarks = data["Benchmark"].unique()
    AAs = [
        #"local",
        "LLVM(BasicAA)",
        "andersen",
        "andersen+LLVM(BasicAA)"]

    fig, ax = plt.subplots(figsize=(8, 4))
    width = 0.25
    stride = len(AAs) * width + 0.3
    x = np.arange(len(benchmarks)) * stride

    legend_keys = []
    legend_names = []

    for i, aa in enumerate(AAs):
        offset = width * i
        rates = data[data["AA"] == aa].set_index("Benchmark")
        rates = rates.loc[benchmarks, "Rate"]
        rects = ax.bar(x + offset,
                       rates,
                       width,
                       label=aa,
                       facecolor=colors[aa],
                       alpha=0.9,
                       edgecolor="#333",
                       linewidth=1.5,
                       zorder=3)

        legend_keys.append(mlines.Line2D([], [],
                                         marker="s",
                                         markersize=10,
                                         linewidth=0,
                                         color=colors[aa]))
        legend_names.append(aa)

    ax.set_xlim(-width * 1.5, max(x) + width * len(AAs) + width * 0.5)
    benchmark_ticks = [re.sub("[-\\.]", "\n", b, count=1) for b in benchmarks]
    ax.set_xticks(x + width * (len(AAs) - 1) / 2, benchmark_ticks)
    ax.tick_params(axis='x', labelrotation=40)
    for tick in ax.xaxis.get_majorticklabels():
        tick.set_horizontalalignment("right")
        tick.set_verticalalignment("top")
        tick.set_rotation_mode("anchor")

    ax.set_ylabel(ylabel)
    ax.yaxis.label.set_size(13)

    ax.set_yticks(np.arange(0, 16 + 1, 2))
    ax.tick_params(axis='y', labelsize=12)
    ax.grid(which='major', axis='y', zorder=0)

    ax.legend(legend_keys, legend_names,
              loc='best',
              ncols=3,
              fontsize=10,
              frameon=False,
              borderpad=1.55)


    plt.tight_layout(pad=0.05)

    if savefig:
        plt.savefig(savefig)
    plt.show()


def parse_text_average(text):
    text = text.strip()
    lines = text.split("\n")

    rows = []

    # The current alias analysis being used
    AA = None
    for line in lines:
        if line == "":
            continue
        parts = line.split(" ")
        if len(parts) == 1:
            AA, = parts
            continue

        # Skip empty parts
        parts = [part for part in parts if part]
        benchmark, no_alias_rate, may_alias_rate, must_alias_rate = parts
        no_alias_rate = float(no_alias_rate)
        may_alias_rate = float(may_alias_rate)
        must_alias_rate = float(must_alias_rate)

        rows.append({
            "AA": AA,
            "Benchmark": benchmark,
            "Response": "MayAlias",
            "Rate": may_alias_rate * 100
            })
        rows.append({
            "AA": AA,
            "Benchmark": benchmark,
            "Response": "MustAlias",
            "Rate": must_alias_rate * 100
            })
        rows.append({
            "AA": AA,
            "Benchmark": benchmark,
            "Response": "NoAlias",
            "Rate": no_alias_rate * 100
            })

    return pd.DataFrame(rows)

def parse_text_total_responses(text):
    text = text.strip()
    lines = text.split("\n")

    rows = []

    # The current alias analysis being used
    AA = None
    for line in lines:
        if line == "":
            continue
        parts = line.split(" ")
        if len(parts) == 1:
            AA, = parts
            continue

        # Skip empty parts
        parts = [part for part in parts if part]
        benchmark, no_alias, may_alias, must_alias, _ = parts
        no_alias = float(no_alias)
        may_alias = float(may_alias)
        must_alias = float(must_alias)
        total = no_alias + may_alias + must_alias

        rows.append({
            "AA": AA,
            "Benchmark": benchmark,
            "Response": "MayAlias",
            "Rate": may_alias / total * 100
            })
        rows.append({
            "AA": AA,
            "Benchmark": benchmark,
            "Response": "MustAlias",
            "Rate": must_alias / total * 100
            })
        rows.append({
            "AA": AA,
            "Benchmark": benchmark,
            "Response": "NoAlias",
            "Rate": no_alias / total * 100
            })

    return pd.DataFrame(rows)


CS_NoDedup_AverageClobber = """
BasicAA
500.perlbench  0.804925  0.132681   0.062342
502.gcc        0.819753  0.058408   0.121347
505.mcf        0.826400  0.123476   0.050124
507.cactuBSSN  0.891204  0.059418   0.049354
525.x264       0.833818  0.110513   0.055135
526.blender    0.818740  0.077578   0.103156
538.imagick    0.845298  0.069975   0.084445
544.nab        0.842944  0.086891   0.069670
557.xz         0.827778  0.082717   0.088873
emacs-29.4           0.831961  0.055891   0.110984
gdb-15.2             0.830937  0.074817   0.093727
ghostscript-10.04.0  0.859720  0.067912   0.072056
sendmail-8.18.1      0.803455  0.126010   0.069389

LlvmAA
500.perlbench  0.829937  0.107493   0.062518
502.gcc        0.824115  0.053869   0.121523
505.mcf        0.838202  0.111204   0.050594
507.cactuBSSN  0.747390  0.203120   0.049465
525.x264       0.830692  0.113428   0.055347
526.blender    0.820466  0.075790   0.103219
538.imagick    0.837878  0.077217   0.084622
544.nab        0.839827  0.089936   0.069742
557.xz         0.812210  0.098177   0.088982
emacs-29.4           0.839675  0.048021   0.111140
gdb-15.2             0.834699  0.070888   0.093895
ghostscript-10.04.0  0.861873  0.065581   0.072235
sendmail-8.18.1      0.842777  0.085923   0.070154

PointsToGraphAA
500.perlbench  0.825768  0.112106   0.062074
502.gcc        0.818755  0.062096   0.118657
505.mcf        0.842263  0.107673   0.050064
507.cactuBSSN  0.899314  0.051559   0.049103
525.x264       0.838522  0.106056   0.054889
526.blender    0.812926  0.084145   0.102403
538.imagick    0.849984  0.066144   0.083591
544.nab        0.866292  0.063712   0.069501
557.xz         0.825893  0.092460   0.081015
emacs-29.4           0.829795  0.060836   0.108205
gdb-15.2             0.837637  0.068592   0.093253
ghostscript-10.04.0  0.860027  0.068240   0.071421
sendmail-8.18.1      0.838615  0.091872   0.068367

ChainedAA(PointsToGraphAA,LlvmAA)
500.perlbench  0.851657  0.085774   0.062517
502.gcc        0.834760  0.043069   0.121678
505.mcf        0.846968  0.102439   0.050594
507.cactuBSSN  0.901915  0.048595   0.049466
525.x264       0.844632  0.099488   0.055347
526.blender    0.824223  0.072033   0.103219
538.imagick    0.860195  0.054901   0.084622
544.nab        0.868775  0.060988   0.069742
557.xz         0.844598  0.065788   0.088982
emacs-29.4           0.848958  0.038736   0.111142
gdb-15.2             0.845141  0.060445   0.093896
ghostscript-10.04.0  0.869496  0.057958   0.072235
sendmail-8.18.1      0.856676  0.072024   0.070154
"""

CS_NoDedup_TotalResponses = """
BasicAA
500.perlbench         41424937.0  17076789.0   1695276.0  0.283682
502.gcc              435617425.0  18462055.0  95247938.0  0.033608
505.mcf                 152390.0     25387.0      5576.0  0.138460
507.cactuBSSN        289664689.0  20686707.0  14922846.0  0.063598
525.x264               5176188.0    549370.0    159062.0  0.093357
526.blender           46686931.0   5613352.0   2445903.0  0.102534
538.imagick          260169588.0  38004488.0  17050291.0  0.120563
544.nab                1526770.0    238695.0     82016.0  0.129200
557.xz                 3328720.0    511520.0    286950.0  0.123939
emacs-29.4            28045633.0   2426329.0    998741.0  0.077098
gdb-15.2              14717167.0   1670172.0    679776.0  0.097859
ghostscript-10.04.0   75319757.0   7678751.0   4129770.0  0.088132
sendmail-8.18.1        4638958.0   1008949.0    179555.0  0.173137

LlvmAA
500.perlbench         47856084.0  10636352.0   1704566.0  0.176692
502.gcc              426197136.0  27867269.0  95263013.0  0.050730
505.mcf                 154322.0     23376.0      5655.0  0.127492
507.cactuBSSN        220065629.0  90270294.0  14938319.0  0.277521
525.x264               5049437.0    675694.0    159489.0  0.114824
526.blender           46607505.0   5686889.0   2451792.0  0.103877
538.imagick          251075201.0  47095961.0  17053205.0  0.149405
544.nab                1503810.0    261626.0     82045.0  0.141612
557.xz                 2977202.0    863007.0    286981.0  0.209103
emacs-29.4            28001001.0   2467895.0   1001807.0  0.078419
gdb-15.2              14548777.0   1835888.0    682450.0  0.107569
ghostscript-10.04.0   74186733.0   8788864.0   4152681.0  0.100873
sendmail-8.18.1        5033499.0    609612.0    184351.0  0.104610

PointsToGraphAA
500.perlbench         46687187.0  11822276.0   1687539.0  0.196393
502.gcc              433238088.0  21402002.0  94687328.0  0.038960
505.mcf                 155505.0     22273.0      5575.0  0.121476
507.cactuBSSN        291048702.0  19312033.0  14913507.0  0.059372
525.x264               5155555.0    575906.0    153159.0  0.097866
526.blender           45624269.0   6919734.0   2202183.0  0.126397
538.imagick          260220665.0  37977115.0  17026587.0  0.120476
544.nab                1616284.0    149292.0     81905.0  0.080808
557.xz                 3470967.0    527629.0    128594.0  0.127842
emacs-29.4            28183017.0   2316903.0    970783.0  0.073621
gdb-15.2              14858510.0   1539527.0    669078.0  0.090204
ghostscript-10.04.0   75675107.0   7417152.0   4036019.0  0.085129
sendmail-8.18.1        5027463.0    627794.0    172205.0  0.107730

ChainedAA(PointsToGraphAA,LlvmAA)
500.perlbench         50585145.0   7907295.0   1704562.0  0.131357
502.gcc              437105435.0  16958609.0  95263374.0  0.030872
505.mcf                 156666.0     21032.0      5655.0  0.114708
507.cactuBSSN        291088789.0  19247130.0  14938323.0  0.059172
525.x264               5225073.0    500058.0    159489.0  0.084977
526.blender           47074757.0   5219597.0   2451832.0  0.095342
538.imagick          268533568.0  29637594.0  17053205.0  0.094021
544.nab                1619025.0    146411.0     82045.0  0.079249
557.xz                 3646930.0    193279.0    286981.0  0.046831
emacs-29.4            28937312.0   1531579.0   1001812.0  0.048667
gdb-15.2              15068764.0   1315892.0    682459.0  0.077101
ghostscript-10.04.0   76720032.0   6255565.0   4152681.0  0.071797
sendmail-8.18.1        5168607.0    474504.0    184351.0  0.081425
"""

#data = parse_text_average(CS_NoDedup_AverageClobber)
#plot(data, ylabel="Average Store MayAlias %", savefig="precision.pdf")

data = parse_text_total_responses(CS_NoDedup_TotalResponses)
plot(data, ylabel="MayAlias Response %", savefig="precision.pdf")
