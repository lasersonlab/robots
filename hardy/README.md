# `hardy` opentrons OT-2 protocols

## `phip-norm`: normalization and shuffling of sera for PhIP-seq

Our usual setup is a 96-well plate with serum diluted 1:100. One column of 8
wells is typically left empty, which will be negative beads-only controls.
Another column of wells is typically filled with the same set of 8 control sera
across experiments. This leaves 80 wells for experimental samples. We typically
transfer 2 µg of IgG into the destination 96-deep well plate where the complex
formation will occur.

`source_plate`: expected to contain at least 120 µL of fluid per well (but
really, this is determined by the max possible volume transfer that is defined,
typically 100 µL).

`dest_plate`: expected to contain around 100 µL fluid per well (which will be
raised to 1 mL for the immune-complex formation).

### Deck arrangement and plate setup

```
10              11              TRASH


7               8               9
tiprack50       tiprack300

4               5               6
source_plate    dest_plate


1               2               3
```

Well A1 is to the upper-left.

### Input data

Need a CSV/TSV/Excel file with at least the following columns:

1. `library_id`: library identifier (should be Illumina-friendly)
2. `sample_id`:  serum sample identifier
3. `source_well`: position of sample in the source plate
4. `conc_ug_ml`: concentration of the sample (µg/mL)

### Usage

```
$ hardy phip-norm -h

**************************************
*                                    *
*  Concentrations MUST be in µg/mL!  *
*                                    *
**************************************

Usage: cli.py phip-norm [OPTIONS]

  Normalize and shuffle serum samples for PhIP-seq

  See README.md for detailed instructions.

Options:
  -i, --input FILENAME       min cols:
                             library_id,sample_id,source_well,conc_ug_ml
                             [required]
  -o, --output-dir PATH      [required]
  -b, --barcodes FILENAME    min cols: plate_well,bc_read  [required]
  -t, --transfer-mass FLOAT  mass to transfer (µg)
  -m, --min-volume FLOAT     minimum transfer volume (µL)
  -M, --max-volume FLOAT     maximum transfer volume (µL)
  --shuffle-wells            shuffle wells (deterministically)
  -h, --help                 Show this message and exit.
```





# DELETE ME:
# from click.utils import open_file
# input_path = '/Users/laserson/tmp/phip-example-plate.xlsx'
# transfer_mass = 2
# min_volume = 3
# max_volume = 100
# shuffle_wells = True
# ip = open_file(input_path, 'rb')
# df = load_data(ip)
# validate_data(df)
# df = compute_normalization(df, transfer_mass, min_volume, max_volume, shuffle_wells)
# summary = summarize_output(df)
# draw_plate(df, "")
