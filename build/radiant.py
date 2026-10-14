"""R-1 Radiant: PEX loops on 3" nub boards under the slab, manifolds, zones and flows.

The house heats from its slab: 1/2" PEX laid on EPS25 Super 4 nub boards (4' x 4', 4" of EPS R-18 under a 1"
grid of pucks that hold the tube on a 3" grid), with 4" of concrete over the pucks. Every tube run sits on that 3"
grid, so the whole layout is a walk over a lattice of nodes 3" apart (build/nubgrid.py): a node holds one tube and
nothing can cross. Fields are tube pairs snaking together 6" apart (supply and return side by side, nested bends),
so both ends of a loop sit together at one edge of the panel; from there the leaders are routed node by node to a
manifold port, hugging walls, through doorways and under walls where a gate allows it. Loops stay under 200' with
their leaders. Room loads are M-1's (hvac.room_load); the garage gets its own loops at 6" held at 50°F.

Zoning is by manifold: every manifold is wholly on one zone, each zone has its own circulator in the mechanical closet
started by its thermostat, and the loops balance on their flow meters; there are no actuators (owner, 2026-10-14).
"""
import math
from setlib import HOUSE, ROOMS, S, Sheet, px, py
from climate import CLIMATE
import hvac
import plumbing
from nubgrid import P, CLR, Grid, Panel, band_loops, band_path, pair_open, pair_route, verify, corners_ft, node, ft, plen_nodes

MAX_LOOP = 200.0          # ft of 1/2" PEX per loop, leaders included (owner, 2026-10-13)
DT = 10.0                 # design temperature drop per loop, °F
DOWN = 0.07               # share of each loop's heat lost down and out the slab edge, over R-18 boards
R_SLAB = {6: 0.25}        # water to slab surface, h·sf·°F/Btu, 1/2" PEX 6" o.c. in a 4" slab
R_COVER = 0.20            # hard-surface flooring assumed (tile, LVP, engineered wood); carpet is ~1.5
R_SURF = 0.50             # slab surface to room (2.0 Btu/h·sf·°F)
GARAGE_F = 50.0
RISE = 2.0                # ft of leader per end, slab up into the manifold
GARAGE_COLOR = '#2e7d32'
BOARD = dict(name='EPS25 Super 4 nub board', size=4.0, sf=16.0, thick_in=5.0, eps_in=4.0, puck_in=1.0, r=18.0, pitch_in=3.0, per_bundle=5, min_bundles=3,
             url='https://pexuniverse.com/eps25-super-4-foam-insulation')
SLAB_H = -0.39            # tube centre: on the EPS between the pucks, 4-1/2" below the slab top (feet from the slab top)
FEED_H = -0.85            # 1" feed pairs in the base course under the boards
BOARD_Z = (-0.75, -0.333) # the board itself: 5" from the base course to the top of the pucks (4" slab above)

ZONES = {
    'Z1': dict(name='Garage (held at 50°F)', color=GARAGE_COLOR, stat='T1', where='Garage, wall by the mud room door', garage=True,
               rooms=['garage', 'mechanical']),
    'Z2': dict(name='Great room', color='#e65100', stat='T2', where='Kitchen side of the living room, on the entry wall, away from the fireplace and the patio glass',
               rooms=['kitchen', 'dining', 'pantry', 'living', 'entry', 'coat']),
    'Z3': dict(name='Master suite and utility', color='#c62828', stat='T3', where='Master bed, interior wall by the hall door',
               rooms=['master_bed', 'master_bath', 'master_closet', 'master_hall', 'laundry', 'powder', 'mud']),
    'Z4': dict(name='Bedroom wing and office', color='#1565c0', stat='T4', where='Bedroom hall, south end',
               rooms=['bed1', 'bed1_closet', 'bath1', 'bed2', 'bed2_closet', 'bath2', 'bed3', 'bed3_closet', 'hall', 'office']),
}
GZ = 'Z1'                  # the garage zone, mixed down and held at 50°F
ZONE_OF = {r: z for z, v in ZONES.items() for r in v['rooms']}
STATS = {'T1': (24.2, 40.2), 'T2': (46.0, 41.6), 'T3': (27.6, 16.6), 'T4': (66.5, 39.2)}

# Heat source and the manifold stations. A station hangs on a wall face ('face' is that coordinate along 'axis'; 'side' is
# the room side of it); its loop ends rise out of the slab in one row of 3" ports on the first grid line in front of the
# face, between 'lo' and 'hi' along the wall. 'riser' is where the 1" feed pair comes up to it.
HS = (33.55, 48.8)         # wall-hung on the mechanical closet's east wall (P-1's water manifold and heater share the closet)
T_SUP = 110.0              # design supply cap, °F: keeps a condensing boiler condensing
STATIONS = {
    'MF-1': dict(room='laundry', axis='y', face=18.0, side=+1, lo=18.5, hi=24.25, mount=(4.0, 5.6), riser=(24.4, 18.4), zone='Z3',
                 where='Laundry, on the north wall from the linen alcove to the east wall, over the dryer',
                 detail='Surface-mounted manifold cabinet on the laundry\'s north wall, 4\' up so the dryer slides under its east end. That wall is the staggered-stud sound wall to the master bed, so the cabinet is not recessed. The master bed, bath and closet loops come under that wall straight up into it; the laundry, mud room, powder and master hall loops come up the laundry side. Zone 3\'s 1" pair rises at its east end.'),
    'MF-2': dict(room='mechanical', axis='x', face=33.913, side=-1, lo=45.5, hi=48.25, mount=(0.8, 2.3), riser=None, zone='Z2',
                 where='Mechanical closet, low on the east wall under HS-1',
                 detail='Surface-mounted cabinet low on the mechanical closet\'s east wall, under the boiler, piped straight to zone 2\'s circulator P-R2; every loop end comes under that wall from the pantry. The water heater keeps the south end of the wall.'),
    'MF-3': dict(room='hall', axis='x', face=64.46, side=+1, recessed=True, lo=24.0, hi=27.75, mount=(2.5, 4.1), riser=(64.9, 28.9), zone='Z2',
                 where='Bedroom hall, west wall north of the fireplace',
                 detail='Recessed manifold cabinet in the hall\'s west wall between the living room opening and the fireplace chase, as S-1 frames it. Zone 2\'s second manifold, on the same circulator as MF-2: the living room and entry loops come under that wall straight into it. A 2x4 wall takes a 3-1/2" deep cabinet; fur it to 2x6 locally if the chosen manifold needs more (S-1).'),
    'MF-4': dict(room='hall', axis='x', face=64.46, side=+1, recessed=True, lo=32.0, hi=37.25, mount=(2.5, 4.1), riser=(64.9, 37.4), zone='Z4',
                 where='Bedroom hall, west wall south of the fireplace',
                 detail='Recessed cabinet in the hall\'s west wall south of the fireplace chase, across from the bath 2 door, 2\'-0" longer than S-1 framed it (the recess now runs from 32\'-0" to 37\'-3"). The bedroom and bath loops come down the hall into it from both ends; the office loops come under that wall from the living room side.'),
    'MF-G': dict(room='garage', axis='y', face=37.133, side=+1, lo=16.5, hi=24.75, mount=(4.0, 5.6), riser=(19.4, 37.6), zone='Z1',
                 where='Garage, on the mud room wall (two 7-loop manifolds side by side)',
                 detail='Surface-mounted cabinets on the garage face of the mud room wall, 4\' above the slab, 8\' from the mechanical closet door; zone 1\'s circulator P-R1 and its mixing valve are in the closet and its 1" pair comes under the garage floor and up that wall. Surface mounting keeps the garage fire separation whole.'),
}
# tube passes under these stretches of wall (x0, y0, x1, y1 is the wall itself; 'into' names the room on the far side).
# Under a wall a tube only goes straight across; the gates in front of a manifold match its port row, so each tube
# comes up into its own port.
GATES = [
    (18.5, 17.54, 23.25, 18.0, 'laundry'),        # G1 master bed into the laundry, straight into MF-1
    (33.913, 45.5, 34.207, 48.25, 'mechanical'),  # G2 pantry into the mechanical closet, straight into MF-2
    (34.5, 44.9, 38.25, 45.187, 'pantry'),        # G4 kitchen into the pantry, west of the pantry opening, on the way to MF-2
    (64.167, 24.0, 64.46, 27.75, 'hall'),         # G8 living into the hall, into MF-3
    (64.167, 32.0, 64.46, 37.25, 'hall'),         # G5 living into the hall, into MF-4 (the office loops)
    (25.5, 21.833, 30.25, 22.127, 'powder'),       # G6 master hall into the powder room
    (78.25, 15.83, 80.5, 16.13, 'bath1'),         # G7 bedroom 2 closet into bath 1, under the shower floor
]
# The tube is 4-1/2" down in the slab, so it runs under everything that sits on the floor: cabinets, the island, tubs,
# showers, vanities, toilets, the washer and dryer, the hearth (owner, 2026-10-14). Only the walls (and their plates), the
# posts and the manifold port rows keep it out. Where a drain or a closet flange comes up through the slab the installer
# shifts that one run over a channel for the length of the fitting (note on the sheet).
NO_TUBE = []
DRAINS = []
PENETRATIONS = ([f for f in HOUSE['fixtures'] if f['kind'] in ('drain', 'wc', 'tub')]      # where P-1 comes up through the slab inside a field
                + [dict(id=st['id'], kind='stack', name=f"{st['name']} vent stack", at=st['at']) for st in plumbing.STACKS])
