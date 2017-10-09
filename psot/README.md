# PhIP-seq serum normalization



## Compute transfer amounts and plate randomization

Input is a tab-delim file with the following columns:

1.  `sample_id` -- the unique identifier for this library (as in `phip_seq_lib`
    Airtable)

2.  `source_well` -- the position for this serum in the source plate

3.  `10k_conc` -- the concentration of antibody in the 1:10000 dilution plate
    (µg/mL)

4.  `100k_conc` -- the concentration of antibody in the 1:100000 dilution plate
    (µg/mL)

