# psot: PhIP-seq OpenTrons serum normalization


## Deck arrangement and plate setup

```
A2                               C2                D2
P20 tiprack                      P200 tiprack      waste container
               
               B1                C1                D1 
               source_plate_1    source_plate_2    dest_plate
```

NOTE: the Rainin tip boxes are not symmetric. They have notches in the sides
that interface with the covers. Ensure that the short distance-to-notch is
closer to you, while the longer distance to notch is towards the back of the
robot.

`source_plate_1` is typically a 1:100 dilution of serum, and `source_plate_2` is
an additional optional plate to allow for another dilution (typically 1:10
dilution of serum).

The source plates are expected to contain at least 120 µL of fluid per well (but
really, this is determined by the max possible volume transfer that is defined,
typically 100 µL). The destination plate is expected to contain around 100 µL
fluid per well (which will be raised to 1 mL for the immune-complex formation).
The P200 pipette is installed on Axis A and the P20 pipette on Axis B.


## Compute transfer amounts and optional plate randomization

Input is a tab-delim or Excel file (*single sheet*) with at least the following
columns:

1.  `library_id` -- the unique identifier for this library (as in `phip_seq_lib`
    Airtable)

2.  `source_well` -- the position for this serum in the source plate (e.g., "D4")

3.  `conc_plate_1_ug_ml` -- the concentration of antibody in the first plate
    (µg/mL) from which the transfer will occur

4.  (*optional*) `conc_plate_2_ug_ml` -- the concentration of antibody in the
    second plate (µg/mL) from which the transfer will occur

Two plates at different concentrations increase the chance that the sample will
have a transfer volume compatible with the pipettes on the robot.

Compute the transfer amounts:

```
./prepare-normalization.py -t 2 -m 2 -M 100 example/example-ELISA-input.xlsx example/example-ELISA-output.tsv
```

**Save the resulting file, especially when randomizing!**  Run
`prepare-normalization.py -h` for more information about options.

See the example input and output files in the `example/` directory.

