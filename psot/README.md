# psot: PhIP-seq OpenTrons serum normalization


## Deck arrangement and plate setup

```
A2                               C2                D2
P20 tiprack                      P200 tiprack      waste container
               
               B1                C1                D1 
               source_plate_1    source_plate_2    dest_plate
```

`source_plate_1` is typically a 1:100 dilution of serum, and optional
`source_plate_2` is typically 1:10 dilution of serum.

The source plates are expected to contain at least 120 µL of fluid per well. The
destination plate is expected to contain around 1 mL of fluid per well.


## Compute transfer amounts and optional plate randomization

Input is a tab-delim or Excel file (*single sheet*) with at least the following
columns:

1.  `sample_id` -- the unique identifier for this library (as in `phip_seq_lib`
    Airtable)

2.  `source_well` -- the position for this serum in the source plate (e.g., "D4")

3.  `conc_plate_1_ug_ml` -- the concentration of antibody in the first plate
    (µg/mL) from which the transfer will occur

4.  (*optional*) `conc_plate_2_ug_ml` -- the concentration of antibody in the
    second plate (µg/mL) from which the transfer will occur

Rows for all 96 wells must be represented in the sheet, even if they are unused
(leave them blank).

Two plates at different concentrations increase the chance that the sample will
have a transfer volume compatible with the pipettes on the robot.

Compute the transfer amounts:

```
./prepare-normalization.py -t 2 -m 2 -M 100 example/example-ELISA-input.xlsx example/example-ELISA-output.tsv
```

**Save the resulting file, especially when randomizing!**  Run
`prepare-normalization.py -h` for more information about options.

See the example input and output files in the `example/` directory.
