from opentrons import containers, instruments


# SET THIS PATH BEFORE RUNNING
path = '/Users/laserson/tmp/tmp-norm.tsv'


# containers
tiprack = containers.load('tiprack-10ul', 'A1')
trash = containers.load('point', 'D2')
source_plate1 = containers.load('96-flat', 'B1')
source_plate2 = containers.load('96-flat', 'C1')
norm = containers.load('96-deep-well', 'D1')


# load transfers
plate1_from = []
plate1_to = []
plate1_vol = []

plate2_from = []
plate2_to = []
plate2_vol = []

with open(path, 'r') as ip:
    header = next(ip)
    assert header.startswith('sample_id')

    for line in ip:
        fields = line.split('\t')

        plate = fields[7]
        if plate == 'manual':
            continue

        source_well = fields[1]
        dest_well = fields[4]
        volume = float(fields[8])

        if plate == 'plate1':
            plate1_from.append(source_plate1.well(source_well))
            plate1_to.append(norm.well(dest_well).bottom(1))
            plate1_vol.append(volume)
        elif plate == 'plate2':
            plate2_from.append(source_plate2.well(source_well))
            plate2_to.append(norm.well(dest_well).bottom(1))
            plate2_vol.append(volume)
        else:
            raise ValueError('unrecognized plate name: {}'.format(plate))


# pipettes
p20 = instruments.Pipette(axis='b',
                          max_volume=20,
                          min_volume=1,
                          tip_racks=[tiprack],
                          trash_container=trash)


# commands
if len(plate1_vol) > 0:
    p20.transfer(plate1_vol, plate1_from, plate1_to, new_tip='always')
if len(plate2_vol) > 0:
    p20.transfer(plate2_vol, plate2_from, plate2_to, new_tip='always')
