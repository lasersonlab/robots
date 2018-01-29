# PhIP-seq serum normalization



## Compute transfer amounts and plate randomization

Input is a tab-delim file with the following columns:

1.  `sample_id` -- the unique identifier for this library (as in `phip_seq_lib`
    Airtable)

2.  `source_well` -- the position for this serum in the source plate

3.  `source_conc_ug_ml` -- the concentration of antibody in the 1:100 dilution plate
    (µg/mL) from which the transfer will occur


```
./prepare-normalization.py -t 2 -m 2 -M 200 example/example-ELISA-input.xlsx example/example-ELISA-output.tsv

```
