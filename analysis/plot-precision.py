#!/usr/bin/env python3

import plotly.express as px
import pandas as pd
import re

import plotly.io as pio
pio.kaleido.scope.mathjax = None

def plot(data, title=None):

    data.loc[data["AA"] == "BasicAA", "AA"] = "local"
    data.loc[data["AA"] == "PointsToGraphAA", "AA"] = "andersen"
    data.loc[data["AA"] == "ChainedAA(PointsToGraphAA,BasicAA)", "AA"] = "both"

    # Skip the "only PtG column"
    # data = data[data["AA"] != "andersen"]

    data = data[data["Response"] != "NoAlias"]
    data = data[data["Response"] != "MustAlias"]

    fig = px.bar(
        data,
        x="Benchmark",
        y="Count",
        color="AA",
        barmode="group",
        title=title)

    fig.update_layout(
        barmode='stack',
        yaxis_title='Alias Query Responses',
        uniformtext_minsize=8,
        uniformtext_mode='hide')

    # fig.update_yaxes(range=[0, 100])
    fig.show()


def parse_text(text):
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
        benchmark, no_alias, may_alias, must_alias, rate = parts
        no_alias = int(float(no_alias))
        may_alias = int(float(may_alias))
        must_alias = int(float(must_alias))

        total_queries = no_alias + may_alias + must_alias

        rows.append({
            "AA": AA,
            "Benchmark": benchmark,
            "Response": "MayAlias",
            "Count": may_alias / total_queries * 100
                    })

        rows.append({
            "AA": AA,
            "Benchmark": benchmark,
            "Response": "MustAlias",
            "Count": must_alias / total_queries * 100
                    })

        rows.append({
            "AA": AA,
            "Benchmark": benchmark,
            "Response": "NoAlias",
            "Count": no_alias / total_queries * 100
                    })

    return pd.DataFrame(rows)


def plot_weighted(data, title, savefig=None):

    data.loc[data["AA"] == "BasicAA", "AA"] = "local"
    data.loc[data["AA"] == "PointsToGraphAA", "AA"] = "andersen"
    data.loc[data["AA"] == "ChainedAA(PointsToGraphAA,BasicAA)", "AA"] = "both"

    # Skip the "only PtG column"
    # data = data[data["AA"] != "andersen"]

    benchmarks = data["Benchmark"].unique()
    benchmark_ticks = {}
    for benchmark in benchmarks:
        benchmark_ticks[benchmark] = re.sub("[-\\.]", "<br>", benchmark, count=1)

    # Only show MayAlias
    data = data[data["Response"] != "NoAlias"]
    data = data[data["Response"] != "MustAlias"]

    fig = px.bar(
        data,
        x="Benchmark",
        y="Rate",
        color="AA",
        barmode="group",
        title=title)

    fig.update_traces(marker_line_color='rgb(20,20,20)', marker_line_width=1.5, opacity=0.8)

    fig.update_yaxes(
        mirror=True,
        ticks='inside',
        tickmode = 'linear',
        tick0 = 0,
        dtick = 2,
        showline=True,
        linecolor='black',
        gridcolor='lightgrey')
    fig.update_xaxes(
        mirror=True,
        showline=True,
        linecolor='black',
        type='category',
        tickangle=90,
        labelalias=benchmark_ticks
    )
    fig.update_layout(
        xaxis_title=None,
        yaxis_title="Average Store May Alias %",
        plot_bgcolor='white',
        autosize=False,
        width=600,
        height=250,
        margin=dict(
            l=0,
            r=0,
            b=0,
            t=0,
            pad=0
        )
    )

    fig.update_layout(
        legend_title_text=None,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=0.99,
            xanchor="right",
            x=0.99,
            bgcolor="rgba(0,0,0,0)"
        ))

    if savefig is not None:
        fig.write_image(savefig)

    fig.show()


def parse_text_weighted(text):
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



