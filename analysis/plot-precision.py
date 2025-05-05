#!/usr/bin/env python3

import plotly.express as px
import pandas as pd

import plotly.io as pio
pio.kaleido.scope.mathjax = None

def plot(data, title):
    fig = px.bar(
        data,
        x="AA",
        y="Count",
        color="Response",
        facet_col="Benchmark",
        title=title)

    fig.update_layout(
        barmode='stack',
        yaxis_title='Alias Query Responses',
        uniformtext_minsize=8,
        uniformtext_mode='hide')

    fig.update_yaxes(range=[0, 100])
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

    if savefig is not None:
        data = data[data["AA"] != "PointsToGraphAA"]
        data.loc[data["AA"] == "BasicAA", "AA"] = "local"
        data.loc[data["AA"] == "ChainedAA(PointsToGraphAA,BasicAA)", "AA"] = "andersen"

    fig = px.bar(
        data,
        x="Benchmark",
        y="MayAlias",
        color="AA",
        color_discrete_sequence=["lightgray", "gray", "blue"],
        #pattern_shape="AA",
        #pattern_shape_sequence=[".", "x"],
        barmode='group',
        title=title)

    fig.update_traces(marker_line_color='rgb(20,20,20)', marker_line_width=1.5, opacity=0.8)
    fig.update_yaxes(
        range=[0, 60],
        mirror=True,
        ticks='inside',
        tickmode = 'linear',
        tick0 = 0,
        dtick = 10,
        showline=True,
        linecolor='black',
        gridcolor='lightgrey')
    fig.update_xaxes(
        mirror=True,
        showline=True,
        linecolor='black')
    fig.update_layout(
        xaxis_title=None,
        yaxis_title="Average store may alias %",
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
        ))
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
        benchmark, may_alias_rate = parts
        may_alias_rate = float(may_alias_rate)

        rows.append({
            "AA": AA,
            "Benchmark": benchmark,
            "MayAlias": may_alias_rate * 100
            })

    return pd.DataFrame(rows)


#                  NoAlias     MayAlias   MustAlias   MayRate
ALS_NoDedup_NoMem2reg = """
BasicAA
500.perlbench  9.139252e+07  189080816.0   19744916.0  0.629811
502.gcc        1.627827e+09  459779338.0  442197680.0  0.181745
505.mcf        3.404980e+05     349074.0      45778.0  0.474705
507.cactuBSSN  6.844409e+08  528591872.0   73512528.0  0.410861
525.x264       1.690442e+07   11607704.0    1797762.0  0.382968
526.blender    1.084301e+08  101868952.0   12755438.0  0.456700
538.imagick    8.842164e+08  211074222.0  132466076.0  0.171919
544.nab        4.416984e+06    3323154.0     586308.0  0.399108
557.xz         9.484716e+06    5259164.0    1125360.0  0.331406

PointsToGraphAA
500.perlbench  2.380857e+08   34926268.0   27206264.0  0.116336
502.gcc        1.954901e+09  130143372.0  444759198.0  0.051444
505.mcf        6.295260e+05      60060.0      45764.0  0.081675
507.cactuBSSN  1.143679e+09   69381556.0   73484598.0  0.053929
525.x264       2.639963e+07    2138718.0    1771534.0  0.070562
526.blender    1.884744e+08   21911892.0   12668190.0  0.098236
538.imagick    9.873031e+08  108275982.0  132177618.0  0.088190
544.nab        7.329380e+06     390516.0     606550.0  0.046901
557.xz         1.357833e+07    1563466.0     727440.0  0.098522

ChainedAA(PointsToGraphAA,BasicAA)
500.perlbench  2.387757e+08   34076496.0   27366048.0  0.113506
502.gcc        1.964270e+09  117999328.0  447534722.0  0.046644
505.mcf        6.295740e+05      59918.0      45858.0  0.081482
507.cactuBSSN  1.144032e+09   68978160.0   73534932.0  0.053615
525.x264       2.656579e+07    1945180.0    1798920.0  0.064176
526.blender    1.900091e+08   20019956.0   13025358.0  0.089754
538.imagick    9.875964e+08  107589830.0  132570464.0  0.087631
544.nab        7.330944e+06     388576.0     606926.0  0.046668
557.xz         1.417198e+07     568360.0    1128900.0  0.035815
"""

