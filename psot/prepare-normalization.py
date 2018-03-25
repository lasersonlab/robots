#! /usr/bin/env python


"""
Concentrations can be null/empty, in which case they won't be considered
For negative/bead-only controls, leave concentrations empty
Concentrations are assumed to be in µg/mL
"""


import sys
from random import shuffle, seed
from itertools import product
from textwrap import dedent

from click import command, argument, option, File
import numpy as np
import pandas as pd


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
    num_libraries = df['library_id'].notnull().sum()
    num_valid = (df['flag'] == 'valid').sum()
    num_invalid = (df['flag'] == 'invalid').sum()
    num_too_dilute = (df['flag'] == 'too_dilute').sum()
    num_too_concentrated = (df['flag'] == 'too_concentrated').sum()
    num_empty = (df['flag'] == 'empty').sum()
    num_weird = (df['flag'] == 'weird').sum()

    median_transfer_vol = np.median(
        list(df[df['source_plate'] == 'plate_1']['transfer_vol_plate_1_ul']) +
        list(df[df['source_plate'] == 'plate_2']['transfer_vol_plate_2_ul']))

    print('median transfer vol ≈ {:.0f} µL\n'.format(median_transfer_vol), file=sys.stderr)
    print('{} libraries in this plate'.format(num_libraries), file=sys.stderr)
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
@option('--shuffle-wells', is_flag=True,
        help='shuffle wells (deterministically using list of identifiers)')
def main(input, output, transfer_mass, min_volume, max_volume, shuffle_wells):
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

    summarize_output(df, min_volume, max_volume)

    # write out data for robot protocol
    df.to_csv(output, sep='\t', index=False, float_format='%.3f')


if __name__ == '__main__':
    main()
