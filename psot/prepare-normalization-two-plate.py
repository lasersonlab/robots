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
    assert len(df) == 96
    assert set(df.source_well) == set(all_wells)


def check_manual(df, min_volume, max_volume):
    num_samples = df['sample_id'].notnull().sum()
    invalid = df['sample_id'].notnull() & df['source_plate'].isin(['manual', 'too_dilute', 'too_concentrated'])
    too_dilute = df['source_plate'] == 'too_dilute'
    too_concentrated = df['source_plate'] == 'too_concentrated'

    print('{} total samples'.format(num_samples), file=sys.stderr)
    print('{} samples are invalid'.format(invalid.sum()), file=sys.stderr)
    print('{} samples are too dilute'.format(too_dilute.sum()), file=sys.stderr)
    print('{} samples are too concentrated'.format(too_concentrated.sum()), file=sys.stderr)

    dilution_factors = [2, 3, 5, 10, 20, 50, 100, 200, 500, 1000, 5000, 10000,
                        100000, 1000000]
    for factor in dilution_factors:
        dil_vols = df.loc[invalid, 'vol_plate1'] * factor
        num_recovered = ((dil_vols >= min_volume) & (dil_vols <= max_volume)).sum()
        if num_recovered > 0:
            print(
                "Another {}x dilution of plate1 may recover {} add'l samples".format(
                    factor, num_recovered),
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
    print('Concentrations MUST be in µg/mL!\n', file=sys.stderr)

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
    # some wells are simply empty/unused (which are also invalid in p1 and p2)
    empty = df['vol_plate1'].isnull()
    df['source_plate'] = ''
    # for locations where where both vols are valid, pick the smaller
    df.loc[ p1_valid &  p2_valid &  p1_lesser, 'source_plate'] = 'plate1'
    df.loc[ p1_valid &  p2_valid & ~p1_lesser, 'source_plate'] = 'plate2'
    # for the rest of the wells, choose whichever has a valid volume
    df.loc[ p1_valid & ~p2_valid             , 'source_plate'] = 'plate1'
    df.loc[~p1_valid &  p2_valid             , 'source_plate'] = 'plate2'
    # neither plate has a valid volume
    df.loc[~p1_valid & ~p2_valid             , 'source_plate'] = 'manual'
    # and some of them are invalid bc they were empty/null
    df.loc[empty                             , 'source_plate'] = 'empty'
    too_dilute =       (df['vol_plate1'] > max_volume) & ((df['vol_plate1'].isnull()) | (df['vol_plate2'] > max_volume))
    too_concentrated = (df['vol_plate1'] < min_volume) & ((df['vol_plate1'].isnull()) | (df['vol_plate2'] < min_volume))
    df.loc[too_dilute, 'source_plate'] = 'too_dilute'
    df.loc[too_concentrated, 'source_plate'] = 'too_concentrated'


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