CS_NoDedup_NoMem2reg = """
BasicAA
500.perlbench   19869929.0   38631797.0   1695276.0  0.641756
502.gcc        383937467.0   70142013.0  95247938.0  0.127687
505.mcf            73049.0     104728.0      5576.0  0.571182
507.cactuBSSN  170143978.0  140207418.0  14922846.0  0.431044
525.x264         3418157.0    2307401.0    159062.0  0.392107
526.blender     28105093.0   24195190.0   2445903.0  0.441952
538.imagick    236002932.0   62171144.0  17050291.0  0.197228
544.nab           952007.0     813458.0     82016.0  0.440307
557.xz           2270864.0    1569376.0    286950.0  0.380253

PointsToGraphAA
500.perlbench   49524380.0   7436357.0   3236265.0  0.123534
502.gcc        436708973.0  17762225.0  94856220.0  0.032334
505.mcf           155751.0     22021.0      5581.0  0.120102
507.cactuBSSN  291103035.0  19254169.0  14917038.0  0.059194
525.x264         5217164.0    514206.0    153250.0  0.087381
526.blender     45972180.0   6547158.0   2226848.0  0.119591
538.imagick    261280564.0  36913344.0  17030459.0  0.117102
544.nab          1637932.0    119886.0     89663.0  0.064892
557.xz           3471970.0    526184.0    129036.0  0.127492

ChainedAA(PointsToGraphAA,BasicAA)
500.perlbench   49591074.0   7361789.0   3244139.0  0.122295
502.gcc        438733934.0  15176157.0  95417327.0  0.027627
505.mcf           155756.0     22015.0      5582.0  0.120069
507.cactuBSSN  291128092.0  19219769.0  14926381.0  0.059088
525.x264         5254543.0    470924.0    159153.0  0.080026
526.blender     47056652.0   5218926.0   2470608.0  0.095329
538.imagick    261348284.0  36821920.0  17054163.0  0.116812
544.nab          1638902.0    118805.0     89774.0  0.064306
557.xz           3646259.0    193539.0    287392.0  0.046849
"""

CS_NoDedup_NoMem2reg_Weighted = """
BasicAA
500.perlbench    0.494323
502.gcc          0.318076
505.mcf          0.539064
507.cactuBSSN    0.392729
525.x264         0.448605
526.blender      0.393168
538.imagick      0.319728
544.nab          0.403361
557.xz           0.391293

PointsToGraphAA
500.perlbench    0.080425
502.gcc          0.051833
505.mcf          0.107386
507.cactuBSSN    0.051097
525.x264         0.095276
526.blender      0.075971
538.imagick      0.073272
544.nab          0.054407
557.xz           0.098483

ChainedAA(PointsToGraphAA,BasicAA)
500.perlbench    0.079155
502.gcc          0.041420
505.mcf          0.107116
507.cactuBSSN    0.050101
525.x264         0.092020
526.blender      0.070178
538.imagick      0.069454
544.nab          0.053307
557.xz           0.066016
"""

ALS_YesDedup_NoMem2reg = """
BasicAA
500.perlbench   1649298.0   45363896.0    51778.0  0.963857
502.gcc        15301046.0  137905534.0  2646282.0  0.884844
505.mcf            5920.0      85288.0       10.0  0.934991
507.cactuBSSN   4780856.0   61632138.0    40846.0  0.927443
525.x264         549054.0    3224948.0    16214.0  0.850861
526.blender     5792494.0   29511328.0   343138.0  0.827878
538.imagick     3316708.0  100303700.0   377606.0  0.964477
544.nab           91136.0     741938.0      190.0  0.890400
557.xz           694638.0    1245644.0   230292.0  0.573878

PointsToGraphAA
500.perlbench  14933662.0   31656132.0   475178.0  0.672605
502.gcc        34060104.0  121421058.0   371700.0  0.779075
505.mcf           39564.0      51596.0       58.0  0.565634
507.cactuBSSN  16758940.0   49685660.0     9240.0  0.747672
525.x264        1822246.0    1967538.0      432.0  0.519110
526.blender    15735336.0   19805706.0   105918.0  0.555607
538.imagick     9856188.0   94132672.0     9154.0  0.905139
544.nab          463650.0     363834.0     5780.0  0.436637
557.xz          1152654.0    1017112.0      808.0  0.468591

ChainedAA(PointsToGraphAA,BasicAA)
500.perlbench  15568674.0   30969350.0   526948.0  0.658013
502.gcc        40044642.0  112790238.0  3017982.0  0.723697
505.mcf           39612.0      51538.0       68.0  0.564998
507.cactuBSSN  17099626.0   49304128.0    50086.0  0.741930
525.x264        1936968.0    1836602.0    16646.0  0.484564
526.blender    17209072.0   17988838.0   449050.0  0.504639
538.imagick    10100440.0   93510822.0   386752.0  0.899160
544.nab          465152.0     362142.0     5970.0  0.434607
557.xz          1550796.0     388678.0   231100.0  0.179067
"""