# Panels: room, rectangle in plan feet, the edge the loop ends sit on ('W', 'E', 'N', 'S'; 'r' starts the bands from the
# other end of that edge), the manifold, and how many 6" rows a band (one loop) may take (0 = whatever 200' allows).
# Rectangles stay 6" off the walls where tube would be near a plate, clear of the cabinets, tubs, vanities, the island,
# the fridge and the hearth, and leave lanes beside the entry edge for the leaders of their own bands and of the loops
# that pass by (those lanes are heated by the leaders).
PANELS = {
    # zone 3, master suite and utility: MF-1
    'MB':  ('master_bed', 16.76, 0.76, 30.24, 15.5, 'Sr', 'MF-1', 0),     # three bands; the rows south of it carry the bath leaders east to the gate
    'BAM': ('master_bath', 6.13, 11.25, 14.75, 17.25, 'Er', 'MF-1', 0),   # the bath between the toilet partition and the shower, vanity and tub included; ends at the bedroom door
    'BAN': ('master_bath', 8.75, 6.25, 15.87, 11.1, 'Sr', 'MF-1', 0),     # north end by the vanity, running on into the toilet nook (BAW); its leaders go down the vanity wall to the door
    'BAW': ('master_bath', 6.13, 5.84, 8.5, 9.0, 'E', 'MF-1', 0),         # the toilet nook, tail of BAN
    'MCN': ('master_closet', 6.75, 25.25, 15.0, 28.0, 'E', 'MF-1', 0),   # closet, north half, running on through the bath door into the shower end of the bath (BAS)
    'BAS': ('master_bath', 6.13, 19.0, 15.87, 23.0, 'Sr', 'MF-1', 0),     # shower end of the bath, tail of MCN
    'LA':  ('laundry', 20.25, 19.0, 23.1, 27.75, 'N', 'MF-1', 0),         # laundry under the washer and dryer, straight up into the ports, running on through the pocket door into the closet's south half (MCS); the rows south of it carry the mud room leaders to the strip under the dryer
    'MCS': ('master_closet', 6.13, 28.25, 15.25, 33.54, 'E', 'MF-1', 0),  # closet, south half, tail of LA
    'MUW': ('mud', 17.25, 31.75, 24.75, 36.6, 'W', 'MF-1', 0),            # mud room west of the garage door, wall to wall below the rows that carry its own and MUEN's leaders to the laundry door; runs on round the leg's west wall into the south half of the east leg (MUES); its leaders go north through the laundry door and up the strip under the dryer
    'PW':  ('powder', 27.5, 22.5, 30.24, 27.25, 'S', 'MF-1', 0),         # the powder room's east 3', under the toilet; fed through its door from the east leg (MUEN), runs on under the hall wall into the master hall (the lav side stays bare: a middle panel of a chain can only be 6 or 10 runs wide)
    'MH':  ('master_hall', 25.34, 18.25, 30.3, 21.5, 'Sr', 'MF-1', 0),     # the master hall wall to wall, last panel of MUEN's loop, fed under the powder room wall
    'MUEN': ('mud', 26.25, 29.5, 30.0, 35.6, 'Wr', 'MF-1', 0),           # mud room east leg, north half by the powder door: its leads and its open ends both sit at the lane along the leg's west wall; the ends run on through the powder door (PW), the leaders go up the lane, round the laundry wall and through the laundry door
    'MUES': ('mud', 26.25, 36.0, 30.0, 41.9, 'Wr', 'MF-1', 0),           # mud room east leg, south half to the garage door; tail of MUW, fed down the same lane
    # zone 2, great room: MF-2 in the closet takes the kitchen and dining as long strips from the pantry wall to the rear wall;
    # MF-3 on the hall wall takes the living room and the entry
    'KD':  ('kitchen', 31.25, 6.0, 39.1, 43.5, 'S', 'MF-2', 0),           # dining and kitchen from the rear wall to the pantry wall, under the island, sink, range and cabinets; four bands of four runs, their ends at the pantry wall, under it into the pantry
    'KD4': ('kitchen', 39.25, 6.0, 41.0, 41.5, 'S', 'MF-2', 0),          # the fifth strip, beside the pantry opening; its leaders go through the opening, so it stops 2' short of the wall to leave the pantry loop's connector a way past
    'PA':  ('pantry', 34.75, 47.75, 42.75, 52.5, 'W', 'MF-2', 0),         # the pantry beyond the leader fan, wall to wall under the shelves; its leads sit at the closet wall and go straight under it into the last two ports; runs on round its east end, back along the coat closet's wall and through the pantry opening into the kitchen's east strip (KE)
    'KE':  ('kitchen', 41.75, 6.0, 42.75, 41.25, 'S', 'MF-2', 0),         # the two runs where the kitchen and dining open to the living room, short of the coat closet; tail of PA
    'LV':  ('living', 42.75, 17.25, 60.5, 40.25, 'E', 'MF-3', 0),          # the living room from the kitchen opening to the lane along the hall wall, under the hearth, down to the rows along the office wall that carry the office and entry leaders; bands' ends at the lane, which carries them to the gate
    'EN':  ('entry', 44.5, 43.25, 49.75, 52.75, 'N', 'MF-3', 0),          # the entry west of the office leaders' lane; its leaders run east along the office wall and up the lane into MF-3
    # zone 4, bedroom wing and office: MF-4
    'B1':  ('bed1', 65.0, 5.9, 77.3, 17.1, 'Sr', 'MF-4', 0),              # bedroom 1 wall to wall in three bands; their leaders stack in the rows along the hall wall, out the door and down the hall
    'C2':  ('bed2_closet', 79.5, 17.0, 82.3, 20.9, 'S', 'MF-4', 0),       # one loop with bath 1: out through the closet door, west along bedroom 2's rear wall and down the hall
    'BT1': ('bath1', 78.5, 5.9, 82.3, 15.3, 'S', 'MF-4', 0),              # the tail of that loop: all of bath 1, under the vanity, toilet and shower
    'B2':  ('bed2', 70.25, 22.6, 82.9, 33.3, 'Wr', 'MF-4', 0),            # bedroom 2 in two bands; the lane under its hall wall carries the closet loop and the north band to the door
    'BT2': ('bath2', 69.25, 34.75, 82.9, 39.7, 'W', 'MF-4', 0),           # bath 2 wall to wall, under the vanity, toilet and tub; out the door straight into MF-4
    'B3':  ('bed3', 65.5, 41.25, 72.1, 52.85, 'N', 'MF-4', 0),             # bedroom 3, west part, straight out the door and up the hall
    'B3E': ('bed3', 72.5, 41.25, 76.1, 52.85, 'N', 'MF-4', 0),             # bedroom 3, east part; runs on round the foot of the room into the closet (B3C)
    'B3C': ('bed3_closet', 78.5, 41.4, 82.75, 44.75, 'W', 'MF-4', 0),     # bedroom 3 closet, tail of B3E
    'OFN': ('office', 52.25, 43.25, 63.75, 48.5, 'Wr', 'MF-4', 0),        # the office, living room side; its leads sit in the French doors' span, out through them, along the office wall and up the lane, under the hall wall into MF-4
    'OFS': ('office', 52.25, 48.75, 63.75, 52.97, 'W', 'MF-4', 0),        # the office, front side, leads likewise in the doors' span
    # garage, 6" like the house (owner, 2026-10-13): MF-G
    # garage west half in six bands, 4 columns wide at the west end where the leaders are longest, 6 toward the ports; the
    # leaders fan east along the north wall into the ports, the first two straight up out of their own columns, so those
    # two bands reach further north and the next two start a little lower, which brings all six out near the same length
    'GW0': ('garage', 1.0, 38.5, 2.6, 66.6, 'N', 'MF-G', 0),
    'GW1': ('garage', 3.0, 39.0, 4.6, 66.6, 'N', 'MF-G', 0),
    'GW2': ('garage', 5.0, 42.5, 7.6, 66.6, 'N', 'MF-G', 0),
    'GW3': ('garage', 8.0, 42.0, 10.6, 66.6, 'N', 'MF-G', 0),
    'GW4': ('garage', 11.0, 41.5, 13.6, 66.6, 'N', 'MF-G', 0),
    'GW5': ('garage', 14.0, 41.5, 16.6, 66.6, 'N', 'MF-G', 0),
    'GS':  ('garage', 17.0, 41.5, 19.6, 66.6, 'Nr', 'MF-G', 0),           # the strip under the west ports, straight up into them
    'GM1': ('garage', 20.0, 38.0, 22.6, 66.6, 'N', 'MF-G', 0),            # under the middle ports, straight up into them
    'GE0': ('garage', 24.5, 43.0, 30.1, 51.6, 'W', 'MF-G', 0),           # 18 rows            # east of the mud room, north part; runs on through the mechanical door into the mechanical closet (MECH)
    'MECH': ('mechanical', 31.5, 46.75, 33.25, 52.9, 'W', 'MF-G', 0),     # the mechanical closet, tail of GE0, west of MF-2's port column
    'GE1': ('garage', 24.5, 52.0, 30.1, 62.6, 'W', 'MF-G', 0),            # south-east, middle rows; leaders up the lane east of GM1
    'GE2': ('garage', 24.5, 63.0, 30.1, 68.6, 'W', 'MF-G', 0),            # south-east corner at the garage door wall; leaders up the same lane; runs on west along the door wall (GSS)
    'GSS': ('garage', 15.75, 67.0, 22.6, 68.6, 'Er', 'MF-G', 0),          # the strip along the garage door wall under GS and GM1, tail of GE2
}
# loops that run on through more panels (open pairs through all but the last, routed pair connectors between, closed pair in the last)
# chain heads whose far edge is a wall: their open pair ends beside their own leads at the entry edge instead
OPEN_AT_ENTRY = {'GE2', 'B3E', 'MUEN'}
CHAINS = [('C2', 'BT1'), ('BAN', 'BAW'), ('MCN', 'BAS'), ('LA', 'MCS'), ('MUW', 'MUES'), ('MUEN', 'PW', 'MH'), ('PA', 'KE'), ('B3E', 'B3C'), ('GE0', 'MECH'), ('GE2', 'GSS')]
# where the bands of one panel go to different stations
BAND_STATION = {}
# bands set by hand (6" rows per loop, from the first row)
BANDS = {'MB': [8, 8, 10], 'B1': [8, 8, 8], 'B2': [10, 10], 'LV': [8, 8, 8, 8, 8, 6], 'KD': [4, 4, 4, 4], 'KD4': [4], 'GW0': [4], 'GW1': [4], 'GW2': [6], 'GW3': [6], 'GW4': [6], 'GW5': [6], 'GS': [6], 'GM1': [6], 'GE0': [18], 'GE1': [22], 'GE2': [12]}
# the order the leaders are routed in: the loop routed first takes the lane along the wall, the next hugs it, so the
# bundles nest. At a port row fed from one side, the loop nearest that end goes first; where bands leave a panel past
# each other toward a gate, the far band goes first and turns off before the near one passes it; where every band
# leaves through the same door, the near band goes first and the far one comes round the outside.
# An entry is a panel, or 'panel.band' for one band of it.
ORDER = ['BAM', 'BAN', 'MCN', 'LA', 'MB', 'MUW', 'MUEN',
         'KD.0', 'KD.1', 'KD.2', 'KD.3', 'KD4', 'PA',
         'OFN', 'OFS', 'EN', 'LV.5', 'LV.4', 'LV.3', 'LV.0', 'LV.1', 'LV.2',
         'B1.2', 'B1.1', 'B1.0', 'C2', 'B2.1', 'B2.0', 'BT2', 'B3', 'B3E',
         'GW0', 'GW1', 'GW2', 'GW3', 'GW4', 'GW5', 'GS', 'GM1', 'GE0', 'GE1', 'GE2']
