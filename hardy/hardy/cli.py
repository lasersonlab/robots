import sys
from bisect import bisect_left
from io import StringIO
from itertools import product
from pathlib import Path
from pprint import pprint
from random import seed, shuffle
from textwrap import dedent
from datetime import datetime

import pandas as pd
import plotly.graph_objs as go
import yaml
from click import Path as ClickPath
from click import File, group, option, version_option
from plotly.colors import (
    PLOTLY_SCALES,
    colorscale_to_colors,
    colorscale_to_scale,
    find_intermediate_color,
    hex_to_rgb,
    label_rgb,
)
from plotly.offline import plot
from sample_sheet import SampleSheet, Sample


__version__ = "0.0.0"


def all_wells():
    return [f"{r}{c}" for r, c in product("ABCDEFGH", range(1, 13))]


def load_data(input):
    if input.name.endswith(".xls") or input.name.endswith(".xlsx"):
        return pd.read_excel(input, header=0)
    elif input.name.endswith(".tsv"):
        return pd.read_table(input, sep="\t", header=0)
    elif input.name.endswith(".csv"):
        return pd.read_table(input, sep=",", header=0)
    else:
        raise ValueError("Input must be .tsv, .csv, .xls, or .xlsx")


def load_template_protocol():
    template_path = Path(__file__).resolve().parent / "template-protocol.py"
    with open(template_path, "r") as ip:
        return ip.read()


def instantiate_template_protocol(df, output_path):
    with open(output_path, "w") as op:
        cols = [
            "norm_flag",
            "source_well",
            "dest_well",
            "transfer_vol_ul",
        ]
        buf = StringIO()
        df.to_csv(buf, columns=cols, sep="\t", index=False, float_format="%.3f")
        print(load_template_protocol().format(buf.getvalue()), file=op)


def validate_data(df):
    reqd_cols = ["library_id", "sample_id", "source_well", "conc_ug_ml"]
    if not (set(reqd_cols) <= set(df.columns)):
        raise ValueError(
            "Input file must contain the following columns: {}".format(reqd_cols)
        )
    if len(df) != 96:
        raise ValueError("There must be 96 values in the source_well column")
    if df["source_well"].isnull().sum() > 0:
        raise ValueError("Empty/null source_wells are not allowed")
    if len(set(df["source_well"])) != len(df):
        raise ValueError("Each row must have a unique source_well")
    if len(set(df["source_well"]) - set(all_wells())) > 0:
        raise ValueError(
            "invalid source_well values: {}".format(
                set(df["source_well"]) - set(all_wells())
            )
        )
    notnull = df["library_id"].notnull()
    if len(set(df["library_id"][notnull])) < len(df[notnull]):
        raise ValueError("Each row must have a unique library_id")


def set_seed(df):
    seed("".join(df["library_id"][df["library_id"].notnull()]))


def summarize_output(df):
    summary = {
        "median_valid_transfer_vol_ul": df.loc[
            df["norm_flag"] == "valid", "transfer_vol_ul"
        ].median(),
        "num_libraries": df["library_id"].notnull().sum().tolist(),
        "num_valid": (df["norm_flag"] == "valid").sum().tolist(),
        "num_invalid": (df["norm_flag"] == "invalid").sum().tolist(),
        "num_too_dilute": (df["norm_flag"] == "too_dilute").sum().tolist(),
        "num_too_concentrated": (df["norm_flag"] == "too_concentrated").sum().tolist(),
        "num_empty": (df["norm_flag"] == "empty").sum().tolist(),
        "num_weird": (df["norm_flag"] == "weird").sum().tolist(),
    }
    pprint(summary, stream=sys.stderr)
    return summary


