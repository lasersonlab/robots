from opentrons import labware, instruments

from csv import DictReader
from io import StringIO


data = StringIO("""{}""")


# labware
tiprack50 = labware.load("opentrons-tiprack-300ul", "7")
tiprack300 = labware.load("opentrons-tiprack-300ul", "8")
source_plate = labware.load("96-flat", "4")
dest_plate = labware.load("96-deep-well", "5")


# pipettes
p50 = instruments.P50_Single(mount="left", tip_racks=[tiprack50])
p300 = instruments.P300_Single(mount="right", tip_racks=[tiprack300])


# transfers
reader = DictReader(data, dialect="unix", delimiter="\t", strict=True)
for row in reader:
    if row["norm_flag"] != "valid":
        continue

    source_well = row["source_well"]
    dest_well = row["dest_well"]
    volume = float(row["transfer_vol_ul"])

    pipette = p50 if volume <= 50 else p300
    pipette.transfer(
        volume,
        source_plate.wells(source_well),
        dest_plate.wells(dest_well),
        new_tip="always",
        blow_out=True,
    )