ALS_NoDedup_NoMem2reg_YesEA = """
BasicAA
500.perlbench         8639726.0   38373538.0    51708.0  0.815331
502.gcc              23612498.0  129594086.0  2646278.0  0.831516
505.mcf                 31216.0      59992.0       10.0  0.657677
507.cactuBSSN        15080294.0   51332700.0    40846.0  0.772456
525.x264              1372012.0    2401990.0    16214.0  0.633734
526.blender          15078068.0   20225754.0   343138.0  0.567391
538.imagick           5165864.0   98454544.0   377606.0  0.946696
544.nab                290368.0     542706.0      190.0  0.651301
557.xz                 822830.0    1117452.0   230292.0  0.514819
emacs-29.4            8621516.0   13252206.0   144686.0  0.601869
gdb-15.2                88488.0      86688.0     1062.0  0.491880
ghostscript-10.04.0  14733572.0   28117152.0   177024.0  0.653466
sendmail-8.18.1        986884.0    1816290.0    10008.0  0.645635

PointsToGraphAA
500.perlbench        12404170.0   34660724.0       78.0  0.736444
502.gcc              20083710.0  135765918.0     3234.0  0.871116
505.mcf                 39436.0      51782.0        0.0  0.567673
507.cactuBSSN        16458084.0   49995736.0       20.0  0.752338
525.x264              1515044.0    2275172.0        0.0  0.600275
526.blender          14593010.0   21053810.0      140.0  0.590620
538.imagick           5740480.0   98257526.0        8.0  0.944802
544.nab                389666.0     443590.0        8.0  0.532352
557.xz                1150136.0    1020438.0        0.0  0.470124
emacs-29.4            8578962.0   13439374.0       72.0  0.610370
gdb-15.2               101690.0      74548.0        0.0  0.422996
ghostscript-10.04.0  16640874.0   26386860.0       14.0  0.613252
sendmail-8.18.1       1165860.0    1647224.0       98.0  0.585538

ChainedAA(PointsToGraphAA,BasicAA)
500.perlbench        13039608.0   33973652.0    51712.0  0.721846
502.gcc              26070030.0  127133368.0  2649464.0  0.815727
505.mcf                 39514.0      51694.0       10.0  0.566708
507.cactuBSSN        16801350.0   49611624.0    40866.0  0.746558
525.x264              1629866.0    2144136.0    16214.0  0.565703
526.blender          16068190.0   19235504.0   343266.0  0.539611
538.imagick           5984924.0   97635484.0   377606.0  0.938821
544.nab                391178.0     441888.0      198.0  0.530310
557.xz                1548298.0     391984.0   230292.0  0.180590
emacs-29.4            9979724.0   11893942.0   144742.0  0.540182
gdb-15.2               105586.0      69590.0     1062.0  0.394864
ghostscript-10.04.0  17268824.0   25581894.0   177030.0  0.594544
sendmail-8.18.1       1184828.0    1618270.0    10084.0  0.575245
"""

CS_NoDedup_NoMem2reg_YesEA = """
BasicAA
500.perlbench        0.775177  0.162430   0.062342
502.gcc              0.811340  0.067903   0.120312
505.mcf              0.819263  0.130612   0.050124
507.cactuBSSN        0.890392  0.060230   0.049354
525.x264             0.824669  0.119663   0.055135
526.blender          0.809476  0.081308   0.108698
538.imagick          0.839446  0.080201   0.080107
544.nab              0.838371  0.091464   0.069670
557.xz               0.817447  0.093048   0.088873
emacs-29.4           0.819083  0.068770   0.110984
gdb-15.2             0.842923  0.057178   0.099562
ghostscript-10.04.0  0.850902  0.076731   0.072056
sendmail-8.18.1      0.789630  0.139835   0.069389

PointsToGraphAA
500.perlbench        0.825768  0.112106   0.062074
502.gcc              0.818884  0.063151   0.117519
505.mcf              0.842263  0.107673   0.050064
507.cactuBSSN        0.899314  0.051559   0.049103
525.x264             0.838522  0.106056   0.054889
526.blender          0.809597  0.082438   0.107449
538.imagick          0.848207  0.072221   0.079327
544.nab              0.866292  0.063712   0.069501
557.xz               0.825893  0.092460   0.081015
emacs-29.4           0.829795  0.060836   0.108205
gdb-15.2             0.857611  0.043010   0.099042
ghostscript-10.04.0  0.860027  0.068240   0.071421
sendmail-8.18.1      0.838615  0.091872   0.068367

ChainedAA(PointsToGraphAA,BasicAA)
500.perlbench        0.826957  0.110650   0.062341
502.gcc              0.829705  0.049396   0.120454
505.mcf              0.843037  0.106839   0.050124
507.cactuBSSN        0.901651  0.048970   0.049355
525.x264             0.841660  0.102672   0.055135
526.blender          0.816747  0.074035   0.108701
538.imagick          0.851403  0.068245   0.080107
544.nab              0.867791  0.062044   0.069670
557.xz               0.841782  0.068714   0.088873
emacs-29.4           0.841451  0.046399   0.110985
gdb-15.2             0.859406  0.040695   0.099562
ghostscript-10.04.0  0.863311  0.064321   0.072056
sendmail-8.18.1      0.844901  0.084558   0.069395
"""

#data = parse_text(ALS_NoDedup_NoMem2reg_YesEA)
#plot(data)

data = parse_text_weighted(CS_NoDedup_NoMem2reg_YesEA)
plot_weighted(data, None, savefig="precision.pdf")