def compute_normalization(df, transfer_mass_ug, min_volume, max_volume, shuffle_wells):
    df = df.copy(deep=True)

    df["transfer_vol_ul"] = transfer_mass_ug / df["conc_ug_ml"] * 1000  # µL

    # set flag
    empty = df["transfer_vol_ul"].isnull()
    too_dilute = df["transfer_vol_ul"] > max_volume
    too_concentrated = df["transfer_vol_ul"] < min_volume
    valid = ~too_dilute & ~too_concentrated & ~empty

    df["norm_flag"] = "weird"
    df.loc[valid, "norm_flag"] = "valid"
    df.loc[empty, "norm_flag"] = "empty"
    df.loc[too_dilute, "norm_flag"] = "too_dilute"
    df.loc[too_concentrated, "norm_flag"] = "too_concentrated"

    # randomize positions if requested
    if shuffle_wells:
        if len(set(["bc_well", "bc_seq", "bc_read"]) & set(df.columns)) > 0:
            raise ValueError(
                "When shuffling wells, input cannot already have barcode associations"
            )
        set_seed(df)  # ensures deterministic shuffling
        shuffled_wells = all_wells()
        shuffle(shuffled_wells)
        df["dest_well"] = shuffled_wells
    else:
        df["dest_well"] = df["source_well"]

    return df


def attach_barcodes(df, barcodes_file):
    barcodes = load_data(barcodes_file)
    if len({"plate_well", "bc_read"} - set(barcodes.columns)) > 0:
        raise ValueError("Barcode file must include columns plate_well and bc_read")
    return pd.merge(
        df,
        barcodes[["plate_well", "bc_read"]],
        how="inner",
        left_on="dest_well",
        right_on="plate_well",
        validate="1:1",
    )


def create_sample_sheet(df, experiment_name):
    sample_sheet = SampleSheet()

    sample_sheet.Header["IEM4FileVersion"] = 4
    sample_sheet.Header["Investigator Name"] = "Laserson Lab"
    sample_sheet.Header["Experiment Name"] = experiment_name
    sample_sheet.Header["Date"] = datetime.today().strftime("%Y-%m-%d")
    sample_sheet.Header["Workflow"] = "GenerateFASTQ"
    sample_sheet.Header["Application"] = "NextSeq FASTQ Only"
    sample_sheet.Header["Assay"] = "TruSeq HT"
    sample_sheet.Header["Description"] = ""
    sample_sheet.Header["Chemistry"] = "Default"

    sample_sheet.Reads = [75]

    notnull = df["library_id"].notnull()
    for tup in df[notnull].itertuples(index=False):
        sample = Sample({"Sample_ID": tup.library_id, "index": tup.bc_read})
        sample_sheet.add_sample(sample)

    return sample_sheet


def _compute_color(color, cmin, cmax, colorscale):
    cs_colors = [hex_to_rgb(c) for c in colorscale_to_colors(PLOTLY_SCALES[colorscale])]
    cs_scale = colorscale_to_scale(PLOTLY_SCALES[colorscale])
    if color < cmin or color > cmax:
        raise ValueError("Must have cmin <= color <= cmax!")
    if color == cmin:
        return label_rgb(cs_colors[0])
    normed = (color - cmin) / (cmax - cmin)
    i = bisect_left(cs_scale, normed)
    intermed = (normed - cs_scale[i - 1]) / (cs_scale[i] - cs_scale[i - 1])
    return label_rgb(find_intermediate_color(cs_colors[i - 1], cs_colors[i], intermed))


