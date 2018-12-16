#! /usr/bin/env python


"""
Concentrations can be null/empty, in which case they won't be considered
For negative/bead-only controls, leave concentrations empty
Concentrations are assumed to be in µg/mL
"""

# THIS STRING REPRESENTS THE ACTUAL OPENTRONS PROTOCOL INTO WHICH WE EMBED
# DATA (i.e., "execute-normalization.py")

protocol = """
from opentrons import containers, instruments
from csv import DictReader
from io import StringIO


data = StringIO(\"\"\"{}\"\"\")


# containers
try:
    tiprack20 = containers.load('tiprack-20ul', 'A2')
except ValueError:
    containers.create('tiprack-20ul', (8, 12), (9, 9), 3.5, 60)
    tiprack20 = containers.load('tiprack-20ul', 'A2')
tiprack200 = containers.load('tiprack-200ul', 'C2')
trash = containers.load('point', 'D2')
source_plate_1 = containers.load('96-flat', 'B1')
source_plate_2 = containers.load('96-flat', 'C1')
try:
    dest_plate = containers.load('96-square-well', 'D1')
except ValueError:
    containers.create('96-square-well', (8, 12), (9, 9), 9, 40)
    dest_plate = containers.load('96-square-well', 'D1')


# pipettes
p200 = instruments.Pipette(axis='a',
                           max_volume=200,
                           min_volume=20,
                           tip_racks=[tiprack200],
                           trash_container=trash)
p20 = instruments.Pipette(axis='b',
                          max_volume=20,
                          min_volume=2,
                          tip_racks=[tiprack20],
                          trash_container=trash)


# load transfers
p20_from = []
p20_to = []
p20_vol = []
p200_from = []
p200_to = []
p200_vol = []
reader = DictReader(data, dialect='unix', delimiter='\t', strict=True)
for row in reader:
    if row['flag'] != 'valid':
        continue

    source_well = row['source_well']
    dest_well = row['dest_well']
    if row['source_plate'] == 'plate_1':
        source_plate = source_plate_1
        volume = float(row['transfer_vol_plate_1_ul'])
    elif row['source_plate'] == 'plate_2':
        source_plate = source_plate_2
        volume = float(row['transfer_vol_plate_2_ul'])
    else:
        raise ValueError('strange source_plate: ' + source_plate)

    if volume > 20:
        p200_from.append(source_plate.well(source_well))
        p200_to.append(dest_plate.well(dest_well).bottom(1))
        p200_vol.append(volume)
    else:
        p20_from.append(source_plate.well(source_well))
        p20_to.append(dest_plate.well(dest_well).bottom(1))
        p20_vol.append(volume)


# commands
if len(p20_vol) > 0:
    p20.transfer(p20_vol, p20_from, p20_to, new_tip='always', blow_out=True)
if len(p200_vol) > 0:
    p200.transfer(p200_vol, p200_from, p200_to, new_tip='always', blow_out=True)
"""


# BEGINNING OF SCRIPT FOR PREPARING NORMALIZATION


import sys
import os
from os.path import join as pjoin
from io import StringIO
from random import shuffle, seed
from itertools import product
from textwrap import dedent

from click import command, option, File, Path
import numpy as np
import pandas as pd
import yaml


all_wells = lambda: ['{}{}'.format(r, c) for r, c in product('ABCDEFGH', range(1, 13))]
reqd_cols = [
    'library_id', 'source_well', 'conc_plate_1_ug_ml', 'conc_plate_2_ug_ml']


def load_data(input):
    if input.name.endswith('.xls') or input.name.endswith('.xlsx'):
        return pd.read_excel(input, header=0)
    elif input.name.endswith('.tsv'):
        return pd.read_table(input, sep='\t', header=0)
    elif input.name.endswith('.csv'):
        return pd.read_table(input, sep=',', header=0)
    else:
        raise ValueError('Input must be .tsv, .csv, .xls, or .xlsx')


def validate_input(df):
    if not (set(reqd_cols) <= set(df.columns)):
        raise ValueError(
            'Input file must contain the following columns, even if they are '
            'unused/empty: {}'.format(reqd_cols))
    if len(df) > 96:
        raise ValueError('This 96-well plate apparently has more than 96 rows!')
    if df.source_well.isnull().sum() > 0:
        raise ValueError('Empty/null source_wells are not allowed')
    if len(set(df.source_well)) != len(df):
        raise ValueError('Each row must have a unique source_well')
    if len(set(df.source_well) - set(all_wells())) > 0:
        raise ValueError(
            'invalid source_well values: {}'.format(
                set(df.source_well) - set(all_wells())))
    if df.library_id.isnull().sum() > 0:
        raise ValueError('Empty/null library_ids are not allowed')
    if len(set(df.library_id)) < len(df):
        raise ValueError('Each row must have a unique library_id')


