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
import numpy as np
import pandas as pd


all_wells = ['{}{}'.format(r, c) for r, c in product('ABCDEFGH', range(1, 13))]
reqd_cols = [
    'sample_id', 'source_well', 'conc_plate_1_ug_ml', 'conc_plate_2_ug_ml']


def validate_input(df):
    if not (set(reqd_cols) <= set(df.columns)):
        raise ValueError(
            'Input file must contain columns: sample_id, source_well, '
            'conc_plate_1_ug_ml, conc_plate_2_ug_ml, even if they are empty')
    if (len(df) != 96) or (set(df.source_well) != set(all_wells)):
        raise ValueError(
            'Input file must contain all 96 rows representing a plate')


def check_output(df, min_volume, max_volume):
    num_samples = df['sample_id'].notnull().sum()
    num_valid = (df['flag'] == 'valid').sum()
    num_invalid = (df['flag'] == 'invalid').sum()
    num_too_dilute = (df['flag'] == 'too_dilute').sum()
    num_too_concentrated = (df['flag'] == 'too_concentrated').sum()
    num_empty = (df['flag'] == 'empty').sum()
    num_weird = (df['flag'] == 'weird').sum()

    median_transfer_vol = np.median(
        list(df[df['source_plate'] == 'plate_1']['transfer_vol_plate_1_ul']) +
        list(df[df['source_plate'] == 'plate_2']['transfer_vol_plate_2_ul']))

    print('median transfer vol = {:.0f} µL'.format(median_transfer_vol), file=sys.stderr)
    print('{} samples (incl some empties)'.format(num_samples), file=sys.stderr)
    print('{} valid'.format(num_valid), file=sys.stderr)
    print('{} invalid'.format(num_invalid), file=sys.stderr)
    print('{} too_dilute'.format(num_too_dilute), file=sys.stderr)
    print('{} too_concentrated'.format(num_too_concentrated), file=sys.stderr)
    print('{} empty'.format(num_empty), file=sys.stderr)
    print('{} weird'.format(num_weird), file=sys.stderr)


@command(context_settings={'help_option_names': ['-h', '--help']})
@argument('input', type=File('rb'))
@argument('output', type=File('w'))
@option('-t', '--transfer-mass', type=float, default=2,
        help='mass to transfer (µg)')
@option('-m', '--min-volume', type=float, default=2,
        help='minimum transfer volume (µL)')
@option('-M', '--max-volume', type=float, default=100,
        help='maximum transfer volume (µL)')
@option('--shuffle-wells', is_flag=True, help='shuffle wells')
def main(input, output, transfer_mass, min_volume, max_volume, shuffle_wells):
    print('Concentrations MUST be in µg/mL!\n', file=sys.stderr)

    if input.name.endswith('.xls') or input.name.endswith('.xlsx'):
        df = pd.read_excel(input, header=0)
    elif input.name.endswith('.tsv'):
        df = pd.read_table(input, sep='\t', header=0)
    else:
        raise ValueError('Input must be .tsv, .xls, or .xlsx')

    validate_input(df)

    # randomize positions if requested
    wells = list(df['source_well'])
    if shuffle_wells:
        shuffle(wells)
    df['dest_well'] = wells

    # compute transfer amounts (conc. should be µg/mL)
    df['transfer_vol_plate_1_ul'] = transfer_mass / df['conc_plate_1_ug_ml'] * 1000 # µL
    df['transfer_vol_plate_2_ul'] = transfer_mass / df['conc_plate_2_ug_ml'] * 1000 # µL

    # compute transfer plates
    # each plate can, in theory, provide a valid in-range volume...
    p1_valid = (df['transfer_vol_plate_1_ul'] >= min_volume) & (df['transfer_vol_plate_1_ul'] <= max_volume)
    p2_valid = (df['transfer_vol_plate_2_ul'] >= min_volume) & (df['transfer_vol_plate_2_ul'] <= max_volume)
    # ...so we keep track of which value is smaller
    p1_lesser = df['transfer_vol_plate_1_ul'] <= df['transfer_vol_plate_2_ul']

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

    check_output(df, min_volume, max_volume)

    # write out data for robot protocol
    df.to_csv(output, sep='\t', index=False, float_format='%.3f')


if __name__ == '__main__':
    main()
