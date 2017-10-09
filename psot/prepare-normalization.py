#! /usr/bin/env python


"""
Concentrations can be null/empty, in which case they won't be considered
For negative/bead-only controls, leave concentrations empty
Concentrations are assumed to be in µg/mL
"""


import sys
from random import shuffle
from itertools import product

from click import command, argument, option, File
import pandas as pd
import numpy as np


all_wells = ['{}{}'.format(r, c) for r, c in product('ABCDEFGH', range(1, 13))]


def validate_input(df):
    assert set(['sample_id', 'source_well', 'conc_plate1', 'conc_plate2']) <= set(df.columns)
    assert '' not in set(df.sample_id)
    assert len(df) <= 96
    assert set(df.source_well) <= set(all_wells)


def check_manual(df, min_volume, max_volume):
    invalid = df['source_plate'] == 'manual'
    for i, row in df[invalid].iterrows():
        print(
            'MANUAL: {} requires excessively large or small transfer'.format(row['sample_id']),
            file=sys.stderr)
    dilution_factors = [2, 3, 5, 10, 20, 50, 100, 200, 500, 1000]
    for factor in dilution_factors:
        dil_vols = df.loc[invalid, 'vol_plate1'] / factor
        num_recovered = ((dil_vols >= min_volume) & (dil_vols <= max_volume)).sum()
        print(
            "Another {}x dilution may recover {} add'l samples".format(factor, num_recovered),
            file=sys.stderr)


@command(context_settings={'help_option_names': ['-h', '--help']})
@argument('input', type=File('rb'))
@argument('output', type=File('w'))
@option('-t', '--transfer-mass', type=float, default=2,
        help='mass to transfer (µg)')
@option('-m', '--min-volume', type=float, default=2,
        help='minimum transfer volume (µL)')
@option('-M', '--max-volume', type=float, default=10,
        help='maximum transfer volume (µL)')
def main(input, output, transfer_mass, min_volume, max_volume):
    if input.name.endswith('.xls') or input.name.endswith('.xlsx'):
        df = pd.read_excel(input, header=0)
    elif input.name.endswith('.tsv'):
        df = pd.read_table(input, sep='\t', header=0)
    else:
        raise ValueError('Input must be .tsv, .xls, or .xlsx')

    validate_input(df)

    # randomize positions
    shuffle(all_wells)
    df['norm_well'] = all_wells[:len(df)]

    # compute transfer amounts (conc. should be µg/mL)
    df['vol_plate1'] = transfer_mass / df['conc_plate1'] * 1000 # µL
    df['vol_plate2'] = transfer_mass / df['conc_plate2'] * 1000 # µL

    # compute which plate to use for each well
    # each plate can, in theory, provide a valid in-range volume...
    p1_valid = (df['vol_plate1'] >= min_volume) & (df['vol_plate1'] <= max_volume)
    p2_valid = (df['vol_plate2'] >= min_volume) & (df['vol_plate2'] <= max_volume)
    # ...so we keep track of which value is smaller
    p1_lesser = df['vol_plate1'] <= df['vol_plate2']
    df['source_plate'] = ''
    # for locations where where both vols are valid, pick the smaller
    df.loc[ p1_valid &  p2_valid &  p1_lesser, 'source_plate'] = 'plate1'
    df.loc[ p1_valid &  p2_valid & ~p1_lesser, 'source_plate'] = 'plate2'
    # for the rest of the wells, choose whichever has a valid volume
    df.loc[ p1_valid & ~p2_valid             , 'source_plate'] = 'plate1'
    df.loc[~p1_valid &  p2_valid             , 'source_plate'] = 'plate2'
    # neither plate has a valid volume
    df.loc[~p1_valid & ~p2_valid             , 'source_plate'] = 'manual'

    # define transfer volume from specified plate
    p1_rows = df.source_plate == 'plate1'
    p2_rows = df.source_plate == 'plate2'
    df.loc[p1_rows, 'transfer_vol'] = df.loc[p1_rows, 'vol_plate1']
    df.loc[p2_rows, 'transfer_vol'] = df.loc[p2_rows, 'vol_plate2']

    check_manual(df, min_volume, max_volume)

    # write out data for robot protocol
    df.to_csv(output, sep='\t', index=False)


if __name__ == '__main__':
    main()