def set_seed(df):
    seed(''.join(df['library_id']))


def summarize_output(df, min_volume, max_volume):
    num_libraries = df['library_id'].notnull().sum().tolist()
    num_valid = (df['flag'] == 'valid').sum().tolist()
    num_invalid = (df['flag'] == 'invalid').sum().tolist()
    num_too_dilute = (df['flag'] == 'too_dilute').sum().tolist()
    num_too_concentrated = (df['flag'] == 'too_concentrated').sum().tolist()
    num_empty = (df['flag'] == 'empty').sum().tolist()
    num_weird = (df['flag'] == 'weird').sum().tolist()

    median_transfer_vol = np.median(
        list(df[df['source_plate'] == 'plate_1']['transfer_vol_plate_1_ul']) +
        list(df[df['source_plate'] == 'plate_2']['transfer_vol_plate_2_ul'])).tolist()

    flagged_wells = list(df[df['flag'] != 'valid']['dest_well'])

    summary = {
        'median_transfer_vol': median_transfer_vol,
        'num_libraries': num_libraries,
        'num_valid': num_valid,
        'num_invalid': num_invalid,
        'num_too_dilute': num_too_dilute,
        'num_too_concentrated': num_too_concentrated,
        'num_empty': num_empty,
        'num_weird': num_weird,
        'non_valid_wells': flagged_wells}

    print('median transfer vol ≈ {:.0f} µL\n'.format(median_transfer_vol), file=sys.stderr)
    print('{} libraries in this plate'.format(num_libraries), file=sys.stderr)
    print('{} valid'.format(num_valid), file=sys.stderr)
    print('{} invalid'.format(num_invalid), file=sys.stderr)
    print('{} too_dilute'.format(num_too_dilute), file=sys.stderr)
    print('{} too_concentrated'.format(num_too_concentrated), file=sys.stderr)
    print('{} empty'.format(num_empty), file=sys.stderr)
    print('{} weird'.format(num_weird), file=sys.stderr)
    print()
    print('not valid dest wells: {}'.format(', '.join(flagged_wells)))

    return summary


def draw_plate(df, output_dir):
    from bokeh.plotting import figure, output_file, save, ColumnDataSource as CDS
    from bokeh.palettes import viridis
    from bokeh.models import FuncTickFormatter, HoverTool

    output_file(pjoin(output_dir, 'source-plate-viz.html'))

    df = df.copy(deep=True)

    projects = list(set(df['project']))
    colors = viridis(len(projects))
    df['col'] = df['source_well'].str[1:].astype(int)
    df['row'] = df['source_well'].str[0].apply(lambda x: 'ABCDEFGH'.find(x) + 1)
    df['color'] = df['project'].apply(lambda x: colors[projects.index(x)])

    empty = df['flag'] == 'empty'
    too_dilute = df['flag'] == 'too_dilute'
    too_concentrated = df['flag'] == 'too_concentrated'
    valid = df['flag'] == 'valid'
    weird = ~valid & ~empty & ~too_dilute & ~too_concentrated

    hover = HoverTool(tooltips=[
        ('project', '@project'),
        ('library_id', '@library_id'),
        ('sample_id', '@sample_id'),
        ('flag', '@flag'),
        ('conc. plate 1', '@conc_plate_1_ug_ml µg/mL')])

    p = figure(plot_width=900, plot_height=600, match_aspect=True, y_range=(9, 0), tools=[hover])
    well_size = 50

    p.square('col', 'row', source=CDS(df[empty]), size=well_size)
    p.circle('col', 'row', source=CDS(df[too_concentrated | too_dilute]), size=well_size, fill_color='color', line_color='red', line_width=10)
    p.circle('col', 'row', source=CDS(df[valid]), size=well_size, fill_color='color')
    p.x('col', 'row', source=CDS(df[weird]), size=well_size, fill_color='color')

    p.xaxis.axis_line_color = None
    p.yaxis.axis_line_color = None
    p.grid.visible = False
    p.outline_line_color = None
    p.xaxis.ticker = list(range(1, 13))
    p.yaxis.ticker = list(range(1, 9))
    p.yaxis.formatter = FuncTickFormatter(code='return "ABCDEFGH".charAt(tick - 1)')

    save(p)

10000 ug/mL
10 ug/uL