NEAR_FIRST = set()
# floor a loop's leaders keep off (x0, y0, x1, y1 in feet), so the pair routed first takes the inside of a bundle and
# the ones after it wrap round the outside
KEEP_OUT = {
    # the lane beside GM1 carries three pairs: GE0's next to its field, GE1's in the middle, GE2's by GM1
    'GE0': [(22.7, 38.0, 23.8, 42.9)], 'GE1': [(22.7, 38.0, 23.3, 62.9)],
    # the mud room's west loop takes the west side of the laundry door so the east leg's loop can pass it on the east side
    'MUW': [(20.75, 29.25, 22.25, 31.75)],
    # bedroom 1's west band takes the west side of its door and the inside of the hall so the other two come round outside it
    'B1.2': [(66.5, 18.25, 68.5, 22.0)],
    # the living room and entry loops reach MF-3 under the wall, never through the hall
    'LV': [(65.0, 18.5, 68.5, 31.5)], 'EN': [(65.0, 18.5, 68.5, 31.5)], 'OFN': [(65.0, 18.5, 68.5, 39.5)], 'OFS': [(65.0, 18.5, 68.5, 39.5)]}
# a loop held to one pair of ports: the coordinate along the port row of its first port (the next one is its second)
PORT = {'BAM': 18.5, 'BAN': 19.0, 'LA': 20.5, 'MUW': 23.5, 'MUEN': 24.0,
        'KD.0': 45.5, 'KD.1': 46.0, 'KD.2': 46.5, 'KD.3': 47.0, 'KD4': 47.5, 'PA': 48.0,
        'EN': 27.5,
        'B1.2': 32.0, 'B1.1': 32.5, 'B1.0': 33.0, 'C2': 33.5, 'B2.1': 34.0, 'B2.0': 34.5, 'BT2': 35.0, 'B3E': 35.5, 'B3': 36.0, 'OFS': 36.5, 'OFN': 37.0,
        'GW0': 16.5, 'GW1': 17.0, 'GW2': 17.5, 'GW3': 18.0, 'GW4': 18.5, 'GW5': 19.0, 'GS': 19.5, 'GM1': 20.0, 'GE2': 22.75, 'GE1': 23.5, 'GE0': 24.0}


# ---------------------------------------------------------------- the layout
def _line(face, side):
    """The first grid line on the room side of a wall face that keeps tube out of the plate's way."""
    return int(math.ceil((face + 0.2) / P - 1e-9)) if side > 0 else int(math.floor((face - 0.2) / P + 1e-9))


def port_nodes(st):
    k = _line(st['face'], st['side'])
    a, b = int(round(st['lo'] / P)), int(round(st['hi'] / P))
    return [(i, k) for i in range(a, b + 1)] if st['axis'] == 'y' else [(k, j) for j in range(a, b + 1)]


def station_at(st):
    """The middle of the port row, in feet (where the leaders gather up into the cabinet)."""
    k = _line(st['face'], st['side']) * P
    return ((st['lo'] + st['hi']) / 2, k) if st['axis'] == 'y' else (k, (st['lo'] + st['hi']) / 2)


def band_len(panel, v0, n):
    nodes, _, _, _ = band_path(panel, v0, n)
    return plen_nodes(nodes)