def draw_plate(df, output_path):
    row2num = {c: i + 1 for (i, c) in enumerate("ABCDEFGH")}
    notnull = df["library_id"].notnull()
    num_libraries = notnull.sum()
    offset = 15  # number of "well" units to move second plate over
    traces = []
    for n, tup in enumerate(df[notnull].itertuples(index=False)):
        x1 = int(tup.source_well[1:])
        y1 = row2num[tup.source_well[0]]
        x2 = int(tup.dest_well[1:])
        y2 = row2num[tup.dest_well[0]]
        color = _compute_color(n, 0, num_libraries - 1, "Viridis")
        marker = go.scatter.Marker(size=25, cmin=0, color=color)
        if tup.norm_flag == "empty":
            marker.update(line=go.scatter.marker.Line(color="orange", width=5))
        elif tup.norm_flag != "valid":
            marker.update(line=go.scatter.marker.Line(color="red", width=5))
        line = go.scatter.Line(color=color)
        trace = go.Scatter(
            x=[x1, x2 + offset],
            y=[y1, y2],
            mode="markers",
            marker=marker,
            line=line,
            text=f"{tup.source_well} => {tup.dest_well}<br>{tup.library_id}<br>transfer: {tup.transfer_vol_ul:.2f} µL<br>{tup.norm_flag}",
            hoverinfo="text",
        )
        traces.append(trace)

    layout = go.Layout(
        height=500,
        width=1200,
        showlegend=False,
        xaxis=go.layout.XAxis(
            range=[0, 12 + offset + 1],
            tickvals=[i for i in range(1, 13)] + [i + offset for i in range(1, 13)],
            ticktext=[str(i) for i in range(1, 13)] * 2,
        ),
        yaxis=go.layout.YAxis(
            scaleanchor="x",
            range=[9, 0],  # reversed axis
            tickvals=list(range(1, 9)),
            ticktext=[c for c in "ABCDEFGH"],
        ),
        hovermode="closest",
    )
    fig = go.Figure(data=traces, layout=layout)
    return fig


@group(context_settings={"help_option_names": ["-h", "--help"]})
@version_option(__version__)
def cli():
    """hardy -- OT-2 robot"""
    print(
        dedent(
            """
                    **************************************
                    *                                    *
                    *  Concentrations MUST be in µg/mL!  *
                    *                                    *
                    **************************************
                    """
        ),
        file=sys.stderr,
    )


@cli.command(name="phip-norm")
@option("-i", "--input", type=File("rb"), required=True, help="min cols: library_id,sample_id,source_well,conc_ug_ml")
@option("-o", "--output-dir", type=ClickPath(exists=False), required=True)
@option("-b", "--barcodes", type=File("rb"), required=True, help="min cols: plate_well,bc_read")
@option("-t", "--transfer-mass", type=float, default=2, help="mass to transfer (µg)")
@option(
    "-m", "--min-volume", type=float, default=3, help="minimum transfer volume (µL)"
)
@option(
    "-M", "--max-volume", type=float, default=100, help="maximum transfer volume (µL)"
)
@option("--shuffle-wells", is_flag=True, help="shuffle wells (deterministically)")
def prepare_phip_normalization(
    input, output_dir, barcodes, transfer_mass, min_volume, max_volume, shuffle_wells
):
    """Normalize and shuffle serum samples for PhIP-seq

    See README.md for detailed instructions.
    """
    df = load_data(input)
    validate_data(df)
    df = compute_normalization(df, transfer_mass, min_volume, max_volume, shuffle_wells)
    df = attach_barcodes(df, barcodes)
    summary = summarize_output(df)
    summary["invocation"] = " ".join(sys.argv)

    output_dir = Path(output_dir)
    output_dir.mkdir(mode=0o755)
    experiment_name = output_dir.name

    # write summary.yaml
    with open(output_dir / "summary.yaml", "w") as op:
        print(yaml.dump(summary, default_flow_style=False), file=op)

    # write plate-normalization-shuffle.tsv
    df.to_csv(
        output_dir / "plate-normalization-shuffle.tsv",
        sep="\t",
        index=False,
        float_format="%.3f",
    )

    # write {experiment_name}-sample-sheet.csv
    sample_sheet = create_sample_sheet(df, experiment_name)
    with open(output_dir / f"{experiment_name}-sample-sheet.csv", "w") as op:
        sample_sheet.write(op)

    # write execute-normalization-shuffle.py
    instantiate_template_protocol(df, output_dir / "execute-normalization-shuffle.py")

    # write plate-viz.html
    fig = draw_plate(df, output_dir)
    plot(
        fig,
        filename=str(output_dir / "plate-viz.html"),
        show_link=False,
        auto_open=False,
    )


if __name__ == "__main__":
    cli()