1:100
100 ug/mL
0.1 ug/uL



@command(context_settings={'help_option_names': ['-h', '--help']})
@option('-i', '--input', type=File('rb'), help="sample_id,well,conc_ug_ml")
@option('-o', '--output-dir', type=Path(exists=False))
@option('-t', '--target-concentration', type=float, default=200,
        help='normalized plate concentration (µg/mL)')
@option('-v', '--transfer-volume', type=float, default=50,
        help='volume of plate to transfer (µL)')
def main(input, output_dir, transfer_mass, min_volume, max_volume, shuffle_wells):
    print(dedent("""
                    **************************************
                    *                                    *
                    *  Concentrations MUST be in µg/mL!  *
                    *                                    *
                    **************************************
                    """),
          file=sys.stderr)

    df = load_data(input)

    validate_input(df)

    # randomize positions if requested
    if shuffle_wells:
        set_seed(df)  # ensures deterministic shuffling
        shuffled_wells = all_wells()
        shuffle(shuffled_wells)
        df['dest_well'] = shuffled_wells[:len(df)]
    else:
        df['dest_well'] = df['source_well']

    # compute transfer amounts (conc. should be µg/mL)
    df['transfer_vol_plate_1_ul'] = transfer_mass / df['conc_plate_1_ug_ml'] * 1000 # µL
    df['transfer_vol_plate_2_ul'] = transfer_mass / df['conc_plate_2_ug_ml'] * 1000 # µL

    # compute transfer plates
    # each plate can, in theory, provide a valid in-range volume...
    p1_valid = (df['transfer_vol_plate_1_ul'] >= min_volume) & (df['transfer_vol_plate_1_ul'] <= max_volume)
    p2_valid = (df['transfer_vol_plate_2_ul'] >= min_volume) & (df['transfer_vol_plate_2_ul'] <= max_volume)
    # ...so we keep track of which value is smaller
    p1_lesser = df['transfer_vol_plate_1_ul'] <= df['transfer_vol_plate_2_ul']

    # set transfer plates
    df['source_plate'] = None
    # for locations where where both vols are valid, pick the smaller
    df.loc[ p1_valid &  p2_valid &  p1_lesser, 'source_plate'] = 'plate_1'
    df.loc[ p1_valid &  p2_valid & ~p1_lesser, 'source_plate'] = 'plate_2'
    # for the rest of the wells, choose whichever has a valid volume
    df.loc[ p1_valid & ~p2_valid             , 'source_plate'] = 'plate_1'
    df.loc[~p1_valid &  p2_valid             , 'source_plate'] = 'plate_2'

    # add flag
    empty = df['transfer_vol_plate_1_ul'].isnull() & df['transfer_vol_plate_2_ul'].isnull()
    valid = p1_valid | p2_valid
    too_dilute =       ~empty & ~valid & ((df['transfer_vol_plate_1_ul'] > max_volume) | (df['transfer_vol_plate_2_ul'] > max_volume))
    too_concentrated = ~empty & ~valid & ((df['transfer_vol_plate_1_ul'] < min_volume) | (df['transfer_vol_plate_2_ul'] < min_volume))
    weird = too_dilute & too_concentrated

    df['flag'] = 'invalid'
    df.loc[empty, 'flag'] = 'empty'
    df.loc[weird, 'flag'] = 'weird'
    df.loc[too_dilute, 'flag'] = 'too_dilute'
    df.loc[too_concentrated, 'flag'] = 'too_concentrated'
    df.loc[valid, 'flag'] = 'valid'

    os.mkdir(output_dir, mode=0o755)

    summary = summarize_output(df, min_volume, max_volume)
    summary['invocation'] = ' '.join(sys.argv)
    with open(pjoin(output_dir, 'summary.yaml'), 'w') as op:
        print(yaml.dump(summary, default_flow_style=False), file=op)

    # write out data for robot protocol
    df.to_csv(pjoin(output_dir, 'plate-normalization.tsv'),
              sep='\t', index=False, float_format='%.3f')

    # write python file with data encoded into it
    with open(pjoin(output_dir, 'execute-normalization.py'), 'w') as op:
        cols = ['flag', 'source_well', 'dest_well', 'source_plate',
                'transfer_vol_plate_1_ul', 'transfer_vol_plate_2_ul']
        buf = StringIO()
        df.to_csv(buf, columns=cols, sep='\t', index=False, float_format='%.3f')
        print(protocol.format(buf.getvalue()), file=op)

    draw_plate(df, output_dir)


if __name__ == '__main__':
    main()
