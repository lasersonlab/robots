from opentrons import containers, instruments
from csv import DictReader


# SET THIS PATH TO TSV FILE BEFORE RUNNING
path = 'example/example-ELISA-output.tsv'


# containers
try:
    tiprack20 = containers.load('tiprack-20ul', 'A2')
except ValueError:
    containers.create('tiprack-20ul', (8, 12), (9, 9), 3.5, 60)
    tiprack20 = containers.load('tiprack-20ul', 'A2')
tiprack200 = containers.load('tiprack-200ul', 'C2')
trash = containers.load('point', 'D2')
source_plate_1 = containers.load('96-flat', 'B1')
source_plate_2 = containers.load('96-flat', 'C1')
try:
    dest_plate = containers.load('96-square-well', 'D1')
except ValueError:
    containers.create('96-square-well', (8, 12), (9, 9), 9, 40)
    dest_plate = containers.load('96-square-well', 'D1')


# pipettes
p200 = instruments.Pipette(axis='a',
                           max_volume=200,
                           min_volume=20,
                           tip_racks=[tiprack200],
                           trash_container=trash)
p20 = instruments.Pipette(axis='b',
                          max_volume=20,
                          min_volume=2,
                          tip_racks=[tiprack20],
                          trash_container=trash)


# load transfers
p20_from = []
p20_to = []
p20_vol = []
p200_from = []
p200_to = []
p200_vol = []
with open(path, 'r') as ip:
    reader = DictReader(ip, dialect='unix', delimiter='\t', strict=True)
    for row in reader:
        if row['flag'] != 'valid':
            continue

        source_well = row['source_well']
        dest_well = row['dest_well']
        if row['source_plate'] == 'plate_1':
            source_plate = source_plate_1
            volume = float(row['transfer_vol_plate_1_ul'])
        elif row['source_plate'] == 'plate_2':
            source_plate = source_plate_2
            volume = float(row['transfer_vol_plate_2_ul'])
        else:
            raise ValueError('strange source_plate: {}'.format(source_plate))

        if volume > 20:
            p200_from.append(source_plate.well(source_well))
            p200_to.append(dest_plate.well(dest_well).bottom(1))
            p200_vol.append(volume)
        else:
            p20_from.append(source_plate.well(source_well))
            p20_to.append(dest_plate.well(dest_well).bottom(1))
            p20_vol.append(volume)


# commands
if len(p20_vol) > 0:
    p20.transfer(p20_vol, p20_from, p20_to, new_tip='always', blow_out=True)
if len(p200_vol) > 0:
    p200.transfer(p200_vol, p200_from, p200_to, new_tip='always', blow_out=True)