ALS_YesDedup_YesMem2reg = """
BasicAA
500.perlbench   5555092.0   29347160.0  1125196.0  0.814578
502.gcc        18632920.0  105403012.0  7121996.0  0.803634
505.mcf           12272.0      40268.0     1332.0  0.747475
507.cactuBSSN   1391284.0   41499462.0   366134.0  0.959373
525.x264         827134.0    1780200.0    50986.0  0.669671
526.blender     5527972.0   16755122.0  1131742.0  0.715577
538.imagick     1810496.0   92736476.0   481152.0  0.975885
544.nab          163328.0     383694.0    13498.0  0.684532
557.xz           658514.0    1066322.0   244190.0  0.541548

PointsToGraphAA
500.perlbench   6567176.0   29005272.0   455000.0  0.805088
502.gcc        20679960.0  110147520.0   330448.0  0.839808
505.mcf            6008.0      47786.0       78.0  0.887029
507.cactuBSSN   3588952.0   39658864.0     9064.0  0.916822
525.x264         693990.0    1963904.0      426.0  0.738776
526.blender     3715638.0   19594226.0   104972.0  0.836830
538.imagick     2683876.0   92336382.0     7866.0  0.971674
544.nab          162432.0     392398.0     5690.0  0.700061
557.xz           962514.0    1005704.0      808.0  0.510762

ChainedAA(PointsToGraphAA,BasicAA)
500.perlbench  11770176.0  22677084.0  1580188.0  0.629439
502.gcc        32653148.0  91052356.0  7452424.0  0.694219
505.mcf           17556.0     34926.0     1390.0  0.648315
507.cactuBSSN   4225696.0  38656004.0   375180.0  0.893638
525.x264        1428534.0   1178374.0    51412.0  0.443278
526.blender     7945484.0  14232690.0  1236662.0  0.607849
538.imagick     3345252.0  91193862.0   489010.0  0.959651
544.nab          307714.0    233618.0    19188.0  0.416788
557.xz          1399854.0    324174.0   244998.0  0.164637
"""

CS_NoDedup_YesMem2reg_Weighted = """
BasicAA
500.perlbench    0.779407
502.gcc          0.650595
505.mcf          0.770469
507.cactuBSSN    0.834425
525.x264         0.639142
526.blender      0.599865
538.imagick      0.640940
544.nab          0.691402
557.xz           0.568762

PointsToGraphAA
500.perlbench    0.501623
502.gcc          0.515057
505.mcf          0.825986
507.cactuBSSN    0.736798
525.x264         0.741593
526.blender      0.749406
538.imagick      0.598906
544.nab          0.490915
557.xz           0.695250

ChainedAA(PointsToGraphAA,BasicAA)
500.perlbench    0.404664
502.gcc          0.349362
505.mcf          0.663441
507.cactuBSSN    0.716454
525.x264         0.434317
526.blender      0.440041
538.imagick      0.478401
544.nab          0.336874
557.xz           0.372936
"""

#data = parse_text(ALS_NoDedup_NoMem2reg)
#plot(data, "AllLoadStores - NoDedup - NoMem2reg")

#data = parse_text(ALS_NoDedup_NoMem2reg)
#plot(data, "AllLoadStores - NoDedup - NoMem2reg")

#data = parse_text(ALS_YesDedup_NoMem2reg)
#plot(data, "AllLoadStores - YesDedup - NoMem2reg")

#data = parse_text(ALS_YesDedup_YesMem2reg)
#plot(data, "AllLoadStores - YesDedup - YesMem2reg")

data = parse_text_weighted(CS_NoDedup_NoMem2reg_Weighted)
# plot_weighted(data, "Clobbering Stores - NoDedup - NoMem2reg")
plot_weighted(data, None, savefig="precision.pdf")


#data = parse_text_weighted(CS_NoDedup_YesMem2reg_Weighted)
#plot_weighted(data, "Clobbering Stores - NoDedup - YesMem2reg")
