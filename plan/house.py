"""64 Stone Sheep Circle: the house as data.

Everything here is read off the owner's plan set (plan/source/, "Larson House",
sheets A-1 to A-5, 6/11/26). Wall rectangles come straight out of the A-1
vector drawing (plan/tools/extract_walls.py); rooms, doors, windows and
fixtures are placed on those walls by hand and checked against the sheet's
dimension strings. Run this file to rewrite plan/house.json, which every
sheet, both apps and the 3D model read.

Datum: feet, X to the right and Y down the sheet as A-1 is drawn. X = 0 is the
outside face of the garage's left wall (the garage door wall), Y = 0 the
outside face of the master bedroom's rear wall. "Front" is the porch side
(bottom of the sheet), "rear" the patio side (top), "left" the garage doors'
side, "right" the bedroom wing's side, matching the elevation names on A-3/A-4.

Python 3.8+, standard library only.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))

META = {
    'address': '64 Stone Sheep Circle',
    'plan_name': 'Larson House',
    'plan_date': '2026-06-11',
    'sheets': {
        'A-1': 'First floor plan, room sizes and dimensions',
        'A-2': 'Roof plan over the floor plan, pitches and ceiling notes',
        'A-3 (site)': 'Site plan (lot outline, house position, north arrow)',
        'A-3 (elev)': 'Front and rear elevations',
        'A-4': 'Left and right elevations',
        'A-5': 'Floor plan with fixtures, cabinets and appliances',
    },
    'scale': '1/4" = 1\'-0"',
    'stories': 1,
    'ceiling_ft': 9.0,
    'vault': {'rooms': ['kitchen', 'living'], 'pitch': '4:12',
              'note': 'A-2: vaulted ceiling 4:12 over kitchen and living; all other interior ceilings 9\''},
    'patio_vault': {'pitch': '6:12', 'note': 'A-2: 6:12 vaulted patio ceiling'},
    'roof': {
        'main_pitch': '6:12', 'gable_pitch': '8:12', 'porch_pitch': '2:12',
        'material': 'standing-seam metal (dark), per elevations',
        'note': 'Hips and gables per A-2; 8:12 on the front entry gable and the gable over the office/entry, 2:12 shed over the front porch.',
    },
    'siding': 'vertical board-and-batten (tan), stone veneer on the front garage gable, cedar-tone posts and gable bracket at the entry',
    'ext_wall_ft': 0.46,   # 5-1/2": 2x6 as drawn
    'int_wall_ft': 0.293,  # 3-1/2": 2x4 as drawn
    'overall': {'width_ft': 83.44, 'depth_ft': 70.09,
                'note': '83\'-5 1/4" across the front, 78\'-0 3/4" across the rear, 70\'-1 1/16" deep at the garage, 62\'-2 15/16" at the bedroom wing to the porch edge'},
}

# Interior faces of each room, as a polygon (or a rectangle x0, y0, x1, y1).
# 'label' is the size printed on A-1 and 'label_sf' its area, kept so the
# apps can show what the plan says next to what the walls measure.
ROOMS = [
    dict(id='master_bed', name='Master Bed', rect=(16.46, 0.46, 30.54, 17.54), label="14' x 17'", label_sf=258, kind='bed'),
    dict(id='master_bath', name='Master Bath', rect=(5.833, 5.54, 16.167, 24.167), label="10'-3\" x 18'-7\"", label_sf=189, kind='bath'),
    dict(id='master_closet', name='Master Closet', rect=(5.833, 24.46, 16.08, 33.84), label="10'-2\" x 9'-4\"", label_sf=107, kind='closet'),
    dict(id='master_hall', name='Master Hall', rect=(25.04, 17.833, 30.54, 21.833), label=None, label_sf=None, kind='hall'),
    dict(id='laundry', name='Laundry', rect=(16.46, 17.833, 24.747, 29.967), label="8'-4\" x 12'-1\"", label_sf=100, kind='laundry'),
    dict(id='powder', name='Powder', rect=(25.04, 22.127, 30.54, 27.647), label="5'-5\" x 5'-5\"", label_sf=34, kind='bath'),
    dict(id='mud', name='Mud Room', poly=[(16.373, 30.26), (25.04, 30.26), (25.04, 27.933), (30.54, 27.933), (30.54, 42.213),
                                          (25.44, 42.213), (25.44, 36.84), (16.373, 36.84)], label="14'-1\" x 6'-6\"", label_sf=145, kind='hall'),
    dict(id='dining', name='Dining', rect=(30.833, 5.54, 43.707, 16.12), label="12'-10\" x 10'-7\"", label_sf=147, kind='living'),
    dict(id='kitchen', name='Kitchen', rect=(30.833, 16.12, 43.707, 44.9), label="13' x 28'-9\"", label_sf=376, kind='kitchen'),
    dict(id='pantry', name='Pantry', rect=(34.207, 45.187, 43.707, 53.273), label="9'-5\" x 8'", label_sf=81, kind='closet'),
    dict(id='mechanical', name='Mechanical', rect=(30.833, 45.187, 33.913, 53.273), label="3' x 8'", label_sf=30, kind='mech'),
    dict(id='living', name='Living', rect=(43.707, 16.847, 64.167, 42.48), label="17'-4\" x 25'-7\"", label_sf=512, kind='living'),
    dict(id='entry', name='Entry', rect=(44.0, 42.48, 51.08, 53.273), label="7' x 10'-7\"", label_sf=80, kind='hall'),
    dict(id='coat', name='Coat Closet', rect=(41.707, 42.773, 43.707, 45.773), label=None, label_sf=None, kind='closet'),
    dict(id='office', name='Office', rect=(51.373, 42.773, 64.167, 53.273), label="12'-9\" x 10'-5\"", label_sf=143, kind='bed'),
    dict(id='hall', name='Bedroom Hall', rect=(64.46, 18.94, 68.54, 39.98), label=None, label_sf=None, kind='hall'),
    dict(id='bed1', name='Bedroom 1', rect=(64.46, 5.54, 77.58, 18.94), label="13'-1\" x 13'-4\"", label_sf=189, kind='bed'),
    dict(id='bed1_closet', name='Bedroom 1 Closet', rect=(68.833, 19.233, 77.58, 21.233), label=None, label_sf=None, kind='closet'),
    dict(id='bath1', name='Bath 1', rect=(77.873, 5.54, 82.98, 15.833), label="5' x 6'-11\"", label_sf=42, kind='bath'),
    dict(id='bed2_closet', name='Closet (Bedroom 2)', rect=(77.873, 16.127, 82.98, 21.233), label="5' x 5'", label_sf=31, kind='closet'),
    dict(id='bed2', name='Bedroom 2', rect=(68.833, 21.52, 82.98, 34.107), label="14'-1\" x 12'-6\"", label_sf=190, kind='bed'),
    dict(id='bath2', name='Bath 2', rect=(68.833, 34.4, 82.98, 39.98), label="14'-1\" x 5'-6\"", label_sf=87, kind='bath'),
    dict(id='bed3', name='Bedroom 3', rect=(64.46, 40.273, 77.46, 53.273), label="12'-11\" x 12'-11\"", label_sf=181, kind='bed'),
    dict(id='bed3_closet', name='Closet (Bedroom 3)', rect=(77.747, 40.273, 82.98, 45.273), label="5'-2\" x 4'-11\"", label_sf=33, kind='closet'),
    dict(id='garage', name='Garage', poly=[(0.46, 37.133), (5.833, 37.133), (5.833, 34.133), (16.08, 34.133), (16.08, 37.133),
                                           (25.147, 37.133), (25.147, 42.507), (30.54, 42.507), (30.54, 69.633), (15.413, 69.633),
                                           (15.413, 67.133), (0.46, 67.133)], label="30' x 32'-11\"", label_sf=978, kind='garage'),
    dict(id='patio', name='Covered Patio', rect=(44.167, 0.0, 64.0, 16.387), label=None, label_sf=None, kind='outdoor'),
    dict(id='porch', name='Front Porch', rect=(31.0, 53.733, 77.913, 62.24), label=None, label_sf=None, kind='outdoor'),
]

# Exterior windows: gaps in the A-1 exterior walls. Sizes on the elevations
# (A-3, A-4) aren't dimensioned; heights and sills below are scaled off them
# and are the open items the window supplier confirms.
W25 = dict(w=2.5, h=5.0, head=8.0)    # the 2'-6" units: tall, divided-lite on the front
W40 = dict(w=4.0, h=4.0, head=8.0)    # the 4'-0" units on the front porch wall
WINDOWS = [
    dict(id='W1', room='master_bed', wall='rear', x=(17.507, 20.007), y=0.0, **W25),
    dict(id='W2', room='master_bed', wall='rear', x=(27.0, 29.5), y=0.0, **W25),
    dict(id='W3', room='master_bath', wall='rear', x=(8.747, 13.247), y=5.08, w=4.5, h=3.0, head=8.0),
    dict(id='W4', room='dining', wall='rear', x=(32.1, 34.6), y=5.08, **W25),
    dict(id='W5', room='dining', wall='rear', x=(35.94, 38.44), y=5.08, **W25),
    dict(id='W6', room='dining', wall='rear', x=(39.747, 42.247), y=5.08, **W25),
    dict(id='W7', room='dining', wall='patio', x=43.707, y=(6.633, 9.133), **W25),
    dict(id='W8', room='dining', wall='patio', x=43.707, y=(11.62, 14.12), **W25),
    dict(id='W9', room='living', wall='patio', x=(46.173, 48.673), y=16.387, **W25),
    dict(id='W10', room='living', wall='patio', x=(59.32, 61.82), y=16.387, **W25),
    dict(id='W11', room='bed1', wall='rear', x=(65.96, 68.46), y=5.08, **W25),
    dict(id='W12', room='bed1', wall='rear', x=(73.58, 76.08), y=5.08, **W25),
    dict(id='W13', room='bed2', wall='right', x=82.98, y=(22.813, 25.313), **W25),
    dict(id='W14', room='bed2', wall='right', x=82.98, y=(30.313, 32.813), **W25),
    dict(id='W15', room='pantry', wall='front', x=(34.827, 38.827), y=53.273, **W40),
    dict(id='W16', room='office', wall='front', x=(56.813, 60.813), y=53.273, **W40),
    dict(id='W17', room='bed3', wall='front', x=(69.413, 73.413), y=53.273, **W40),
    dict(id='W18', room='garage', wall='front', x=(9.293, 11.793), y=67.133, **W25),
    dict(id='W19', room='garage', wall='front', x=(18.7, 21.2), y=69.633, **W25),
    dict(id='W20', room='garage', wall='front', x=(24.753, 27.253), y=69.633, **W25),
]

# Doors and cased openings. 'at' is the wall line, 'span' the opening along
# it. Swings are from the A-1 door arcs. 'into' is the room the leaf swings
# into. Interior heights are not on the plans: 8'-0" is assumed to match the
# exterior doors on the elevations (open item).
DOORS = [
    dict(id='D1', kind='entry', name='Front entry', between=('entry', 'porch'), axis='y', at=53.273, span=(45.793, 49.293), w=3.0, h=8.0, into='entry', ext=True),
    dict(id='D2', kind='french', name='Patio French doors', between=('living', 'patio'), axis='y', at=16.387, span=(51.033, 56.967), w=6.0, h=8.0, into='living', ext=True, leaves=2),
    dict(id='D3', kind='exterior', name='Garage service door', between=('garage', 'outside'), axis='y', at=36.673, span=(1.307, 4.433), w=3.0, h=6.667, into='garage', ext=True),
    dict(id='D4', kind='overhead', name='Garage door 1', between=('garage', 'outside'), axis='x', at=0.0, span=(41.073, 50.193), w=9.0, h=8.0, ext=True),
    dict(id='D5', kind='overhead', name='Garage door 2', between=('garage', 'outside'), axis='x', at=0.0, span=(54.073, 63.193), w=9.0, h=8.0, ext=True),
    dict(id='D6', kind='fire', name='Garage to mud room', between=('garage', 'mud'), axis='y', at=42.213, span=(26.427, 29.553), w=3.0, h=8.0, into='mud'),
    dict(id='D7', kind='double', name='Mechanical (from garage)', between=('garage', 'mechanical'), axis='x', at=30.54, span=(46.627, 51.753), w=5.0, h=8.0, into='garage', leaves=2),
    dict(id='D8', kind='swing', name='Master bedroom', between=('master_hall', 'master_bed'), axis='y', at=17.54, span=(26.38, 29.5), w=3.0, h=8.0, into='master_bed'),
    dict(id='D9', kind='opening', name='Master bed to bath', between=('master_bed', 'master_bath'), axis='x', at=16.167, span=(14.0, 17.12), w=3.0, h=8.0),
    dict(id='D10', kind='opening', name='Master bath to closet', between=('master_bath', 'master_closet'), axis='y', at=24.167, span=(11.647, 14.273), w=2.5, h=8.0),
    dict(id='D11', kind='pocket', name='Master closet to laundry', between=('master_closet', 'laundry'), axis='x', at=16.08, span=(25.307, 27.933), w=2.5, h=8.0),
    dict(id='D12', kind='swing', name='Laundry', between=('mud', 'laundry'), axis='y', at=29.967, span=(19.167, 21.96), w=2.667, h=8.0, into='laundry'),
    dict(id='D13', kind='swing', name='Powder', between=('mud', 'powder'), axis='y', at=27.647, span=(25.733, 28.36), w=2.5, h=8.0, into='powder'),
    dict(id='D14', kind='opening', name='Pantry', between=('kitchen', 'pantry'), axis='y', at=44.9, span=(38.5, 41.127), w=2.5, h=8.0),
    dict(id='D15', kind='swing', name='Coat closet', between=('entry', 'coat'), axis='x', at=43.707, span=(43.213, 45.333), w=2.0, h=8.0, into='entry'),
    dict(id='D16', kind='french', name='Office French doors', between=('entry', 'office'), axis='x', at=51.08, span=(45.46, 50.587), w=5.0, h=8.0, into='office', leaves=2),
    dict(id='D17', kind='swing', name='Bedroom 1', between=('hall', 'bed1'), axis='y', at=18.94, span=(64.94, 68.06), w=3.0, h=8.0, into='bed1'),
    dict(id='D18', kind='bypass', name='Bedroom 1 closet', between=('bed1', 'bed1_closet'), axis='y', at=18.94, span=(70.127, 76.247), w=6.0, h=8.0),
    dict(id='D19', kind='swing', name='Bath 1', between=('bed1', 'bath1'), axis='x', at=77.58, span=(6.027, 8.647), w=2.5, h=8.0, into='bath1'),
    dict(id='D20', kind='swing', name='Bedroom 2 closet', between=('bed2', 'bed2_closet'), axis='y', at=21.233, span=(79.113, 81.74), w=2.5, h=8.0, into='bed2'),
    dict(id='D21', kind='swing', name='Bedroom 2', between=('hall', 'bed2'), axis='x', at=68.54, span=(30.94, 33.567), w=2.5, h=8.0, into='bed2'),
    dict(id='D22', kind='swing', name='Bath 2', between=('hall', 'bath2'), axis='x', at=68.54, span=(34.773, 37.4), w=2.5, h=8.0, into='bath2'),
    dict(id='D23', kind='swing', name='Bedroom 3', between=('hall', 'bed3'), axis='y', at=39.98, span=(65.1, 67.887), w=2.667, h=8.0, into='bed3'),
    dict(id='D24', kind='swing', name='Bedroom 3 closet', between=('bed3', 'bed3_closet'), axis='x', at=77.46, span=(41.46, 44.087), w=2.5, h=8.0, into='bed3'),
    dict(id='D25', kind='glass', name='Master shower glass door', between=('master_bath', 'master_bath'), axis='x', at=9.833, span=(19.9, 21.4), w=1.5, h=7.0),
    dict(id='O1', kind='opening', name='Kitchen to master hall', between=('kitchen', 'master_hall'), axis='x', at=30.54, span=(18.127, 21.54), w=3.4, h=8.0),
    dict(id='O2', kind='opening', name='Kitchen to mud room', between=('kitchen', 'mud'), axis='x', at=30.54, span=(38.193, 41.82), w=3.6, h=8.0),
    dict(id='O3', kind='opening', name='Living to bedroom hall', between=('living', 'hall'), axis='x', at=64.167, span=(19.733, 23.36), w=3.6, h=8.0),
]

# Fixtures and appliances from A-5 (tags as printed there). Positions are the
# fixture's center; sizes its footprint. K-9135 and K-9136 are the drain tags
# A-5 puts in the showers and the garage and mechanical floors.
FIXTURES = [
    dict(id='MB-WC', room='master_bath', kind='wc', name='ADA toilet', at=(7.05, 7.5), size=(2.35, 1.66)),
    dict(id='MB-TUB', room='master_bath', kind='tub', name='Pedestal tub (faucet)', at=(7.5, 13.8), size=(2.6, 5.66)),
    dict(id='MB-LAV1', room='master_bath', kind='lav', name='Vanity sink 1', at=(15.08, 7.6), size=(2.08, 1.8)),
    dict(id='MB-LAV2', room='master_bath', kind='lav', name='Vanity sink 2', at=(15.08, 11.6), size=(2.08, 1.8)),
    dict(id='MB-VAN', room='master_bath', kind='cabinet', name='Double vanity, 8\'', at=(15.08, 9.63), size=(2.08, 8.09)),
    dict(id='MB-SHR', room='master_bath', kind='shower', name='Shower 4\' x 6\' (glass door)', at=(7.83, 21.17), size=(4.0, 6.0)),
    dict(id='MB-FD', room='master_bath', kind='drain', name='Shower drain K-9136', at=(7.91, 21.08), size=(0.54, 0.55)),
    dict(id='B1-LAV', room='bath1', kind='lav', name='Vanity sink', at=(81.89, 7.13), size=(2.08, 3.09)),
    dict(id='B1-WC', room='bath1', kind='wc', name='ADA toilet', at=(81.76, 10.05), size=(2.34, 1.67)),
    dict(id='B1-SHR', room='bath1', kind='shower', name='Shower 5\' x 3\'-4"', at=(80.43, 14.15), size=(5.1, 3.37)),
    dict(id='B1-FD', room='bath1', kind='drain', name='Shower drain K-9135', at=(80.5, 14.02), size=(0.55, 0.54)),
    dict(id='PR-WC', room='powder', kind='wc', name='ADA toilet', at=(29.33, 23.59), size=(2.35, 1.67)),
    dict(id='PR-LAV', room='powder', kind='lav', name='Lavatory (not drawn on A-5; assumed)', at=(26.0, 25.0), size=(1.5, 1.6)),
    dict(id='LA-WASH', room='laundry', kind='washer', name='Washer (curved front loading)', at=(23.6, 23.3), size=(2.25, 2.5)),
    dict(id='LA-DRY', room='laundry', kind='dryer', name='Dryer (curved)', at=(23.6, 20.6), size=(2.25, 2.5)),
    dict(id='LA-CAB', room='laundry', kind='cabinet', name='Laundry cabinets / counter', at=(17.5, 23.9), size=(2.0, 12.0)),
    dict(id='K-RANGE', room='kitchen', kind='range', name='48" range BS655Z-48 (GEM-FPF tag)', at=(32.0, 29.6), size=(2.3, 4.0)),
    dict(id='K-BASE', room='kitchen', kind='cabinet', name='Wall cabinets and counter, left wall', at=(32.02, 30.49), size=(2.3, 14.93)),
    dict(id='K-ISL', room='kitchen', kind='island', name='Island 4\'-5" x 11\'-11"', at=(38.68, 30.6), size=(4.38, 11.92)),
    dict(id='K-SINK', room='kitchen', kind='sink', name='Kitchen sink (island)', at=(38.68, 27.6), size=(2.0, 3.0)),
    dict(id='K-DW', room='kitchen', kind='dw', name='Dishwasher (island)', at=(38.68, 25.6), size=(2.0, 2.0)),
    dict(id='K-REF', room='kitchen', kind='ref', name='Refrigerator, 35" (R35")', at=(37.9, 43.4), size=(2.92, 2.6)),
    dict(id='K-BACK', room='kitchen', kind='cabinet', name='Counter, front wall', at=(34.6, 43.4), size=(3.73, 2.89)),
    dict(id='LV-FP', room='living', kind='fireplace', name='Wood fireplace insert, curved', at=(61.69, 29.59), size=(1.85, 3.55)),
    dict(id='B2-LAV1', room='bath2', kind='lav', name='Vanity sink 1', at=(71.3, 38.98), size=(1.8, 1.92)),
    dict(id='B2-LAV2', room='bath2', kind='lav', name='Vanity sink 2', at=(74.4, 38.98), size=(1.8, 1.92)),
    dict(id='B2-VAN', room='bath2', kind='cabinet', name='Double vanity, 8\'', at=(72.87, 38.98), size=(8.0, 1.92)),
    dict(id='B2-WC', room='bath2', kind='wc', name='ADA toilet', at=(78.5, 38.77), size=(1.66, 2.35)),
    dict(id='B2-TUB', room='bath2', kind='tub', name='Standard tub 1 [66W]', at=(81.57, 37.19), size=(2.73, 5.5)),
    dict(id='ME-FD', room='mechanical', kind='drain', name='Floor drain K-9136', at=(32.02, 49.23), size=(0.54, 0.54)),
    dict(id='GA-FD', room='garage', kind='drain', name='Floor drain K-9136', at=(14.96, 52.14), size=(0.54, 0.55)),
]

# Outside faces of the heated house (the thermal envelope, with the walls to
# the garage on the house side) and of the garage, for gross areas, the slab
# and the energy model.
ENVELOPE = [(16.0, 0.0), (31.0, 0.0), (31.0, 5.08), (44.167, 5.08), (44.167, 16.387), (64.0, 16.387), (64.0, 5.08),
            (83.44, 5.08), (83.44, 45.733), (77.913, 45.733), (77.913, 53.733), (30.54, 53.733), (30.54, 42.507),
            (25.147, 42.507), (25.147, 37.133), (16.08, 37.133), (16.08, 34.133), (5.373, 34.133), (5.373, 5.08), (16.0, 5.08)]
GARAGE_OUTLINE = [(0.0, 36.673), (5.373, 36.673), (5.373, 34.133), (16.08, 34.133), (16.08, 37.133), (25.147, 37.133),
                  (25.147, 42.507), (30.54, 42.507), (30.54, 53.733), (31.0, 53.733), (31.0, 70.093), (14.96, 70.093),
                  (14.96, 67.593), (0.0, 67.593)]

# Roof posts at the patio corners and along the porch (A-1).
POSTS = [(43.79, 0.21), (64.21, 0.21), (43.79, 4.86), (64.21, 4.86),
         (31.25, 62.04), (42.54, 62.04), (52.54, 62.04), (65.13, 62.04), (77.71, 62.04)]

# Wall rectangles from the A-1 drawing: kind (E exterior, I interior), x0, y0, x1, y1.
WALLS = [
    ('E', 16.0, 0.0, 16.46, 5.54),
    ('E', 16.46, 0.0, 17.507, 0.46),
    ('E', 20.007, 0.0, 27.0, 0.46),
    ('E', 29.5, 0.0, 30.54, 0.46),
    ('E', 30.54, 0.0, 31.0, 5.54),
    ('E', 5.373, 5.08, 5.833, 37.133),
    ('E', 5.833, 5.08, 8.747, 5.54),
    ('E', 13.247, 5.08, 16.0, 5.54),
    ('E', 31.0, 5.08, 32.1, 5.54),
    ('E', 34.6, 5.08, 35.94, 5.54),
    ('E', 38.44, 5.08, 39.747, 5.54),
    ('E', 42.247, 5.08, 44.167, 5.54),
    ('E', 64.0, 5.08, 65.96, 5.54),
    ('E', 68.46, 5.08, 73.58, 5.54),
    ('E', 76.08, 5.08, 82.98, 5.54),
    ('E', 82.98, 5.08, 83.44, 22.813),
    ('I', 16.167, 5.54, 16.46, 14.0),
    ('I', 30.54, 5.54, 30.833, 18.127),
    ('E', 43.707, 5.54, 44.167, 6.633),
    ('E', 64.0, 5.54, 64.46, 16.847),
    ('I', 77.58, 5.54, 77.873, 6.027),
    ('I', 77.58, 8.647, 77.873, 21.233),
    ('E', 43.707, 9.133, 44.167, 11.62),
    ('I', 5.833, 9.54, 8.5, 9.833),
    ('E', 43.707, 14.12, 44.167, 16.847),
    ('I', 77.873, 15.833, 82.98, 16.127),
    ('E', 44.167, 16.387, 46.173, 16.847),
    ('E', 48.673, 16.387, 51.033, 16.847),
    ('E', 56.967, 16.387, 59.32, 16.847),
    ('E', 61.82, 16.387, 64.0, 16.847),
    ('I', 64.167, 16.847, 64.46, 19.733),
    ('I', 16.167, 17.12, 16.46, 17.833),
    ('I', 16.46, 17.54, 26.38, 17.833),
    ('I', 29.5, 17.54, 30.54, 17.833),
    ('I', 17.833, 17.833, 18.127, 21.98),
    ('I', 24.747, 17.833, 25.04, 21.98),
    ('I', 5.833, 17.873, 9.833, 18.167),
    ('I', 64.46, 18.94, 64.94, 19.233),
    ('I', 68.06, 18.94, 68.687, 19.233),
    ('I', 68.687, 18.94, 70.127, 19.233),
    ('I', 76.247, 18.94, 77.58, 19.233),
    ('I', 68.54, 19.233, 68.833, 30.94),
    ('I', 68.833, 21.233, 79.113, 21.52),
    ('I', 81.74, 21.233, 82.98, 21.52),
    ('I', 30.54, 21.54, 30.833, 38.193),
    ('I', 25.04, 21.833, 30.54, 22.127),
    ('I', 16.08, 21.98, 18.127, 22.267),
    ('I', 24.747, 21.98, 25.04, 30.26),
    ('I', 16.08, 22.267, 16.373, 25.307),
    ('I', 64.167, 23.36, 64.46, 53.273),
    ('I', 5.833, 24.167, 11.647, 24.46),
    ('I', 14.273, 24.167, 16.08, 24.46),
    ('E', 82.98, 25.313, 83.44, 30.313),
    ('I', 25.04, 27.647, 25.733, 27.933),
    ('I', 28.36, 27.647, 30.54, 27.933),
    ('I', 16.08, 27.933, 16.373, 36.84),
    ('I', 16.373, 29.967, 19.167, 30.26),
    ('I', 21.96, 29.967, 24.747, 30.26),
    ('E', 82.98, 32.813, 83.44, 45.733),
    ('I', 68.54, 33.567, 68.833, 34.773),
    ('I', 5.833, 33.84, 16.08, 34.133),
    ('I', 68.833, 34.107, 82.98, 34.4),
    ('E', 0.0, 36.673, 0.46, 41.073),
    ('E', 0.46, 36.673, 1.307, 37.133),
    ('E', 4.433, 36.673, 5.373, 37.133),
    ('I', 16.08, 36.84, 25.147, 37.133),
    ('I', 25.147, 36.84, 25.44, 42.507),
    ('I', 68.54, 37.4, 68.833, 39.98),
    ('I', 64.46, 39.98, 65.1, 40.273),
    ('I', 67.887, 39.98, 82.98, 40.273),
    ('I', 77.46, 40.273, 77.747, 41.46),
    ('I', 30.54, 41.82, 30.833, 46.627),
    ('I', 25.44, 42.213, 26.427, 42.507),
    ('I', 29.553, 42.213, 30.54, 42.507),
    ('I', 41.413, 42.48, 41.707, 46.067),
    ('I', 41.707, 42.48, 43.707, 42.773),
    ('I', 43.707, 42.48, 44.0, 43.213),
    ('I', 51.08, 42.48, 51.373, 45.46),
    ('I', 51.373, 42.48, 64.167, 42.773),
    ('I', 77.46, 44.087, 77.747, 45.273),
    ('I', 30.833, 44.9, 38.5, 45.187),
    ('I', 41.127, 44.9, 41.413, 45.187),
    ('I', 33.913, 45.187, 34.207, 53.273),
    ('E', 77.46, 45.273, 82.98, 45.733),
    ('I', 43.707, 45.333, 44.0, 53.273),
    ('E', 77.46, 45.733, 77.913, 53.733),
    ('I', 41.707, 45.773, 43.707, 46.067),
    ('E', 0.0, 50.193, 0.46, 54.073),
    ('I', 51.08, 50.587, 51.373, 53.273),
    ('I', 30.54, 51.753, 30.833, 53.733),
    ('E', 30.833, 53.273, 34.827, 53.733),
    ('E', 38.827, 53.273, 45.793, 53.733),
    ('E', 49.293, 53.273, 56.813, 53.733),
    ('E', 60.813, 53.273, 69.413, 53.733),
    ('E', 73.413, 53.273, 77.46, 53.733),
    ('E', 30.54, 53.733, 31.0, 70.093),
    ('E', 0.0, 63.193, 0.46, 67.593),
    ('E', 0.46, 67.133, 9.293, 67.593),
    ('E', 11.793, 67.133, 14.96, 67.593),
    ('E', 14.96, 67.133, 15.413, 70.093),
    ('E', 15.413, 69.633, 18.7, 70.093),
    ('E', 21.2, 69.633, 24.753, 70.093),
    ('E', 27.253, 69.633, 30.54, 70.093),
]


def shoelace(p):
    return abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))) / 2


def area(room):
    if 'rect' in room:
        x0, y0, x1, y1 = room['rect']
        return (x1 - x0) * (y1 - y0)
    p = room['poly']
    return abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))) / 2


def poly(room):
    if 'poly' in room:
        return [list(p) for p in room['poly']]
    x0, y0, x1, y1 = room['rect']
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def build():
    rooms = []
    for r in ROOMS:
        rooms.append({k: v for k, v in r.items() if k not in ('rect', 'poly')} | {'poly': poly(r), 'area_sf': round(area(r), 1)})
    windows = []
    for w in WINDOWS:
        w = dict(w)
        w['axis'] = 'y' if isinstance(w['x'], tuple) else 'x'   # the wall line the window sits on
        if w['axis'] == 'y':
            w['at'], w['span'] = w.pop('y'), list(w.pop('x'))
        else:
            w['at'], w['span'] = w.pop('x'), list(w.pop('y'))
        w['sill'] = round(w['head'] - w['h'], 3)
        windows.append(w)
    heated = [r for r in rooms if r['kind'] not in ('garage', 'outdoor')]
    out = {
        'meta': META,
        'rooms': rooms,
        'windows': windows,
        'doors': [dict(d, span=list(d['span']), between=list(d['between'])) for d in DOORS],
        'fixtures': [dict(f, at=list(f['at']), size=list(f['size'])) for f in FIXTURES],
        'posts': [list(p) for p in POSTS],
        'envelope': [list(p) for p in ENVELOPE],
        'garage_outline': [list(p) for p in GARAGE_OUTLINE],
        'walls': [{'kind': k, 'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1} for k, x0, y0, x1, y1 in WALLS],
        'totals': {
            'heated_gross_sf': round(shoelace(ENVELOPE)),
            'garage_gross_sf': round(shoelace(GARAGE_OUTLINE)),
            'conditioned_room_sf': round(sum(r['area_sf'] for r in heated)),
            'garage_sf': round(next(r['area_sf'] for r in rooms if r['id'] == 'garage')),
            'patio_sf': round(next(r['area_sf'] for r in rooms if r['id'] == 'patio')),
            'porch_sf': round(next(r['area_sf'] for r in rooms if r['id'] == 'porch')),
        },
    }
    return out


def check(h):
    """Every door and window must sit in a gap of a wall line, every fixture inside its room."""
    problems = []
    rooms = {r['id']: r for r in h['rooms']}
    for f in h['fixtures']:
        xs = [p[0] for p in rooms[f['room']]['poly']]; ys = [p[1] for p in rooms[f['room']]['poly']]
        if not (min(xs) - 0.05 <= f['at'][0] <= max(xs) + 0.05 and min(ys) - 0.05 <= f['at'][1] <= max(ys) + 0.05):
            problems.append(f"fixture {f['id']} outside {f['room']}")
    for o in h['windows'] + [d for d in h['doors'] if d['kind'] != 'glass']:
        a, (s0, s1) = o['at'], o['span']
        for w in h['walls']:
            # a wall crossing the opening's middle on its own line means the opening is blocked
            if o['axis'] == 'y' and w['y0'] - 0.05 <= a <= w['y1'] + 0.05 and w['x0'] < (s0 + s1) / 2 < w['x1'] and (w['x1'] - w['x0']) > (w['y1'] - w['y0']):
                problems.append(f"{o['id']} blocked by wall {w}")
            if o['axis'] == 'x' and w['x0'] - 0.05 <= a <= w['x1'] + 0.05 and w['y0'] < (s0 + s1) / 2 < w['y1'] and (w['y1'] - w['y0']) > (w['x1'] - w['x0']):
                problems.append(f"{o['id']} blocked by wall {w}")
    return problems


if __name__ == '__main__':
    h = build()
    probs = check(h)
    for p in probs:
        print('CHECK:', p)
    with open(os.path.join(HERE, 'house.json'), 'w') as f:
        json.dump(h, f, indent=1)
    t = h['totals']
    print(f"house.json: {len(h['rooms'])} rooms, {len(h['windows'])} windows, {len(h['doors'])} doors, {len(h['fixtures'])} fixtures, {len(h['walls'])} walls")
    print(f"heated gross {t['heated_gross_sf']} sf, garage gross {t['garage_gross_sf']} sf")
    print(f"conditioned rooms {t['conditioned_room_sf']} sf, garage {t['garage_sf']} sf, patio {t['patio_sf']} sf, porch {t['porch_sf']} sf")