def est_lead(panel, st_at, v0=None, n=None):
    """A rough leader length for a loop of this panel (or of its band at rows v0..v0+n), both ways with the rises, from
    its lead nodes to the station."""
    if v0 is None:
        x0, y0, x1, y1 = panel.rect_ft()
        ex, ey = {'W': (x0, (y0 + y1) / 2), 'E': (x1, (y0 + y1) / 2), 'N': ((x0 + x1) / 2, y0), 'S': ((x0 + x1) / 2, y1)}[panel.entry]
    else:
        ex, ey = ft(panel.to_node(-1, v0 + panel.s * (n // 2)))
    return 2 * 1.3 * (abs(ex - st_at[0]) + abs(ey - st_at[1])) + 2 * RISE


def plan_bands(panel, cap, st_at, target, lead=None):
    """Split a panel into bands (one loop each) so that every band's tube plus its own leader comes as close to `target` as
    the rows allow, never over the loop budget: bands far from the station get fewer rows. `lead` is the panel's measured
    average leader from the last pass; it scales the estimates."""
    m, R = panel.local()
    R2 = R - R % 2
    if R2 < 2: return []
    scale = 1.0 if lead is None else lead / max(1.0, est_lead(panel, st_at))
    def leads_for(bands): return [scale * est_lead(panel, st_at, v0, n) for v0, n in bands]
    best = None
    for nb in range(1, R2 // 2 + 1):
        bands = band_loops(panel, -(-R2 // nb) + (-(-R2 // nb)) % 2)
        if len(bands) != nb: continue
        # reshape: rows in proportion to the tube each band may carry after its leader
        for _ in range(4):
            lds = leads_for(bands)
            w = [max(0.15, target - ld) for ld in lds]
            raw = [R2 * x / sum(w) for x in w]
            sizes = [max(2, int(round(x / 2)) * 2) for x in raw]
            while sum(sizes) > R2: sizes[sizes.index(max(sizes))] -= 2
            while sum(sizes) < R2: sizes[sizes.index(min(sizes))] += 2
            nbands = []; v = 0
            for n in sizes: nbands.append((v, n)); v += n * panel.s
            if nbands == bands: break
            bands = nbands
        if cap and max(n for _, n in bands) > cap: continue
        lens = [band_len(panel, v0, n) + ld for (v0, n), ld in zip(bands, leads_for(bands))]
        if max(lens) > MAX_LOOP - 4: continue
        score = max(abs(L - target) for L in lens)
        if best is None or score < best[0]: best = (score, bands)
        if max(lens) < target - 30: break          # splitting further only shortens them
    return best[1] if best else band_loops(panel, 2)


def _sub(a, b): return (a[0] - b[0], a[1] - b[1])


def band_rect(panel, v0, n):
    """The floor one band of a panel heats, in feet: its tube extents plus half a spacing all round."""
    s = panel.s
    a = panel.to_node(0, v0); b = panel.to_node(panel.local()[0] - 1, v0 + (n - 1) * s)
    x0, x1 = sorted((a[0], b[0])); y0, y1 = sorted((a[1], b[1]))
    h = s * P / 2
    return (x0 * P - h, y0 * P - h, x1 * P + h, y1 * P + h)


TARGET = 180.0            # the loop length every band is planned to, ft, so loops on a manifold come out alike
TARGETS = {}              # per-station overrides


def layout(caps=None, first=(), verbose=False, stop_before=None, leads=None):
    """Lay every loop out on the grid. Returns the loops (fields, leaders, lengths), the grid and a list of failures."""
    caps = dict(caps or {}); leads = dict(leads or {})
    grid = Grid(HOUSE, gates=GATES, no_tube=NO_TUBE, drains=DRAINS)
    panels = {k: Panel(v[0], v[1], v[2], v[3], v[4], v[5]) for k, v in PANELS.items()}
    for pn in panels.values():
        grid.field.update(pn.bbox_nodes())
    for k, st in STATIONS.items():
        grid.add_ports(k, port_nodes(st), st['room'])
    chained = {t: c for c in CHAINS for t in c[1:]}
    loops = []
    for k, v in PANELS.items():
        if k in chained: continue
        pn = panels[k]; st = v[6]
        if k in BANDS and k not in caps:
            bands = []; vv = 0
            for n in BANDS[k]: bands.append((vv, n)); vv += n * pn.s
        else:
            bands = plan_bands(pn, caps.get(k, v[7]), station_at(STATIONS[st]), TARGETS.get(st, TARGET), leads.get(k))
        chain = next((c for c in CHAINS if c[0] == k), None)
        for bi, (v0, n) in enumerate(bands):
            st_b = BAND_STATION.get((k, bi), st)
            if chain:
                # the loop runs on through every panel of the chain: open pairs through all but the last, which closes it
                if k in OPEN_AT_ENTRY:
                    if n % 4 == 2: n -= 2      # the open pair ends at the entry edge, beside the leads
                elif n % 4 == 0: n -= 2        # an open pair must end at the far edge
                if n < 2: continue
                segs = []
                for i, name in enumerate(chain):
                    pb = panels[name]
                    if i == 0: v_, n_ = v0, n
                    else:
                        m2, R2 = pb.local(); v_, n_ = 0, R2 - R2 % 2
                        if i < len(chain) - 1 and n_ % 4 == 0: n_ -= 2
                    if i < len(chain) - 1:
                        na, nb, lin, lout, ends = pair_open(pb, v_, n_)
                        segs.append(dict(open=True, a=na, b=nb, lin=lin, lout=lout, ends=ends, panel=pb, rect=band_rect(pb, v_, n_), room=PANELS[name][0]))
                    else:
                        nodes, _, lin, lout = band_path(pb, v_, n_)
                        segs.append(dict(open=False, field=nodes, lin=lin, lout=lout, panel=pb, rect=band_rect(pb, v_, n_), room=PANELS[name][0]))
                loops.append(dict(panel=k, band=bi, st=st_b, room=v[0], segs=segs, a=segs[0]['a'], lead_in=segs[0]['lin'], lead_out=segs[0]['lout'], n=n,
                                  panels=[g['panel'] for g in segs], rooms=[g['room'] for g in segs], rects=[g['rect'] for g in segs]))
            else:
                nodes, corners, lin, lout = band_path(pn, v0, n)
                loops.append(dict(panel=k, band=bi, st=st_b, room=v[0], field=nodes, lead_in=lin, lead_out=lout, panels=[pn], rooms=[v[0]], n=n,
                                  rects=[band_rect(pn, v0, n)]))
    # fields and the lead nodes go down first; leaders thread between them afterwards
    bad = []
    for i, l in enumerate(loops):
        l['tag'] = f'L{i + 1}'
        if 'field' in l:
            grid.take(l['field'], l['tag'] + 'f'); nodes = l['field']
        else:
            nodes = []
            for j, g in enumerate(l['segs']):
                if g['open']:
                    grid.take(g['a'], f"{l['tag']}a{j}"); grid.take(g['b'], f"{l['tag']}b{j}"); nodes += g['a'] + g['b']
                    grid.used[g['ends'][0]] = f"{l['tag']}c{j}a"; grid.used[g['ends'][1]] = f"{l['tag']}c{j}b"
                else:
                    grid.take(g['field'], f"{l['tag']}f{j}"); nodes += g['field']
                if j: grid.used[g['lin']] = f"{l['tag']}c{j - 1}a"; grid.used[g['lout']] = f"{l['tag']}c{j - 1}b"
        grid.used[l['lead_in']] = l['tag'] + 's'; grid.used[l['lead_out']] = l['tag'] + 'r'
        hit = [n for n in nodes if n in grid.blocked or n not in grid.room]
        if hit: bad.append(f"{l['tag']} {l['panel']}: field over a wall or post at {[ft(n) for n in hit[:3]]}")
    if bad: raise ValueError('; '.join(bad))
    fails = []
    # connectors of the chained loops: the pair runs on from a panel's two open ends to the next panel's lead nodes
    for l in loops:
        if 'segs' not in l: continue
        ok = True
        for j in range(len(l['segs']) - 1):
            g, h = l['segs'][j], l['segs'][j + 1]
            e0, e1 = g['ends']; t = f"{l['tag']}c{j}"
            r = pair_route(grid, e0, e1, _sub(e0, g['a'][-1]), leads=(h['lin'], h['lout'])) if ok else None
            if not r:
                if ok: fails.append((l['tag'], l['panel'], 'connector'))
                g['conn'] = None; ok = False
                continue
            ca, cb = r
            grid.used[ca[-1]] = t + 'a'; grid.used[cb[-1]] = t + 'b'     # whichever lead each tube landed on
            grid.take(ca, t + 'a'); grid.take(cb, t + 'b')
            # tube A runs on from end 0; if its connector lands on the next panel's lead-out, that panel is run the other way round
            if ca[-1] == h['lout']:
                if h['open']:
                    h['a'], h['b'] = h['b'], h['a']; h['ends'] = (h['ends'][1], h['ends'][0])
                    e0, e1 = h['ends']; grid.used[e0], grid.used[e1] = grid.used[e1], grid.used[e0]   # the tags on its open ends follow
                else: h['field'] = h['field'][::-1]
            g['conn'] = (ca, cb)
    # leaders, farthest loops first (they take the outside lanes), with any hand-picked ones before them
    def far(l):
        sx, sy = station_at(STATIONS[l['st']]); x, y = ft(l['lead_in'])
        return abs(x - sx) + abs(y - sy)
    def rank(l):
        k = l['panel']; kb = f"{k}.{l['band']}"
        if k in first: return (0, first.index(k), 0)
        if kb in ORDER: return (1, ORDER.index(kb), 0)
        return (1, ORDER.index(k) if k in ORDER else 99, far(l) * (1 if k in NEAR_FIRST else -1))
    order = sorted(loops, key=rank)
    for l in order:
        st = l['st']
        kb = f"{l['panel']}.{l['band']}"
        if stop_before and kb == stop_before: break
        d0 = _sub(l['lead_in'], l['field'][0] if 'field' in l else l['a'][0])
        grid.keep_out = set()
        for x0, y0, x1, y1 in KEEP_OUT.get(kb, KEEP_OUT.get(l['panel'], [])):
            grid.keep_out.update((i, j) for i in range(int(x0 / P), int(x1 / P) + 2) for j in range(int(y0 / P), int(y1 / P) + 2)
                                 if x0 - 1e-6 <= i * P <= x1 + 1e-6 and y0 - 1e-6 <= j * P <= y1 + 1e-6)
        pl = grid.ports[st]
        if kb in PORT or l['panel'] in PORT:
            c = int(round(PORT.get(kb, PORT.get(l['panel'])) / P)); ax = 0 if STATIONS[st]['axis'] == 'y' else 1
            pl = [n for n in pl if n[ax] in (c, c + 1)]
        r = pair_route(grid, l['lead_in'], l['lead_out'], d0, ports=pl)
        grid.keep_out = set()
        if r:
            ps, pr = r
            grid.take(ps, l['tag'] + 's'); grid.take(pr, l['tag'] + 'r')
            l['sup'], l['ret'] = ps, pr
        else:
            l['sup'] = l['ret'] = None
            fails.append((l['tag'], l['panel'], 'leader'))
            if verbose: print('FAIL', l['tag'], l['panel'], st)
    # lengths and the tube as drawn
    for l in loops:
        tube = []
        if l.get('sup'): tube += l['sup'][::-1]
        if 'field' in l:
            tube += l['field']; l['in_floor'] = plen_nodes(l['field'])
        else:
            A, B, L = [], [], 0.0
            for g in l['segs']:
                if g['open']:
                    A += g['a']; B = g['b'][::-1] + B; L += plen_nodes(g['a']) + plen_nodes(g['b'])
                    if g.get('conn'):
                        ca, cb = g['conn']; A += ca; B = cb[::-1] + B; L += plen_nodes(ca) + plen_nodes(cb) + 2 * P
                else:
                    A += g['field']; L += plen_nodes(g['field'])
            tube += A + B; l['in_floor'] = L
        if l.get('ret'): tube += l['ret']
        l['tube'] = tube
        l['leader'] = (plen_nodes(l['sup']) if l.get('sup') else 0) + (plen_nodes(l['ret']) if l.get('ret') else 0) + 2 * RISE
        l['total'] = l['in_floor'] + l['leader'] + (2 * P if l.get('sup') else 0) + (2 * P if l.get('ret') else 0)   # the steps from lead nodes into the field
        l['ports'] = (l['sup'][-1], l['ret'][-1]) if l.get('sup') and l.get('ret') else None
    return loops, grid, fails


def solve(verbose=False):
    """Lay out with estimated leaders, then again with the leaders as routed (so the bands are planned to the real
    totals), then trim any band whose loop came out over budget and put loops that could not be routed first."""
    caps = {}; first = []; leads = {}
    for it in range(16):
        loops, grid, fails = layout(caps, first, verbose, leads=leads)
        over = [l for l in loops if l['total'] > MAX_LOOP]
        if verbose:
            print(f"pass {it}: {len(loops)} loops, {len(fails)} failures, {len(over)} over {MAX_LOOP:.0f}'")
        if it < 2:
            # plan the next pass with each panel's measured leader (its bands' average)
            acc = {}
            for l in loops:
                if l.get('sup'): acc.setdefault(l['panel'], []).append(l['leader'] + 4 * P)
            leads = {k: sum(v) / len(v) for k, v in acc.items()}
            if it == 0: continue
        if not fails and not over: return loops, grid
        for tag, panel, what in fails:
            if panel not in first: first.append(panel)
        for l in over:
            caps[l['panel']] = max(2, min(caps.get(l['panel'], 99), l['n'] - 2))
    raise RuntimeError(f'radiant layout did not settle: failures {fails}, over budget {[l["tag"] for l in over]}')


# ---------------------------------------------------------------- hydronics
def lc(t): return t[:1].lower() + t[1:]


def head_ft(L, gpm): return L * 0.0118 * (gpm / 0.5) ** 1.75


def plen(pts): return sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(pts, pts[1:]))


def room_loads():
    out = {}
    for r in HOUSE['rooms']:
        if r['kind'] == 'outdoor': continue
        h = hvac.room_load(r)['heat']
        if r['kind'] == 'garage':
            h *= (GARAGE_F - CLIMATE['heat_design_f']) / (CLIMATE['indoor_heat_f'] - CLIMATE['heat_design_f'])
        out[r['id']] = h
    return out


# the 1" feed pairs from the circulators in the mechanical closet to the remote stations, under the boards; MF-2 sits in the
# closet and is piped straight to its circulator. Each is drawn a few inches from the next so they read apart.
FEED_ROUTES = {
    'MF-1': [HS, (31.6, HS[1]), (31.6, 18.4), STATIONS['MF-1']['riser']],
    'MF-G': [HS, (32.0, HS[1]), (32.0, 36.4), STATIONS['MF-G']['riser']],
    'MF-4': [HS, (HS[0], 44.5), (64.9, 44.5), STATIONS['MF-4']['riser']],
    'MF-3': [HS, (HS[0] - 0.3, HS[1]), (HS[0] - 0.3, 44.8), (65.2, 44.8), (65.2, 28.9), STATIONS['MF-3']['riser']],
}


def hydronics(loops, grid):
    """Each loop's heat, flow, head and water temperature, and the feed pairs. A room's M-1 load is carried by all the tube in
    it, fields and the leaders passing through alike, shared by length; the floor a room's tube heats is half a square foot per
    foot of tube (6" spacing), up to the room's area, and that sets the water it needs."""
    loads = room_loads()
    tube_in = {}
    for l in loops:
        cnt = {}
        for n in l['tube']:
            r = grid.room.get(n)
            if r: cnt[r] = cnt.get(r, 0) + 1
        l['ft_in'] = {r: c * P for r, c in cnt.items()}
        for r, f in l['ft_in'].items(): tube_in[r] = tube_in.get(r, 0.0) + f
    heated = {r: min(ROOMS[r]['area_sf'], f * 0.5) for r, f in tube_in.items()}
    for l in loops:
        z = ZONE_OF[l['rooms'][0]]; l['zone'] = z; l['id'] = l['tag']
        shares = {r: f / tube_in[r] for r, f in l['ft_in'].items()}
        q_room = sum(loads[r] * sh for r, sh in shares.items())
        area = sum(heated[r] * sh for r, sh in shares.items())
        t_room = GARAGE_F if z == GZ else CLIMATE['indoor_heat_f']
        r_tot = R_SLAB[6] + (0.0 if z == GZ else R_COVER) + R_SURF
        # the water the loop needs is set by the room it heats most that needs the most (a doorway it passes through does not count)
        main = [r for r in shares if l['ft_in'][r] >= 10 or r in l['rooms']]
        flux = max(loads[r] / heated[r] for r in main)
        short = sum(max(0.0, loads[r] - heated[r] * (T_SUP - DT / 2 - t_room) / r_tot) * shares[r] for r in main) if z != GZ else 0.0
        l.update(area=area, q_room=q_room, q=q_room * (1 + DOWN), t_avg=t_room + flux * r_tot, t_surf=t_room + flux * R_SURF, short=short,
                 room_names=[ROOMS[r]['name'] for r in l['rooms']], heats=[ROOMS[r]['name'] for r in sorted(shares, key=lambda r: -l['ft_in'][r]) if l['ft_in'][r] >= 10])
        l['gpm'] = max(0.2, l['q'] / (500 * DT)); l['head'] = head_ft(l['total'], l['gpm'])
    unheated = [(r['id'], r['name'], loads[r['id']]) for r in HOUSE['rooms'] if r['kind'] != 'outdoor' and r['id'] not in tube_in]
    by_leaders = [(r['id'], r['name'], loads[r['id']], tube_in[r['id']]) for r in HOUSE['rooms'] if r['kind'] != 'outdoor' and r['id'] in tube_in and r['id'] not in {rm for l in loops for rm in l['rooms']}]
    feeds = []
    for k, pts in FEED_ROUTES.items():
        feeds.append(dict(id='F-' + k[3:], mf=k, to=k, pts=pts, lf=plen(pts), gpm=sum(l['gpm'] for l in loops if l['st'] == k)))
    return loads, unheated, by_leaders, feeds


def coils(lengths, coil=1000.0):
    """How many coils the loops cut from, one uncut length per loop, longest first into whichever coil has room."""
    left = []
    for L in sorted(lengths, reverse=True):
        for i, r in enumerate(left):
            if r >= L: left[i] -= L; break
        else: left.append(coil - L)
    return len(left)


# ---------------------------------------------------------------- the sheet
def draw_boards(sh):
    """The boards under the slab, on the rooms layer: 4' x 4' in a running bond from the datum, with their 3" nub grid as the
    dot pattern (a dot is a puck; tube runs between the dots), clipped to the slab."""
    clip = ' '.join(f'{px(x):.1f},{py(y):.1f}' for x, y in plumbing.OUTLINE)
    tile = P * S
    sh.add(f'<defs><clipPath id="r1-slab"><polygon points="{clip}"/></clipPath>'
           f'<pattern id="r1-nubs" patternUnits="userSpaceOnUse" x="{px(0):.1f}" y="{py(0):.1f}" width="{tile:.3f}" height="{tile:.3f}">'
           f'<circle cx="{tile / 2:.3f}" cy="{tile / 2:.3f}" r="0.38" fill="#aaa399"/></pattern></defs>', 'rooms')
    xs = [p[0] for p in plumbing.OUTLINE]; ys = [p[1] for p in plumbing.OUTLINE]
    B = BOARD['size']
    out = [f'<g clip-path="url(#r1-slab)"><polygon points="{clip}" fill="url(#r1-nubs)"/>']
    for k in range(int(min(ys) // B), int(max(ys) // B) + 1):
        y0 = k * B; y1 = y0 + B
        out.append(f'<line x1="{px(min(xs)):.1f}" y1="{py(y0):.1f}" x2="{px(max(xs)):.1f}" y2="{py(y0):.1f}" stroke="#bdb6aa" stroke-width="0.7"/>')
        off = B / 2 if k % 2 else 0.0
        for j in range(int(min(xs) // B) - 1, int(max(xs) // B) + 2):
            x = j * B + off
            out.append(f'<line x1="{px(x):.1f}" y1="{py(y0):.1f}" x2="{px(x):.1f}" y2="{py(y1):.1f}" stroke="#bdb6aa" stroke-width="0.7"/>')
    out.append('</g>')
    sh.add(''.join(out), 'rooms')


def station_box(st, grow=0.25, depth=0.35, into_wall=0.0):
    """A manifold cabinet on the plan: along the wall over its port row, `depth` into the room (and `into_wall` the other way)."""
    lo, hi = st['lo'] - grow, st['hi'] + grow
    f, sd = st['face'], st['side']
    if st['axis'] == 'y': return (lo, min(f - sd * into_wall, f + sd * depth), hi, max(f - sd * into_wall, f + sd * depth))
    return (min(f - sd * into_wall, f + sd * depth), lo, max(f - sd * into_wall, f + sd * depth), hi)


def build():
    sh = Sheet('R-1', 'Radiant floor', f"PEX loops on 3\" nub boards under the slab: {MAX_LOOP:.0f}' loops, nothing crossing, five manifolds on four zones with a circulator each, flows at {CLIMATE['name']} design ({CLIMATE['heat_design_f']:.0f}°F).")
    sh.base()
    draw_boards(sh)
    loops, grid = solve()
    verify(grid, [(l['tag'], l['tube']) for l in loops])
    loads, unheated, by_leaders, feeds = hydronics(loops, grid)
    t_supply = min(T_SUP, math.ceil((max(l['t_avg'] for l in loops if l['zone'] != GZ) + DT / 2) / 5) * 5)
    shorts = [l for l in loops if l['short'] > 300]
    by_st = {k: [l for l in loops if l['st'] == k] for k in STATIONS}
    def port_no(l):
        row = grid.ports[l['st']]
        return tuple(row.index(n) + 1 for n in l['ports'])
    picks = {}
    for l in loops:
        z = l['zone']; Z = ZONES[z]; c = Z['color']; st = l['st']; ps, pr = port_no(l)
        rooms = ', '.join(l['room_names'])
        title = (f"Loop {l['id']}, zone {z[1:]} ({Z['name']}): {rooms}. {l['in_floor']:.0f}' in the field + {l['leader']:.0f}' of leaders = {l['total']:.0f}' of 1/2\" PEX at 6\" o.c., "
                 f"to {st} ports {ps} and {pr}. {l['q']:,.0f} Btu/h, {l['gpm']:.2f} gpm on the flow meter, {l['head']:.1f} ft of head. One continuous coil, no fittings in the slab; tag both ends {l['id']}.")
        sh.open_group(l['id'], title)
        tube = l['tube']; ns, nr = len(l['sup']), len(l['ret'])
        sh.path(corners_ft(tube), 'transparent', 7)
        sh.path(corners_ft(tube[ns - 1:len(tube) - nr + 1]), c, 1.1, extra=' class="pex"')
        sh.path(corners_ft(l['sup']), c, 0.9, '4,1.2', extra=' class="lead"'); sh.path(corners_ft(l['ret']), c, 0.9, '4,1.2', extra=' class="lead"')
        x0, y0, x1, y1 = max(l['rects'], key=lambda r: (r[2] - r[0]) * (r[3] - r[1]))
        sh.add(f'<text x="{px((x0 + x1) / 2):.1f}" y="{py((y0 + y1) / 2 + (1.4 if y1 - y0 > 4 else 0)):.1f}" font-size="7.5" font-weight="700" fill="{c}" text-anchor="middle" dominant-baseline="middle" stroke="#fff" stroke-width="2.5" paint-order="stroke">{l["id"]}</text>')
        sh.close_group()
        picks[l['id']] = dict(tag=l['id'], sub=f"Zone {z[1:]} · {Z['name']}", fields=[
            ('Rooms', rooms + (f" (its leaders also heat {', '.join(h for h in l['heats'] if h not in l['room_names'])})" if [h for h in l['heats'] if h not in l['room_names']] else '')), ('Tube', f"{l['total']:.0f}' of 1/2\" PEX: {l['in_floor']:.0f}' in the field at 6\" o.c. + {l['leader']:.0f}' of leaders (both ends, with the 2' rises)"),
            ('Manifold', f"{st}, ports {ps} (supply) and {pr} (return), {lc(STATIONS[st]['where'])}"), ('Heat', f"{l['q']:,.0f} Btu/h at design, {l['area']:.0f} sq ft of heated floor"),
            ('Flow', f"{l['gpm']:.2f} gpm on the flow meter, {l['head']:.1f} ft of head in the tube"),
            ('Water / floor', f"needs about {l['t_avg']:.0f}°F average water; floor surface about {l['t_surf']:.0f}°F at design"),
            ('Zone', f"{z[1:]}, {Z['name']}: {Z['stat']} starts circulator P-R{z[1:]} in the mechanical closet; no actuator on the port")])
    for f in feeds:
        fz = STATIONS[f['mf']]['zone'][1:]
        sh.open_group(f['id'], f"1\" PEX supply and return pair, circulator P-R{fz} in the mechanical closet to {f['to']}: about {f['lf']:.0f}' each way, {f['gpm']:.1f} gpm, under the boards, insulated end to end.")
        sh.path(f['pts'], 'transparent', 7); sh.path(f['pts'], '#6a1b9a', 3.0); sh.path(f['pts'], '#fff', 1.0)
        sh.close_group()
        picks[f['id']] = dict(tag=f['id'], sub=f"Feed pair to {f['to']}", fields=[('Pipe', '1" PEX supply + return, closed-cell insulated end to end, in the base course under the nub boards'),
                                                                                ('Run', f"about {f['lf']:.0f}' each way from circulator P-R{fz} by HS-1"), ('Flow', f"{f['gpm']:.1f} gpm with every loop on {f['to']} calling")])
    for f in PENETRATIONS:   # where P-1 comes up through a field: the installer shifts one run over a channel there
        x, y = f['at']; what = {'wc': 'closet flange', 'drain': 'drain body', 'tub': 'tub trap', 'stack': 'stack'}[f['kind']]
        sh.open_group('X-' + f['id'], f"{f['id']}: {f['name']} comes up through the slab here (P-1). Shift the one run it meets over a channel for the length of the fitting, so the tube stays 3\" clear of the {what}.", layer='tags', hit=(x, y, 0.9))
        sh.circle(x, y, 0.42, '#fff', '#b4462f', 1.2, layer='tags')
        sh.line(x - 0.3, y - 0.3, x + 0.3, y + 0.3, '#b4462f', 1.2, layer='tags'); sh.line(x - 0.3, y + 0.3, x + 0.3, y - 0.3, '#b4462f', 1.2, layer='tags')
        sh.close_group(layer='tags')
    for k, st in STATIONS.items():
        on = by_st[k]; n = len(on); nports = len(grid.ports[k])
        x, y = station_at(st)
        title = f"{k}: {n}-loop stainless manifold with flow meters, all zone {st['zone'][1:]} ({ZONES[st['zone']]['name']}), {lc(st['where'])}. {st['detail']}"
        sh.open_group(k, title, hit=(x, y, 1.4))
        bx = station_box(st, into_wall=0.25)
        sh.rect(bx[0], bx[1], bx[2], bx[3], '#fff', '#222', 1.3, '4,2')
        horiz = st['axis'] == 'y'
        sh.text((bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2, k, 6.5, '#222', '700', rot=0 if horiz else -90, layer='disc')
        sh.close_group()
        picks[k] = dict(tag=k, sub=st['where'], fields=[
            ('Manifold', f"{n}-loop stainless, flow meters, isolation ball valves, purge/fill; no actuators, the whole manifold is zone {st['zone'][1:]} on circulator P-R{st['zone'][1:]}" + (' (two manifolds side by side)' if n > 8 else '')),
            ('Loops', ', '.join(f"{l['id']} on {'/'.join(str(p) for p in port_no(l))}" for l in on) + f"; {2 * n} of {nports} 3\" port positions used"),
            ('Flow', f"{sum(l['gpm'] for l in on):.1f} gpm with all loops calling"), ('Where', st['detail'])])
    x, y = HS
    sh.open_group('HS-1', 'HS-1, condensing boiler for the slab, with the four zone circulators P-R1 to P-R4, the garage mixing valve and the zone controller', hit=(x, y, 1.2))
    sh.rect(x - 1.1, y - 0.6, x + 1.1, y + 0.6, '#fff', '#6a1b9a', 1.6); sh.text(x, y, 'HS-1', 6, '#6a1b9a', '700', layer='disc')
    sh.close_group()
    tot_q = sum(l['q'] for l in loops); house_q = sum(l['q'] for l in loops if l['zone'] != GZ); tot_gpm = sum(l['gpm'] for l in loops)
    picks['HS-1'] = dict(tag='HS-1', sub='Mechanical closet', fields=[
        ('Equipment', "Wall-hung condensing boiler with outdoor reset, on natural gas or propane (owner's picks, 2026-10-13); circuit 27 on E-1"),
        ('Output', f"{tot_q:,.0f} Btu/h with every zone calling, {house_q:,.0f} Btu/h for the house alone"),
        ('Water', f"{t_supply:.0f}°F supply at {CLIMATE['heat_design_f']:.0f}°F outside, reset down to about 80°F at 50°F outside; garage loops mix down to about 70°F"),
        ('Pumps', 'Four ECM circulators on constant ΔP, one per zone, all in this closet: P-R1 garage (MF-G, on its own mixing valve), P-R2 great room (MF-2 here and MF-3 by a 1" pair), P-R3 master suite and utility (MF-1), P-R4 bedroom wing and office (MF-4)'),
        ('Controls', '24 V zone controller: T1 to T4 each start their circulator; outdoor sensor on the shaded rear wall')])
    for z, Z in ZONES.items():
        x, y = STATS[Z['stat']]
        sh.tag(x, y, Z['stat'], Z['color'], id=Z['stat'], title=f"{Z['stat']}, zone {z[1:]} thermostat ({Z['name']}): {Z['where']}.", r=0.62, size=6)
        lz = [l for l in loops if l['zone'] == z]
        picks[Z['stat']] = dict(tag=Z['stat'], sub=f"Zone {z[1:]} · {Z['name']}", fields=[('Where', Z['where']), ('Loops', ', '.join(l['id'] for l in lz)),
                                                                                       ('Manifolds', ', '.join(sorted({l['st'] for l in lz}))), ('Load', f"{sum(l['q'] for l in lz):,.0f} Btu/h at design")])
    legend = [(Z['color'], f"Zone {z[1:]}, {Z['name']} ({Z['stat']})") for z, Z in ZONES.items()] + [('#6a1b9a', '1" feed pair from the closet circulators, under the boards')]
    sym = [(f'<line x1="-12" y1="0" x2="12" y2="0" stroke="{c}" stroke-width="1.6"/>', t) for c, t in legend[:-1]]
    sym += [('<line x1="-12" y1="0" x2="12" y2="0" stroke="#555" stroke-width="1" stroke-dasharray="4,1.2"/>', 'leaders, supply and return side by side 3" apart'),
            ('<line x1="-12" y1="0" x2="12" y2="0" stroke="#6a1b9a" stroke-width="3"/><line x1="-12" y1="0" x2="12" y2="0" stroke="#fff" stroke-width="1"/>', legend[-1][1]),
            ('<rect x="-9" y="-4" width="18" height="8" fill="#fff" stroke="#222" stroke-dasharray="3,2"/>', 'manifold cabinet over its row of 3" ports'),
            ('<rect x="-10" y="-6" width="20" height="12" fill="#fff" stroke="#bdb6aa"/><line x1="0" y1="-6" x2="0" y2="6" stroke="#bdb6aa"/>' + ''.join(f'<circle cx="{cx}" cy="{cy}" r="0.5" fill="#aaa399"/>' for cx in (-7.5, -5, -2.5, 2.5, 5, 7.5) for cy in (-3.5, -1, 1.5, 4)), "4' x 4' nub boards in a running bond from the datum; dots are the 3\" puck grid")]
    sh.legend(sym)
    # numbers for the notes and tables
    tot_tube = sum(l['total'] for l in loops); leaders = sum(l['leader'] for l in loops)
    longest = max(loops, key=lambda l: l['total']); shortest = min(loops, key=lambda l: l['total'])
    worst = max(loops, key=lambda l: l['head'])
    feed_lf = sum(f['lf'] for f in feeds)
    slab_sf = HOUSE['totals']['heated_gross_sf'] + HOUSE['totals']['garage_gross_sf']
    boards = math.ceil(slab_sf / BOARD['sf'] * 1.05); bundles = max(BOARD['min_bundles'], math.ceil(boards / BOARD['per_bundle']))
    n_coils = coils([l['total'] * 1.02 for l in loops])
    unheated_txt = ', '.join(f"{nm} ({q:,.0f} Btu/h)" for _, nm, q in unheated)
    leaders_txt = ', '.join(f"{nm} ({ft:.0f}' of leaders for {q:,.0f} Btu/h)" for _, nm, q, ft in by_leaders)
    gates_txt = 'under the master bed wall into MF-1, under the kitchen wall into the pantry and under the pantry wall into MF-2, under the living room wall into MF-3 and MF-4, under the master hall wall into the powder room, and under the bath 1 wall from the bedroom 2 closet'
    spread_txt = ', '.join(f"{k} {min(l['total'] for l in by_st[k]):.0f}'-{max(l['total'] for l in by_st[k]):.0f}'" for k in STATIONS if by_st[k])
    station_txt = '; '.join(f"{k} ({lc(STATIONS[k]['where'])}, {len(by_st[k])} loops) serves " + ', '.join(sorted({r for l in by_st[k] for r in l['room_names']}, key=lambda n: [r['name'] for r in HOUSE['rooms']].index(n))) for k in STATIONS)
    notes = [
        f"The layout is drawn on the boards' own grid. {BOARD['name']}s ({BOARD['size']:.0f}' x {BOARD['size']:.0f}', {BOARD['thick_in']:.0f}\" thick: {BOARD['eps_in']:.0f}\" of EPS, R-{BOARD['r']:.0f}, under a {BOARD['puck_in']:.0f}\" grid of pucks on {BOARD['pitch_in']:.0f}\" centres) go down in a running bond with their puck rows on the 3\" lines from the datum at 0,0 (the garage-door wall's outside face and the master bed's rear wall line, as on every sheet), so every tube on this sheet sits in a channel between pucks. Lay the first board's corner at the datum and the rest follow; a board cut at a wall keeps its grid.",
        f"Tube: {len(loops)} loops of 1/2\" O2-barrier PEX, none over {MAX_LOOP:.0f}' with its leaders and the 2' rises at the cabinet ({longest['id']} is the longest at {longest['total']:.0f}', {shortest['id']} the shortest at {shortest['total']:.0f}'). Fields at 6\" o.c. (every other channel), supply and return side by side so each loop's two ends leave its field together; leaders run as 3\" pairs through doorways and along walls to their manifold. Nothing crosses anything: the whole layout was checked tube by tube on the grid. One continuous coil per loop, no fittings in the slab; tag both ends with the loop number at the cabinet. The loops on one manifold are planned to like lengths so they balance on their flow meters ({spread_txt}); MF-1's spread is the master bath, whose three small fields are boxed in by the toilet and shower walls and can neither join each other nor share rows with the bedroom.",
        f"Under a wall only where drawn, straight across and only for the length drawn: {gates_txt}. Mark every wall crossing on the boards before the pour so the plate anchors and shots stay 12\" off it; everywhere else the leaders go through the doorway.",
        f"The tube runs under everything that sits on the floor: the kitchen base cabinets, island, fridge and range, the washer and dryer, the tubs, showers, vanities and toilets, the hearth. It lies about {-SLAB_H * 12:.0f}\" below the top of the slab, so nothing fastened to the floor reaches it; only the walls and their plates, the posts and the manifold port rows keep it out. Where P-1 brings a drain, a tub trap, a closet flange or a vent stack up through the slab ({len(PENETRATIONS)} places, each marked with a crossed circle) shift the one run it meets over a channel for the length of the fitting, so the tube stays 3\" clear of the flange or drain body; the showers' floors are heated like the rest.",
        f"Manifolds, five stations, each wholly on one zone, each with a 3\" port position per tube end in one row along its wall (the schedule gives every loop's two port numbers, counted from the low end of the row): {station_txt}. The four circulators are in the mechanical closet with HS-1: MF-2 is piped to P-R2 there; MF-1, MF-3, MF-4 and MF-G each get a 1\" insulated pair under the boards, {feed_lf:.0f}' each way in all.",
        f"The leaders rise straight up out of the slab at their port positions into the cabinet (sleeve each rise in 12\" of pipe insulation where it leaves the concrete) and bundle up to the manifold; they may be gathered sideways in the last 12\" below the cabinet. Cabinets are recessed in the hall wall (MF-3, MF-4) and surface-mounted on the laundry's sound wall (MF-1), low on the closet's east wall under the boiler (MF-2) and on the garage face of the mud room wall (MF-G).",
        f"Zoning is by manifold: four zones (garage; great room; master suite and utility; bedroom wing and office), each a circulator in the mechanical closet started by its thermostat, and every loop on a manifold is on that manifold's zone. Zone 2 has two manifolds, MF-2 and MF-3, on the one circulator. No actuators: balance each loop on its flow meter.",
        f"Flow: {tot_gpm:.1f} gpm with every loop calling, each loop set on its flow meter at a {DT:.0f}°F drop. Design heat {tot_q:,.0f} Btu/h, of which {tot_q - house_q:,.0f} is the garage at {GARAGE_F:.0f}°F; {DOWN * 100:.0f}% is added for heat lost down through the R-{BOARD['r']:.0f} boards and out the slab edge. Rooms with no field of their own are heated by the leader bundles running through them: {leaders_txt}. Nothing heats the {unheated_txt}; they borrow from the rooms around them.",
        f"Water: {t_supply:.0f}°F supply at {CLIMATE['heat_design_f']:.0f}°F outside, reset lower as it warms, so a condensing boiler stays condensing. Floor surfaces stay at or under {max(l['t_surf'] for l in loops if l['zone'] != GZ):.0f}°F."
        + (' At that supply ' + ', '.join(f"{l['id']} ({', '.join(l['room_names'])}) falls about {l['short']:,.0f} Btu/h short" for l in shorts) + ' at design; see the open items.' if shorts else ''),
        "Pumps: one constant-ΔP ECM circulator per zone, sized on the zone's hardest loop plus about 3 ft for the feed pair and manifold: " + '; '.join(f"P-R{z[1:]} about {math.ceil(max(l['head'] for l in loops if l['zone'] == z) + 3)} ft ({max((l for l in loops if l['zone'] == z), key=lambda l: l['head'])['id']}, {sum(l['gpm'] for l in loops if l['zone'] == z):.1f} gpm)" for z in ZONES) + '.',
        f"Under the boards: 10-mil vapor barrier over the compacted base, lapped and taped; R-10 (2\") rigid foam at the slab edge. The 4\" slab goes over the pucks with the tube tops about 1\" below the surface of the boards; no mesh ties are needed, the pucks hold the tube. Pressure test every loop at 100 psi water or 60 psi air for 24 hours before the pour and keep it under pressure through the pour. Photograph every room with a tape in frame before concrete.",
        'HS-1, the four circulators and the zone controller are circuit 27 on E-1 (200 A panel in the garage); the manifold cabinets need no power. T1 to T4 wire to the zone controller in the closet.',
        f"P-1's water lines, vents and drains are all in the base course below the boards and the feed pairs (cold PEX {plumbing.ft_in(-plumbing.COLD_H)} down, hot {plumbing.ft_in(-plumbing.HOT_H)}, drains below both), so the boards go down whole, with no channels cut for plumbing.",
    ]
    open_items = [f"{l['id']} ({', '.join(l['room_names'])}): the floor carries all but about {l['short']:,.0f} Btu/h of the room at {CLIMATE['heat_design_f']:.0f}°F with {T_SUP:.0f}°F water. Add a small electric towel warmer, or run the boiler hotter on the coldest days." for l in shorts] + [
        "Not tubed: the coat closet (about 6 sq ft), the bedroom 1 bypass closet (about 20 sq ft), the 3' x 10' notch at the garage's north wall beside the master closet (about 31 sq ft, left bare by decision 2026-10-14), the laundry's west floor along the counter (about 15 sq ft: every way of tubing it either takes the laundry loop past 200' or crosses the closet and mud room leaders that use that floor) and the west 18\" of the powder room under the lav (about 9 sq ft: the powder is the middle panel of the mud room leg's loop, which can only be 3' or 5' wide there, and 5' would not clear the east wall). The first three are too small for a loop of their own at the lengths on their manifold, and none can be added to a neighbouring loop without crossing another. All five sit inside heated floor and borrow from it.",
        "Boiler model: HS-1 is a condensing boiler on natural gas or propane (decided 2026-10-13). Pick a combi or a boiler with an indirect tank if it should also make the domestic hot water and replace P-1's 50 gal heater; propane needs the boiler's LP conversion kit.",
        'Garage: kept at 50°F on its own manifold, pump and thermostat. Decide whether it runs a glycol mix behind a plate heat exchanger, which protects it if the house loses power in a cold snap with the doors open.',
        'Flooring: the loops assume hard-surface floors. Carpet in a bedroom needs about 10°F warmer water for that loop.',
        "S-1: MF-3 and MF-4 recess into the hall's 2x4 west wall (3-1/2\" deep; fur locally if the chosen manifold needs more). MF-4's recess is 2'-0\" longer than S-1 framed it, 32'-0\" to 37'-3\" along the wall; the MF-K and MF-5 recesses are no longer needed and MF-1's surface cabinet now runs 18'-6\" to 24'-3\" at 4' up, over the dryer.",
        "E-1: no actuators, so the receptacles at the manifold cabinets are not needed; HS-1, the four circulators and the zone controller stay on circuit 27, and T1 to T4 wire to the zone controller in the closet.",
        "P-1: the closet's east wall is shared, MF-2 low at its north end under HS-1 and the water heater at its south end; the main water manifold and its risers stay west of MF-2's port column (x 33'-6\"). The pantry floor carries MF-2's leaders at 3\" across its west end and runs warmer than the rooms around it; sleeve the bundle if the pantry should stay cool.",
        f"The {BOARD['name']}s come {BOARD['per_bundle']} to a bundle ({BOARD['per_bundle'] * BOARD['sf']:.0f} sq ft), {BOARD['min_bundles']} bundles minimum: {bundles} bundles cover the {slab_sf:,} sq ft slab with 5% for cuts. Confirm the lead time; the board layout can start at any corner as long as the grid holds the datum.",
    ]
    sh.title_block([f"{len(loops)} loops, {tot_tube:,.0f}' of 1/2\" PEX, {len(STATIONS)} manifolds, no loop over {MAX_LOOP:.0f}'.", 'Green zone 1 (garage), orange zone 2, red zone 3, blue zone 4.',
                    f"{tot_q / 1000:,.0f} kBtu/h at design, {t_supply:.0f}°F supply.", f"{BOARD['name']}s on the 3\" grid from the datum; nothing crosses; tube under every fixture."])
    loop_rows = [(l['id'], [l['id'], l['zone'][1:], ', '.join(l['room_names']), l['st'], '/'.join(str(p) for p in port_no(l)), f"{l['in_floor']:.0f}'", f"{l['leader'] / 2:.0f}'", f"{l['total']:.0f}'",
                           f"{l['q']:,.0f}", f"{l['gpm']:.2f} gpm", f"{l['head']:.1f} ft", f"{l['t_surf']:.0f}°F"]) for l in loops]
    for z, Z in ZONES.items():
        lz = [l for l in loops if l['zone'] == z]
        loop_rows.append((Z['stat'], [f"Zone {z[1:]}", z[1:], Z['name'], ', '.join(sorted({l['st'] for l in lz})), '', f"{len(lz)} loops", '', f"{sum(l['total'] for l in lz):,.0f}'",
                                       f"{sum(l['q'] for l in lz):,.0f}", f"{sum(l['gpm'] for l in lz):.1f} gpm", '', '']))
    mf_rows = []
    for k, st in STATIONS.items():
        on = by_st[k]; f = next((f for f in feeds if f['mf'] == k), None)
        mf_rows.append((k, [k, f"{len(on)} loops: " + ', '.join(l['id'] for l in on), f"{2 * len(on)} of {len(grid.ports[k])}", st['where'], st['zone'][1:],
                            f"1\" pair {f['id']}, {f['lf']:.0f}' each way, from P-R{st['zone'][1:]}" if f else f"piped direct to P-R{st['zone'][1:]} in the closet"]))
    tables = [
        dict(key='loops', title='Loop schedule', lede='Ports are the supply and return positions counted from the low end of the manifold\'s row. Leader is each way. Heat includes the share lost downward. Pick a row to find the loop.',
             cols=['Loop', 'Zone', 'Rooms', 'Manifold', 'Ports', 'In field', 'Leader', 'Total', 'Btu/h', 'Flow', 'Head', 'Floor'], rows=loop_rows),
        dict(key='manifolds', title='Manifolds', lede='Each station\'s row of 3" port positions along its wall; a loop takes two next to each other.', cols=['Tag', 'Loops', 'Ports used', 'Where', 'Zones', 'Feed'], rows=mf_rows),
        dict(key='bom', title='Bill of materials', lede='Rough-order quantities from the drawing geometry, for pricing. The installer takes off the final list.', cols=['Item', 'Qty', 'Notes'], rows=[
            (None, ['1/2" O2-barrier PEX, 1,000\' coils', f'{n_coils} coils', f"{tot_tube:,.0f}' in {len(loops)} uncut lengths of {shortest['total']:.0f}' to {longest['total']:.0f}' (the schedule), cut longest first"]),
            (None, [BOARD['name'] + f", {BOARD['size']:.0f}' x {BOARD['size']:.0f}'", f'{boards} boards ({bundles} bundles of {BOARD["per_bundle"]})', f"{slab_sf:,} sq ft of slab + 5% for cuts; R-{BOARD['r']:.0f}, 1/2\" tube channels on 3\" centres"]),
            (None, ['1" PEX supply + return, insulated', f"{feed_lf * 2 * 1.05:.0f} lf", 'HS-1 to the stations, in the base course under the boards']),
            (None, ['Stainless manifolds with flow meters', f"{len(STATIONS)} stations", ', '.join(f"{k} {len(by_st[k])}-loop" for k in STATIONS) + ' (MF-G as two manifolds side by side)']),
            (None, ['Zone controller + thermostats', '1 + 4', 'T1 to T4, one per zone, each starting its circulator; outdoor reset sensor']),
            (None, ['Circulators', '4', 'P-R1 to P-R4, ECM on constant ΔP, one per zone, all in the mechanical closet; P-R1 with the garage mixing valve']),
            (None, ['Manifold cabinets', str(len(STATIONS)), 'recessed at MF-3 and MF-4; surface at MF-1, MF-2 and MF-G']),
            (None, ['R-10 rigid foam, 2", slab edge', f"{round(plen(plumbing.OUTLINE + plumbing.OUTLINE[:1]) * 1.05):,} lf", 'the perimeter of the slab, full depth']),
            (None, ['10-mil vapor barrier', f"{slab_sf * 1.1:,.0f} sf", 'under the boards, lapped and taped']),
            (None, ['Pipe insulation, 1/2" x 12"', f"{2 * len(loops)} pcs", 'one sleeve on every tube end where it rises out of the concrete']),
        ]),
    ]
    summary = dict(loops=len(loops), tube_ft=round(tot_tube), heat=round(tot_q), house_heat=round(house_q), gpm=round(tot_gpm, 1), supply_f=t_supply, manifolds=len(STATIONS), boards=boards)
    # 3D model (build/app_template.html, the radiant section): one tube mesh per loop on the boards, the manifold cabinets with their
    # riser bundles, the 1" feed pairs under the boards, HS-1, the thermostats and the board layer as a ghost. Heights are feet from the slab top.
    loops3d = []
    for l in loops:
        loops3d.append(dict(id=l['id'], zone=l['zone'], color=ZONES[l['zone']]['color'], mf=l['st'], rise=list(station_at(STATIONS[l['st']])),
                            name=f"{l['id']} · zone {l['zone'][1:]}, {', '.join(l['room_names'])}",
                            text=f"{l['total']:.0f}' of 1/2\" PEX at 6\" o.c. on the nub boards, {l['gpm']:.2f} gpm, to {l['st']} ports {'/'.join(str(p) for p in port_no(l))} (R-1)",
                            paths=[[list(p) for p in corners_ft(l['tube'])]], panels=[list(r) for r in l['rects']]))
    stations3d = []
    for k, st in STATIONS.items():
        on = by_st[k]; lo, hi = st['mount']
        stations3d.append(dict(id=k, at=list(station_at(st)), box=list(station_box(st, grow=0.2, depth=0.35)), z=[lo, hi], name=f"{k} · radiant manifold, {len(on)} loops",
                               text=f"{st['detail']} Loops {', '.join(l['id'] for l in on)}; {sum(l['gpm'] for l in on):.1f} gpm with all calling (R-1)."))
    feeds3d = [dict(id=f['id'], mf=f['mf'], pts=[list(p) for p in f['pts']], name=f"{f['id']} · 1\" feed pair to {f['to']}",
                    text=f"1\" PEX supply and return from HS-1, about {f['lf']:.0f}' each way, insulated, in the base course under the boards (R-1)") for f in feeds]
    hs3d = dict(id='HS-1', box=[33.0, 48.0, 33.9, 49.6], z=[2.5, 5.0], name='HS-1 · condensing boiler',
                text="Gas or propane condensing boiler for the slab, wall-hung on the mechanical closet's east wall over MF-2, with the four zone circulators P-R1 to P-R4, the garage mixing valve and the zone controller; circuit 27 (R-1)")
    stats3d = [dict(id=Z['stat'], at=list(STATS[Z['stat']]), color=Z['color'], name=f"{Z['stat']} · zone {z[1:]} thermostat", text=f"{Z['name']}: {Z['where']} (R-1)") for z, Z in ZONES.items()]
    foam3d = dict(z=[BOARD_Z[0], BOARD_Z[0] + BOARD['eps_in'] / 12], name=f"Boards · {BOARD['name']}, R-{BOARD['r']:.0f}", ref='Board',
                  text=f"{BOARD['thick_in']:.0f}\" nub boards under the whole slab: {BOARD['eps_in']:.0f}\" of EPS under a {BOARD['puck_in']:.0f}\" grid of pucks on {BOARD['pitch_in']:.0f}\" centres that hold the tube; 4\" of concrete over the pucks (R-1)")
    r3d = dict(slab_h=SLAB_H, feed_h=FEED_H, loops=loops3d, stations=stations3d, feeds=feeds3d, hs=hs3d, stats=stats3d, foam=foam3d)
    return dict(sheet=sh, picks=picks, tables=tables, notes=notes, open=open_items, summary=summary, legend=legend, r3d=r3d, loops=loops)
