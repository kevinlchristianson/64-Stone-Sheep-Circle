"""E-1 Electrical: devices on the walls, the switch plan, the circuit plan, panel P1 and the service load.

The owner's plan set has no electrical sheet, so this is the electrical
design: every device is placed by hand on a real wall face (or the ceiling)
of plan/house.json, room by room, to NEC 2023 and the usual builder layout:

- receptacles so no point along a wall is more than 6 ft from one (210.52(A)),
  kitchen counters at 4 ft spacing (210.52(C)), a GFCI within 3 ft of every
  lavatory, hall receptacles over 10 ft, one per garage bay, front and rear
  exterior receptacles and one within 25 ft of each outdoor unit (210.63)
- every light belongs to one switch leg, switched in the room it lights at the
  door you walk in through; 3-way / 4-way where a room has more than one way in
- circuits by room and load, panel P1 in the garage beside the mud room door
- smoke alarms in every sleeping room, smoke + CO outside each sleeping area

The drawing follows the 7824 Zero Rd E-1 format and symbols: receptacles R#
(orange), switches S# (brown discs), lights and fans L# (gold), alarms A#
(red), panels and equipment X#. Each wall device has a stem back to its wall.
Circuit sheets E-1.1 onward show one circuit with its cable run from P1.

Mounting heights here are the standard ones (receptacles 16", switches 48",
counters 44", vanities 40" to centre); Zero Rd's 30" / 42" were that owner's
accessibility choice, so they are an open item, not a format rule.
"""
import math
from setlib import HOUSE, ROOMS, Sheet, ft_in, centroid, bbox, esc, px, py, S as SC, MX, MY

ELEC, SWC, LITE, ALARM, LVC, DARK = '#c8650a', '#8a5a00', '#d9a400', '#b4462f', '#1f5f8b', '#333'
WIRE = {'240': ELEC, 'rec': ALARM, 'light': SWC, 'data': LVC}
STEM = 11.3          # px, symbol centre to wall face (Zero Rd)
ROOMNAME = {**{r['id']: r['name'] for r in HOUSE['rooms']}, 'outside': 'Outside'}

# ---------------------------------------------------------------- circuits on panel P1
# key, breaker, wire, load name, serves, kind (wire colour), VA (for the load calc)
CIRCUITS = [
    ('1-2', '240V 50A 2P', '#6 Cu', 'Range, 48" electric', 'kitchen, left wall', '240', 12000),
    ('3-4', '240V 30A 2P', '#10 Cu', 'Dryer', 'laundry', '240', 5000),
    ('5-6', '240V 20A 2P', '#12 Cu', 'Mini-split CU-1, 18k (master, dining heads)', 'left side yard, master closet wall; heads fed from the unit (MCA ~17A)', '240', 4080),
    ('7-8', '240V 40A 2P', '#8 Cu', 'Mini-split CU-2, 36k (bedrooms 1-3, living heads)', 'right side yard, bedroom 3 closet wall; heads fed from the unit (MCA ~28A, MOP 35-40A)', '240', 6720),
    ('9-10', '240V 50A 2P', '#6 Cu', 'EV-ready receptacle (NEMA 14-50)', 'garage, front wall', '240', 9600),
    ('11', '20A GFCI/AFCI', '#12', 'Kitchen small appliance 1', 'left counter run', 'rec', 1500),
    ('12', '20A GFCI/AFCI', '#12', 'Kitchen small appliance 2', 'island, front counter', 'rec', 1500),
    ('13', '20A GFCI/AFCI', '#12', 'Small appliance 3: dining + pantry', 'dining walls, pantry counter', 'rec', 1500),
    ('14', '20A AFCI', '#12', 'Refrigerator', 'kitchen, front wall', 'rec', 800),
    ('15', '20A GFCI/AFCI', '#12', 'Dishwasher', 'island', 'rec', 1200),
    ('16', '20A GFCI/AFCI', '#12', 'Disposal', 'island sink base', 'rec', 900),
    ('17', '15A AFCI', '#14', 'Range hood', 'over the range', 'rec', 400),
    ('18', '20A GFCI/AFCI', '#12', 'Laundry: washer + counter', 'laundry', 'rec', 1500),
    ('19', '20A GFCI', '#12', 'Bath receptacles west', 'master bath, powder', 'rec', 360),
    ('20', '20A GFCI', '#12', 'Bath receptacles east', 'bath 1, bath 2', 'rec', 360),
    ('21', '15A AFCI', '#14', 'Master suite receptacles', 'master bedroom, master closet', 'rec', 0),
    ('22', '15A AFCI', '#14', 'Living receptacles', 'living, TV wall, floor box, fireplace blower', 'rec', 200),
    ('23', '15A AFCI', '#14', 'Entry + office receptacles', 'entry, office', 'rec', 0),
    ('24', '15A AFCI', '#14', 'Bedroom 1 + hall receptacles', 'bedroom 1, bedroom hall', 'rec', 0),
    ('25', '15A AFCI', '#14', 'Bedroom 2 receptacles', 'bedroom 2', 'rec', 0),
    ('26', '15A AFCI', '#14', 'Bedroom 3 receptacles', 'bedroom 3', 'rec', 0),
    ('27', '20A GFCI/AFCI', '#12', 'Mud room receptacles', 'mud room', 'rec', 0),
    ('28', '20A GFCI', '#12', 'Garage receptacles', 'garage walls, one per bay', 'rec', 0),
    ('29', '20A GFCI', '#12', 'Garage door openers', 'two ceiling receptacles', 'rec', 1200),
    ('30', '20A GFCI', '#12', 'Exterior receptacles', 'porch, patio, both mini-split units', 'rec', 0),
    ('31', '15A AFCI', '#14', 'Boiler, circulators, zone controls', 'mechanical room, the three manifold stations (MF-1 laundry, MF-2/MF-G garage, MF-3 hall)', 'rec', 700),
    ('32', '15A AFCI', '#14', 'Water heater (power vent)', 'mechanical room', 'rec', 400),
    ('33', '15A AFCI', '#14', 'Lighting A', 'master suite, master hall, laundry, powder, mud room', 'light', 0),
    ('34', '15A AFCI', '#14', 'Lighting B', 'kitchen, dining, pantry, mech, living, entry, coat closet, porch, patio', 'light', 0),
    ('35', '15A AFCI', '#14', 'Lighting C + alarms', 'office, bedroom wing, baths, closets, every smoke and CO alarm', 'light', 0),
    ('36', '15A', '#14', 'Garage + garage exterior lights', 'garage, garage door and service door lights', 'light', 0),
    ('37', '15A AFCI', '#14', 'Media panel + low voltage', 'media panel in the pantry, doorbell transformer', 'rec', 300),
    ('38-40', '', '', 'Spare', 'three spaces', '', 0),
]
CKT = {c[0]: dict(key=c[0], breaker=c[1], wire=c[2], name=c[3], serves=c[4], kind=c[5], va=c[6]) for c in CIRCUITS}

# ---------------------------------------------------------------- switch legs: leg -> (what, room, control, note)
LEGS = {}


def leg(k, what, room, control, note=''):
    LEGS[k] = dict(what=what, room=room, control=control, note=note)


leg('mbed-cans', 'Master bedroom cans', 'master_bed', 'dimmer at the bedroom door, rocker 1 of 3', '')
leg('mbed-fan', 'Master bedroom fan box', 'master_bed', 'rocker 2 at the bedroom door; fan speed on the fan remote', 'fan-rated box for a ceiling fan with light kit')
leg('mhall', 'Master hall', 'master_hall', '3-way: kitchen opening and the bedroom door (rocker 3 of the bedroom bank is its partner on the hall side)', '')
leg('mbath-light', 'Master bath lights', 'master_bath', 'dimmer at the bath opening, rocker 1 of 3', 'cans, vanity lights and the fan units\' lights dim together')
leg('mbath-fan', 'Master bath fans', 'master_bath', 'rocker 2 with a 60-minute timer; humidity sensing runs them anyway', '')
leg('mbath-shower', 'Master shower and tub cans', 'master_bath', 'rocker 3 at the bath opening', 'wet-rated')
leg('mcloset', 'Master closet', 'master_closet', 'occupancy-sensor switch at the bath opening', 'closet-rated fixtures, 12" from shelves (410.16)')
leg('laundry', 'Laundry', 'laundry', 'switch at the laundry door, latch side', '')
leg('powder-light', 'Powder lights', 'powder', 'rocker 1 at the powder door', 'vanity light and the fan unit\'s light')
leg('powder-fan', 'Powder fan', 'powder', 'rocker 2 with a 20-minute timer', '')
leg('mud', 'Mud room cans', 'mud', '3-way: garage door and the kitchen opening', '')
leg('kit-cans', 'Kitchen cans', 'kitchen', '3-way dimmer: mud room opening and the master hall opening', 'sloped-ceiling trims under the 4:12 vault')
leg('kit-pend', 'Island pendants', 'kitchen', 'dimmer at the mud room opening, rocker 2', '')
leg('kit-ucl', 'Under-cabinet lights', 'kitchen', 'rocker 3 at the mud room opening', 'LED tape with a driver in the upper cabinet')
leg('dining', 'Dining chandelier', 'dining', 'dimmer on the dining wall at the kitchen end', '')
leg('pantry', 'Pantry', 'pantry', 'switch inside the pantry opening', '')
leg('mech', 'Mechanical room', 'mechanical', 'switch inside the door', '')
leg('living-cans', 'Living cans', 'living', '3 places: dimmer at the entry, 4-way at the patio doors, 3-way at the bedroom hall', 'sloped-ceiling trims under the 4:12 vault')
leg('living-fan', 'Living fan box', 'living', 'rocker 2 at the patio doors; fan speed on the fan remote', 'downrod sized for the 4:12 vault')
leg('entry', 'Entry light', 'entry', 'rocker at the front door', '')
leg('coat', 'Coat closet', 'coat', 'integral occupancy sensor, no switch', 'no wall space for a switch inside a 2 ft closet')
leg('porch', 'Porch cans and front door lights', 'porch', 'rocker at the front door; photocell or timer optional', 'wet-rated, dark-sky')
leg('patio-lights', 'Patio cans and door lights', 'patio', 'rocker 3 at the patio doors', 'wet-rated')
leg('patio-fan', 'Patio fan', 'patio', 'rocker 4 at the patio doors', 'wet-rated fan')
leg('office', 'Office cans', 'office', 'dimmer at the office doors', '')
leg('bhall', 'Bedroom hall cans', 'hall', '3-way: living end and bedroom 3 end', '')
for n, rm in (('1', 'bed1'), ('2', 'bed2'), ('3', 'bed3')):
    leg(f'bed{n}-light', f'Bedroom {n} light', rm, 'rocker 1 at the bedroom door (light kit on the fan)', '')
    leg(f'bed{n}-fan', f'Bedroom {n} fan', rm, 'rocker 2 at the bedroom door', 'fan-rated box')
    leg(f'bed{n}-closet', f'Bedroom {n} closet', f'bed{n}_closet', 'integral occupancy sensor, no switch', 'closet-rated, 12" from shelves (410.16)')
leg('bath1-light', 'Bath 1 lights', 'bath1', 'rocker 1 at the bath door', 'vanity light, shower can and the fan unit\'s light')
leg('bath1-fan', 'Bath 1 fan', 'bath1', 'rocker 2 with a 60-minute timer', '')
leg('bath2-light', 'Bath 2 lights', 'bath2', 'rocker 1 at the bath door', 'vanity lights, tub can and the fan unit\'s light')
leg('bath2-fan', 'Bath 2 fan', 'bath2', 'rocker 2 with a 60-minute timer', '')
leg('garage', 'Garage lights', 'garage', '3-way: service door and mud room door', '')
leg('garage-ext', 'Garage door and service door lights', 'outside', 'rocker 2 at the mud room door; photocell optional', 'dark-sky')


# ---------------------------------------------------------------- the device layout
DEV = []
NORMAL = {'rear': (0, 1), 'front': (0, -1), 'left': (1, 0), 'right': (-1, 0)}
WALLNAME = {v: k for k, v in NORMAL.items()}


def _add(kind, room, x, y, n, h, lg, ckt, legs=(), note='', legend='', **kw):
    DEV.append(dict(kind=kind, room=room, x=x, y=y, n=n, h=h, legend=legend or lg, ckt=ckt, legs=list(legs), note=note, **kw))
    return DEV[-1]


def wall(kind, room, side, a, h, lg, ckt, legs=(), note='', **kw):
    """On a rectangular room's wall face: side rear/front/left/right, a = the plan x (rear/front) or y (left/right)."""
    x0, y0, x1, y1 = bbox(ROOMS[room])
    x, y = {'rear': (a, y0), 'front': (a, y1), 'left': (x0, a), 'right': (x1, a)}[side]
    return _add(kind, room, x, y, NORMAL[side], h, lg, ckt, legs, note, **kw)


def at(kind, room, x, y, face, h, lg, ckt, legs=(), note='', **kw):
    """On a wall face at (x, y); face is the wall's name as seen from inside the room (rear/front/left/right)."""
    return _add(kind, room, x, y, NORMAL[face], h, lg, ckt, legs, note, **kw)


def ceil(kind, room, x, y, lg, ckt, legs=(), note='', h=None, **kw):
    return _add(kind, room, x, y, (0, 0), h, lg, ckt, legs, note, **kw)


REC, USB, GFCI, R20, R240, WP, FLOOR, TV, DATA, LV = 'rec', 'usb', 'gfci', 'r20', 'r240', 'wp', 'floor', 'tv', 'data', 'lv'
SW, SW3, SW4, DIM, OCC = 'sw', 'sw3', 'sw4', 'dim', 'occ'
CAN, WET, SURF, CLOSET, PEND, FANBOX, EF, EFL, SCONCE, STRIP, EXT, HOOD = 'can', 'wet', 'surf', 'closet', 'pend', 'fanbox', 'ef', 'efl', 'sconce', 'strip', 'ext', 'hood'
SMOKE, COMBO, PANEL, MP, DISC, METER = 'smoke', 'combo', 'panel', 'mp', 'disc', 'meter'
LEGEND = {
    REC: 'duplex receptacle, 15A, tamper-resistant', USB: 'duplex receptacle with USB-C, 15A', GFCI: 'GFCI receptacle, 20A', R20: 'receptacle, 20A dedicated',
    R240: '240V receptacle or junction', WP: 'weatherproof GFCI receptacle, in-use cover', FLOOR: 'floor box receptacle', TV: 'recessed TV box: power + 2 x Cat6',
    DATA: 'data outlet, 2 x Cat6', LV: 'low-voltage drop', SW: 'switch, rocker', SW3: '3-way switch, rocker', SW4: '4-way switch, rocker', DIM: 'dimmer, rocker',
    OCC: 'occupancy-sensor switch', CAN: '4" recessed LED, 2700K, IC, dimmable', WET: '4" recessed LED, wet location', SURF: 'surface LED ceiling fixture',
    CLOSET: 'surface LED, closet-rated (410.16), integral occupancy sensor', PEND: 'pendant', FANBOX: 'fan-rated ceiling box, switched', EF: 'exhaust fan, 110 CFM, humidity sensing',
    EFL: 'exhaust fan with integrated LED light, 110 CFM, humidity sensing', SCONCE: 'wall sconce / vanity light', STRIP: 'linear LED under cabinet', EXT: 'exterior LED, wet location, dark-sky',
    HOOD: 'range hood, ducted outside', SMOKE: 'smoke alarm, 120V interconnected w/ battery', COMBO: 'smoke + CO alarm, 120V interconnected w/ battery',
    PANEL: 'panel P1, 200A main breaker, 40 space', MP: 'media panel: Cat6 home runs, network switch', DISC: 'fused disconnect, within sight of the unit', METER: 'meter-main: utility meter + 200A service disconnect (230.85)',
}
H_REC, H_SW, H_CTR, H_VAN, H_CEIL = 16, 48, 44, 40, 108

# master bedroom: bed on the right (dining) wall, nightstand USB-C receptacles either side of it, TV opposite
wall(REC, 'master_bed', 'rear', 23.25, H_REC, '', '21')
wall(USB, 'master_bed', 'right', 4.3, H_REC, '', '21', note='nightstand')
wall(USB, 'master_bed', 'right', 12.7, H_REC, '', '21', note='nightstand')
wall(REC, 'master_bed', 'front', 21.0, H_REC, '', '21')
wall(REC, 'master_bed', 'left', 3.6, H_REC, '', '21')
wall(TV, 'master_bed', 'left', 8.5, 60, '', '21', note='TV facing the bed')
wall(DIM, 'master_bed', 'front', 25.7, H_SW, '', '33', ['mbed-cans', 'mbed-fan', 'mhall'], note='3-gang at the bedroom door, latch side of D8: cans (dimmer), fan box, master hall 3-way')
for x, y in ((19.5, 4.4), (27.5, 4.4), (19.5, 13.4), (27.5, 13.4)):
    ceil(CAN, 'master_bed', x, y, '', '33', ['mbed-cans'])
ceil(FANBOX, 'master_bed', 23.5, 9.6, '', '33', ['mbed-fan'], note='room centre, below the label')
ceil(SMOKE, 'master_bed', 20.6, 15.6, '', '35', note='over 3 ft from the fan blades')
# master hall
wall(SW3, 'master_hall', 'rear', 25.65, H_SW, '', '33', ['mhall'], note='hall side of the bedroom door')
wall(SW3, 'master_hall', 'front', 29.95, H_SW, '', '33', ['mhall'], note='at the kitchen opening')
ceil(CAN, 'master_hall', 28.6, 19.8, '', '33', ['mhall'])
ceil(COMBO, 'master_hall', 26.3, 19.8, '', '35', note='outside the master suite')
# master bath: vanity on the bedroom wall, WC top left, tub, shower bottom left
wall(GFCI, 'master_bath', 'right', 9.6, H_VAN, '', '19', note='between the two vanity sinks')
wall(SCONCE, 'master_bath', 'right', 7.6, 84, '', '33', ['mbath-light'], note='over the mirror at sink 1')
wall(SCONCE, 'master_bath', 'right', 11.6, 84, '', '33', ['mbath-light'], note='over the mirror at sink 2')
wall(DIM, 'master_bath', 'right', 17.85, H_SW, '', '33', ['mbath-light', 'mbath-fan', 'mbath-shower'], note='3-gang just inside the opening from the bedroom: lights (dimmer), fans, shower and tub cans')
ceil(CAN, 'master_bath', 12.0, 8.2, '', '33', ['mbath-light'])
ceil(CAN, 'master_bath', 12.0, 15.2, '', '33', ['mbath-light'])
ceil(CAN, 'master_bath', 13.0, 21.0, '', '33', ['mbath-light'])
ceil(WET, 'master_bath', 7.5, 13.8, '', '33', ['mbath-shower'], note='over the tub')
ceil(WET, 'master_bath', 7.8, 21.6, '', '33', ['mbath-shower'], note='in the shower')
ceil(EFL, 'master_bath', 8.4, 9.6, '', '33', ['mbath-light', 'mbath-fan'], note='toilet; the light dims with the room, the fan on rocker 2')
ceil(EFL, 'master_bath', 10.6, 18.6, '', '33', ['mbath-light', 'mbath-fan'], note='between the tub and the shower')
# master closet
wall(OCC, 'master_closet', 'rear', 15.0, H_SW, '', '33', ['mcloset'], note='inside the opening from the bath')
ceil(CLOSET, 'master_closet', 8.6, 29.4, '', '33', ['mcloset'])
ceil(CLOSET, 'master_closet', 13.3, 29.4, '', '33', ['mcloset'])
wall(REC, 'master_closet', 'front', 11.0, H_REC, '', '21', note='steamer, vacuum')
# laundry
wall(R20, 'laundry', 'right', 23.3, 42, '', '18', note='washer, behind the machine')
wall(R240, 'laundry', 'right', 20.6, 30, '', '3-4', note='dryer, NEMA 14-30R')
wall(GFCI, 'laundry', 'left', 24.4, H_CTR, '', '18', note='laundry counter')
wall(GFCI, 'laundry', 'left', 28.0, H_CTR, '', '18', note='laundry counter')
wall(SW, 'laundry', 'front', 22.6, H_SW, '', '33', ['laundry'], note='latch side of D12')
ceil(SURF, 'laundry', 20.6, 21.0, '', '33', ['laundry'])
ceil(SURF, 'laundry', 20.6, 27.0, '', '33', ['laundry'])
# powder
wall(GFCI, 'powder', 'left', 23.2, H_VAN, '', '19', note='beside the lav')
wall(SCONCE, 'powder', 'left', 25.0, 84, '', '33', ['powder-light'], note='over the mirror')
wall(SW, 'powder', 'front', 29.1, H_SW, '', '33', ['powder-light', 'powder-fan'], note='2-gang, latch side of D13: light, fan')
ceil(EFL, 'powder', 28.3, 25.1, '', '33', ['powder-light', 'powder-fan'])
# mud room (L-shaped)
at(REC, 'mud', 16.373, 33.5, 'left', H_REC, '', '27', note='bench')
at(REC, 'mud', 20.9, 36.84, 'front', H_REC, '', '27')
at(REC, 'mud', 25.44, 39.6, 'left', H_REC, '', '27')
at(REC, 'mud', 30.54, 32.0, 'right', H_REC, '', '27')
at(SW3, 'mud', 30.06, 42.213, 'front', H_SW, '', '33', ['mud'], note='at the garage door, latch side of D6')
at(SW3, 'mud', 30.54, 37.55, 'right', H_SW, '', '33', ['mud'], note='at the kitchen opening')
for x, y in ((19.6, 33.6), (27.8, 31.4), (27.8, 38.6)):
    ceil(CAN, 'mud', x, y, '', '33', ['mud'])
# kitchen: counter run on the left wall with the range, island with sink and dishwasher, fridge and counter on the front wall
for y in (24.2, 26.6, 32.8, 36.4):
    wall(GFCI, 'kitchen', 'left', y, H_CTR, '', '11', note='counter, 4 ft spacing')
wall(GFCI, 'kitchen', 'front', 34.6, H_CTR, '', '12', note='front counter')
at(GFCI, 'kitchen', 40.87, 28.2, 'left', 27, '', '12', note='island end panel, living side, below the counter edge', island=True)
at(GFCI, 'kitchen', 40.87, 33.4, 'left', 27, '', '12', note='island, living side, below the counter edge', island=True)
wall(R240, 'kitchen', 'left', 29.6, 6, '', '1-2', note='range receptacle behind the range, NEMA 14-50R')
wall(HOOD, 'kitchen', 'left', 29.6, 72, '', '17', note='hood over the range, ducted outside')
wall(R20, 'kitchen', 'front', 37.9, 48, '', '14', note='refrigerator, above the floor in the fridge recess')
ceil(R20, 'kitchen', 38.68, 25.6, '', '15', note='dishwasher, junction in the island sink base', h=12, island=True)
ceil(R20, 'kitchen', 38.68, 27.6, '', '16', note='disposal, switched receptacle in the sink base; air switch on the sink deck', h=12, island=True)
at(DIM, 'kitchen', 30.833, 42.4, 'left', H_SW, '', '34', ['kit-cans', 'kit-pend', 'kit-ucl'], note='3-gang beside the mud room opening: cans (3-way dimmer), pendants, under-cabinet')
at(DIM, 'kitchen', 30.833, 22.25, 'left', H_SW, '', '34', ['kit-cans'], note='3-way dimmer at the master hall opening')
for x, y in ((34.3, 19.6), (34.3, 24.6), (34.3, 34.6), (34.3, 39.8), (41.8, 19.6), (41.8, 24.6), (41.8, 36.6), (41.8, 41.6)):
    ceil(CAN, 'kitchen', x, y, '', '34', ['kit-cans'])
for y in (26.6, 30.6, 34.6):
    ceil(PEND, 'kitchen', 38.68, y, '', '34', ['kit-pend'], h=72, note='over the island')
at(STRIP, 'kitchen', 30.833, 25.3, 'left', 54, '', '34', ['kit-ucl'], note='under the uppers, left of the range', y0=23.1, y1=27.5)
at(STRIP, 'kitchen', 30.833, 34.85, 'left', 54, '', '34', ['kit-ucl'], note='under the uppers, right of the range', y0=31.7, y1=38.0)
# dining (receptacles on a small-appliance circuit, 210.11(C)(1))
wall(GFCI, 'dining', 'left', 8.4, H_REC, '', '13')
wall(GFCI, 'dining', 'left', 13.6, H_REC, '', '13')
wall(GFCI, 'dining', 'rear', 35.27, H_REC, '', '13', note='between the windows')
wall(GFCI, 'dining', 'rear', 39.1, H_REC, '', '13', note='between the windows')
wall(GFCI, 'dining', 'right', 10.37, H_REC, '', '13', note='between the windows')
wall(DIM, 'dining', 'left', 15.35, H_SW, '', '34', ['dining'], note='kitchen end of the dining wall')
ceil(PEND, 'dining', 37.27, 11.6, '', '34', ['dining'], h=78, note='chandelier over the table; 30" over the top')
# pantry and mechanical
wall(GFCI, 'pantry', 'right', 49.2, H_CTR, '', '13', note='pantry counter')
wall(GFCI, 'pantry', 'left', 47.4, H_CTR, '', '13', note='pantry counter')
wall(SW, 'pantry', 'rear', 41.85, H_SW, '', '34', ['pantry'], note='inside the opening')
ceil(CLOSET, 'pantry', 37.0, 49.2, '', '34', ['pantry'], legend='surface LED, closet-rated (410.16)')
ceil(CLOSET, 'pantry', 41.0, 49.2, '', '34', ['pantry'], legend='surface LED, closet-rated (410.16)')
wall(MP, 'pantry', 'left', 51.2, 54, '', '37', note='media panel on the mech room wall; every Cat6 home-runs here')
wall(R20, 'mechanical', 'right', 47.6, 54, '', '31', legend='boiler: 120V service switch + receptacle', note='heat source for the radiant slab (R-1)')
wall(REC, 'mechanical', 'right', 51.5, 54, '', '31', legend='duplex receptacle, 15A', note='circulators and zone control panel')
wall(R20, 'mechanical', 'right', 52.7, 54, '', '32', legend='water heater: 120V receptacle (power vent)', note='')
wall(SW, 'mechanical', 'rear', 31.35, H_SW, '', '34', ['mech'], note='inside the double doors')
ceil(SURF, 'mechanical', 32.37, 46.9, '', '34', ['mech'])
# radiant manifold stations (R-1): a receptacle at each for the actuator wiring module and its transformer
wall(REC, 'laundry', 'rear', 22.4, 24, '', '31', legend='duplex receptacle, 15A', note='radiant manifold MF-1 actuator module (R-1)')
at(GFCI, 'garage', 20.4, 37.13, 'rear', 48, '', '31', legend='GFCI receptacle, 15A', note='radiant manifolds MF-2 / MF-G actuator module and the garage circulator P-RG (R-1)')
wall(REC, 'hall', 'left', 27.4, 24, '', '31', legend='duplex receptacle, 15A', note='radiant manifold MF-3 actuator module (R-1)')
# living: open to the kitchen; patio doors on the rear wall, fireplace on the bedroom-hall wall
for x in (44.9, 49.8, 58.2, 63.0):
    wall(REC, 'living', 'rear', x, H_REC, '', '22')
for y in (18.5, 25.6, 35.2, 40.6):
    wall(REC, 'living', 'right', y, H_REC, '', '22')
wall(TV, 'living', 'right', 29.6, 66, '', '22', note='over the fireplace mantel')
wall(REC, 'living', 'right', 32.2, 8, '', '22', legend='duplex receptacle, 15A', note='fireplace insert blower, beside the insert')
wall(REC, 'living', 'front', 56.0, H_REC, '', '22')
wall(REC, 'living', 'front', 62.0, H_REC, '', '22')
ceil(FLOOR, 'living', 52.4, 34.0, '', '22', note='floor box under the sofa (confirm the furniture layout)', h=0)
wall(SW4, 'living', 'rear', 50.3, H_SW, '', '34', ['living-cans', 'living-fan', 'patio-lights', 'patio-fan'], note='4-gang beside the patio doors: living cans 4-way, living fan, patio lights, patio fan')
wall(SW3, 'living', 'right', 24.25, H_SW, '', '34', ['living-cans'], note='at the bedroom hall opening')
for x in (47.8, 54.0, 60.2):
    for y in (22.4, 37.0):
        ceil(CAN, 'living', x, y, '', '34', ['living-cans'])
ceil(FANBOX, 'living', 54.0, 31.4, '', '34', ['living-fan'], note='room centre, below the label')
# entry, coat closet, office
wall(REC, 'entry', 'left', 49.6, H_REC, '', '23')
wall(DIM, 'entry', 'right', 52.1, H_SW, '', '34', ['living-cans', 'entry', 'porch'], note='3-gang at the front door: living cans 3-way dimmer, entry light, porch lights')
ceil(SURF, 'entry', 47.55, 49.4, '', '34', ['entry'])
ceil(COMBO, 'entry', 48.8, 44.6, '', '35', note='outside the office (a possible bedroom)')
ceil(CLOSET, 'coat', 42.7, 44.3, '', '34', ['coat'])
for x in (54.6, 60.4):
    wall(REC, 'office', 'rear', x, H_REC, '', '23')
wall(REC, 'office', 'right', 47.0, H_REC, '', '23')
wall(DATA, 'office', 'right', 49.3, H_REC, '', '37', note='desk')
wall(REC, 'office', 'front', 54.2, H_REC, '', '23')
wall(REC, 'office', 'front', 62.6, H_REC, '', '23')
wall(DIM, 'office', 'left', 51.6, H_SW, '', '35', ['office'], note='inside the French doors')
for x in (54.6, 61.0):
    for y in (45.6, 50.4):
        ceil(CAN, 'office', x, y, '', '35', ['office'])
ceil(SMOKE, 'office', 57.8, 50.6, '', '35')
# bedroom hall
wall(REC, 'hall', 'left', 31.0, H_REC, '', '24', note='hall over 10 ft (210.52(H))')
wall(SW3, 'hall', 'left', 24.95, H_SW, '', '35', ['bhall'], note='living end, just past the opening')
wall(SW3, 'hall', 'left', 38.7, H_SW, '', '35', ['bhall'], note='bedroom 3 end')
for y in (22.0, 30.0, 36.4):
    ceil(CAN, 'hall', 66.5, y, '', '35', ['bhall'])
ceil(COMBO, 'hall', 66.5, 26.4, '', '35', note='outside the bedrooms')
# bedroom 1, bath 1
wall(REC, 'bed1', 'rear', 72.1, H_REC, '', '24', note='between the windows')
wall(REC, 'bed1', 'front', 69.5, H_REC, '', '24', note='2 ft wall space between the door and the closet (210.52(A)(2))')
wall(REC, 'bed1', 'left', 9.0, H_REC, '', '24')
wall(REC, 'bed1', 'left', 15.4, H_REC, '', '24')
wall(REC, 'bed1', 'right', 11.6, H_REC, '', '24')
wall(REC, 'bed1', 'right', 16.6, H_REC, '', '24')
wall(SW, 'bed1', 'front', 68.75, H_SW, '', '35', ['bed1-light', 'bed1-fan'], note='2-gang, latch side of D17: light, fan')
ceil(FANBOX, 'bed1', 71.0, 11.2, '', '35', ['bed1-light', 'bed1-fan'])
ceil(SMOKE, 'bed1', 74.8, 15.6, '', '35')
ceil(CLOSET, 'bed1_closet', 73.2, 20.23, '', '35', ['bed1-closet'])
wall(GFCI, 'bath1', 'right', 8.95, H_VAN, '', '20', note='between the lav and the toilet')
wall(SCONCE, 'bath1', 'right', 7.1, 84, '', '35', ['bath1-light'], note='over the mirror')
wall(SW, 'bath1', 'left', 9.3, H_SW, '', '35', ['bath1-light', 'bath1-fan'], note='2-gang, latch side of D19: lights, fan')
ceil(EFL, 'bath1', 80.0, 10.2, '', '35', ['bath1-light', 'bath1-fan'])
ceil(WET, 'bath1', 80.4, 14.2, '', '35', ['bath1-light'], note='in the shower')
# bedroom 2, bath 2
wall(REC, 'bed2', 'rear', 73.0, H_REC, '', '25')
wall(REC, 'bed2', 'right', 26.2, H_REC, '', '25', note='between the windows')
wall(REC, 'bed2', 'front', 74.2, H_REC, '', '25')
wall(REC, 'bed2', 'front', 80.0, H_REC, '', '25')
wall(REC, 'bed2', 'left', 25.6, H_REC, '', '25')
wall(SW, 'bed2', 'front', 69.45, H_SW, '', '35', ['bed2-light', 'bed2-fan'], note='2-gang in the corner, latch side of D21: light, fan')
ceil(FANBOX, 'bed2', 75.9, 27.2, '', '35', ['bed2-light', 'bed2-fan'])
ceil(SMOKE, 'bed2', 80.2, 31.6, '', '35')
ceil(CLOSET, 'bed2_closet', 80.4, 18.4, '', '35', ['bed2-closet'])
wall(GFCI, 'bath2', 'front', 72.85, H_VAN, '', '20', note='between the two sinks')
wall(SCONCE, 'bath2', 'front', 71.3, 84, '', '35', ['bath2-light'], note='over the mirror at sink 1')
wall(SCONCE, 'bath2', 'front', 74.4, 84, '', '35', ['bath2-light'], note='over the mirror at sink 2')
wall(SW, 'bath2', 'left', 37.85, H_SW, '', '35', ['bath2-light', 'bath2-fan'], note='2-gang, latch side of D22: lights, fan')
ceil(EFL, 'bath2', 76.6, 36.4, '', '35', ['bath2-light', 'bath2-fan'])
ceil(WET, 'bath2', 81.6, 37.2, '', '35', ['bath2-light'], note='over the tub')
# bedroom 3
wall(REC, 'bed3', 'rear', 72.5, H_REC, '', '26')
wall(REC, 'bed3', 'left', 45.5, H_REC, '', '26')
wall(REC, 'bed3', 'front', 67.0, H_REC, '', '26')
wall(REC, 'bed3', 'front', 75.5, H_REC, '', '26')
wall(REC, 'bed3', 'right', 49.0, H_REC, '', '26')
wall(SW, 'bed3', 'rear', 68.5, H_SW, '', '35', ['bed3-light', 'bed3-fan'], note='2-gang, latch side of D23: light, fan')
ceil(FANBOX, 'bed3', 70.96, 47.6, '', '35', ['bed3-light', 'bed3-fan'])
ceil(SMOKE, 'bed3', 75.2, 51.2, '', '35')
ceil(CLOSET, 'bed3_closet', 80.4, 42.8, '', '35', ['bed3-closet'])
# garage
at(PANEL, 'garage', 30.54, 44.6, 'right', 60, '', 'panel', note='beside the mud room door, 36" clear in front; fed from the meter-main outside')
at(GFCI, 'garage', 0.46, 52.1, 'left', 48, '', '28', note='between the garage doors')
at(GFCI, 'garage', 5.0, 67.13, 'front', 48, '', '28')
at(GFCI, 'garage', 22.8, 69.63, 'front', 48, '', '28')
at(GFCI, 'garage', 30.54, 59.0, 'right', 48, '', '28')
at(GFCI, 'garage', 11.0, 34.13, 'rear', 48, '', '28')
at(GFCI, 'garage', 25.15, 39.8, 'right', 48, '', '28', note='workbench')
at(R240, 'garage', 30.54, 66.4, 'right', 48, '', '9-10', legend='240V receptacle, NEMA 14-50R', note='EV-ready; swap for a hardwired charger if wanted')
ceil(GFCI, 'garage', 11.5, 45.63, '', '29', note='door opener 1, ceiling', h=H_CEIL)
ceil(GFCI, 'garage', 11.5, 58.63, '', '29', note='door opener 2, ceiling', h=H_CEIL)
at(SW3, 'garage', 5.15, 37.13, 'rear', H_SW, '', '36', ['garage'], note='inside the service door, latch side of D3')
at(SW3, 'garage', 29.95, 42.513, 'rear', H_SW, '', '36', ['garage', 'garage-ext'], note='2-gang at the mud room door: garage lights 3-way, garage door lights')
for x in (6.5, 18.0, 25.5):
    for y in (45.0, 60.0):
        ceil(SURF, 'garage', x, y, '', '36', ['garage'], legend='4 ft LED shop fixture')
# outside: meter-main, porch, patio, garage doors, mini-split disconnects
at(METER, 'outside', 30.54 + 0.46, 66.4, 'left', 60, '', 'panel', note='on the garage wall outside, beside the EV receptacle; utility service route to confirm')
for x in (36.0, 47.55, 58.0, 70.0):
    ceil(WET, 'porch', x, 58.0, '', '34', ['porch'], h=H_CEIL)
at(EXT, 'porch', 44.95, 53.73, 'rear', 72, '', '34', ['porch'], note='front door, left')
at(EXT, 'porch', 50.15, 53.73, 'rear', 72, '', '34', ['porch'], note='front door, right')
at(WP, 'porch', 39.8, 53.73, 'rear', 24, '', '30')
at(WP, 'porch', 63.0, 53.73, 'rear', 24, '', '30')
ceil(WET, 'patio', 48.5, 5.2, '', '34', ['patio-lights'], h=H_CEIL)
ceil(WET, 'patio', 59.7, 5.2, '', '34', ['patio-lights'], h=H_CEIL)
ceil(FANBOX, 'patio', 54.1, 9.0, '', '34', ['patio-fan'], legend='fan-rated ceiling box, wet location', h=H_CEIL)
at(EXT, 'patio', 50.35, 16.39, 'front', 72, '', '34', ['patio-lights'], note='patio doors, left')
at(EXT, 'patio', 57.65, 16.39, 'front', 72, '', '34', ['patio-lights'], note='patio doors, right')
at(WP, 'patio', 45.2, 16.39, 'front', 24, '', '30')
at(WP, 'patio', 63.0, 16.39, 'front', 24, '', '30')
at(EXT, 'outside', 5.15, 36.67, 'front', 78, '', '36', ['garage-ext'], note='service door')
for y in (39.1, 52.1, 65.1):
    at(EXT, 'outside', 0.0, y, 'right', 84, '', '36', ['garage-ext'], note='garage door coach light')
at(DISC, 'outside', 5.373, 31.6, 'right', 48, '', '5-6', legend='fused disconnect DS1, CU-1', note='left side yard, on the master closet wall beside the unit (M-1)')
at(WP, 'outside', 5.373, 25.6, 'right', 24, '', '30', note='service receptacle within 25 ft of CU-1 (210.63)')
at(DISC, 'outside', 83.44, 45.0, 'left', 48, '', '7-8', legend='fused disconnect DS2, CU-2', note='right side yard, on the bedroom 3 closet wall beside the unit (M-1)')
at(WP, 'outside', 83.44, 40.9, 'left', 24, '', '30', note='service receptacle within 25 ft of CU-2 (210.63)')
at(LV, 'outside', 50.9, 53.73, 'rear', 48, '', '37', legend='low-voltage drop: Cat6 for a video doorbell', note='right of the front door')

PREFIX = {REC: 'R', USB: 'R', GFCI: 'R', R20: 'R', R240: 'R', WP: 'R', FLOOR: 'R', TV: 'R', DATA: 'R', LV: 'X',
          SW: 'S', SW3: 'S', SW4: 'S', DIM: 'S', OCC: 'S',
          CAN: 'L', WET: 'L', SURF: 'L', CLOSET: 'L', PEND: 'L', FANBOX: 'L', EF: 'L', EFL: 'L', SCONCE: 'L', STRIP: 'L', EXT: 'L', HOOD: 'L',
          SMOKE: 'A', COMBO: 'A', PANEL: 'X', MP: 'X', DISC: 'X', METER: 'X'}
SWITCHES = (SW, SW3, SW4, DIM, OCC)
LIGHTS = (CAN, WET, SURF, CLOSET, PEND, FANBOX, EF, EFL, SCONCE, STRIP, EXT)
RECS = (REC, USB, GFCI, R20, R240, WP, FLOOR, TV)
NET = (TV, DATA, LV, MP)
# design watts for the lighting circuits (LED)
WATTS = {CAN: 9, WET: 10, SURF: 18, CLOSET: 12, PEND: 15, FANBOX: 75, EF: 20, EFL: 35, SCONCE: 20, STRIP: 24, EXT: 12, SMOKE: 2, COMBO: 2}


def number():
    seq = {}
    order = sorted(range(len(DEV)), key=lambda i: (PREFIX[DEV[i]['kind']] != 'X', 0))
    for d in DEV:
        p = PREFIX[d['kind']]; seq[p] = seq.get(p, 0) + 1; d['id'] = f'{p}{seq[p]}'
        if not d['legend']: d['legend'] = LEGEND[d['kind']]
        if d['kind'] in SWITCHES and d['legs'] and 'note' in d:
            pass


def where(d):
    """The tape position, Zero Rd style: which wall, how far along it from the nearer corner (or from two walls on the ceiling)."""
    x, y = d['x'], d['y']; nx, ny = d['n']
    if d['room'] in ('outside', 'porch', 'patio') and (nx or ny):
        side = {(0, 1): 'rear', (0, -1): 'front', (1, 0): 'left', (-1, 0): 'right'}[(nx, ny)]
        face = {'rear': 'front', 'front': 'rear', 'left': 'right', 'right': 'left'}[side] if d['room'] == 'outside' else side
        return f"outside, on the house wall, {ft_in(x)} from the garage-door wall, {ft_in(y)} from the master bedroom's rear wall"
    rm = ROOMS.get(d['room'])
    x0, y0, x1, y1 = bbox(rm) if rm else (0, 0, 84, 71)
    if not (nx or ny):
        dx = ('left', x - x0) if x - x0 <= x1 - x else ('right', x1 - x)
        dy = ('rear', y - y0) if y - y0 <= y1 - y else ('front', y1 - y)
        if d['room'] in ('porch', 'patio'): return f"porch/patio ceiling, {ft_in(x)} from the garage-door wall, {ft_in(y)} from the master bedroom's rear wall"
        return f"ceiling, {ft_in(dx[1])} from the {dx[0]} wall, {ft_in(dy[1])} from the {dy[0]} wall"
    side = WALLNAME[(nx, ny)]
    if ny:
        ref = ('left', x - x0) if x - x0 <= x1 - x else ('right', x1 - x)
    else:
        ref = ('rear', y - y0) if y - y0 <= y1 - y else ('front', y1 - y)
    return f"on the {side} wall, {ft_in(ref[1])} from the {ref[0]} wall"


# ---------------------------------------------------------------- symbols (Zero Rd E-1, in px around the symbol centre)
def symbol(sh, d):
    k = d['kind']; cx, cy = d['cx'], d['cy']; wx, wy = d['wx'], d['wy']
    out = []
    ln = lambda x0, y0, x1, y1, c, w, dash='': out.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="{c}" stroke-width="{w}"' + (f' stroke-dasharray="{dash}"' if dash else '') + '/>')
    cir = lambda r, f, s, w: out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{f}" stroke="{s}" stroke-width="{w}"/>')
    txt = lambda t, size, c, dy=0.0: out.append(f'<text x="{cx:.1f}" y="{cy + dy:.1f}" font-size="{size}" font-weight="700" fill="{c}" text-anchor="middle" dominant-baseline="middle">{esc(t)}</text>')
    rect = lambda w, h, f, s, sw: out.append(f'<rect x="{cx - w / 2:.1f}" y="{cy - h / 2:.1f}" width="{w}" height="{h}" fill="{f}" stroke="{s}" stroke-width="{sw}" rx="0"/>')
    tri = lambda c: out.append(f'<path d="M{cx - 6.3:.1f},{cy + 5.9:.1f} L{cx + 6.3:.1f},{cy + 5.9:.1f} L{cx:.1f},{cy - 6.0:.1f} Z" fill="#fff" stroke="{c}" stroke-width="1.1" stroke-linejoin="round" stroke-linecap="round"/>')
    stem = (wx is not None)
    if k in (REC, USB, GFCI, R20, R240, WP):
        cir(5.9, '#fff', ELEC, 1.1)
        if stem: ln(cx, cy, wx, wy, ELEC, 1.4)
        if k == REC:
            # two lines parallel to the wall
            tx, ty = (1, 0) if not stem or abs(wy - cy) > abs(wx - cx) else (0, 1)
            nx_, ny_ = ty, tx
            for o in (-1.7, 1.7):
                ln(cx - 7.7 * tx + o * nx_, cy - 7.7 * ty + o * ny_, cx + 7.7 * tx + o * nx_, cy + 7.7 * ty + o * ny_, ELEC, 0.9)
        else:
            t, s = {USB: ('U', 5.5), GFCI: ('G', 5.5), R20: ('20', 4.3), R240: ('240', 4.3), WP: ('WP', 4.3)}[k]
            txt(t, s, ELEC)
    elif k == FLOOR:
        rect(11.8, 11.8, '#fff', ELEC, 1.1); txt('F', 5.5, ELEC)
    elif k in (TV, DATA, LV):
        c = LVC if k == LV else ELEC
        tri(c); txt({TV: 'TV', DATA: 'D', LV: 'LV'}[k], 4.5 if k != LV else 4.2, c, dy=-1.8 + 0.6)
    elif k in SWITCHES:
        if stem: ln(cx, cy, wx, wy, SWC, 1.2)
        out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5.4" fill="{SWC}" stroke="#fff" stroke-width="0.8"/>')
        txt({SW: 'S', SW3: '3', SW4: '4', DIM: 'D', OCC: 'o'}[k], 6, '#fff', 0.2)
    elif k in (CAN, WET):
        cir(5.0, '#fff', LITE, 1.2); out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="1.4" fill="{LITE}" stroke="{LITE}" stroke-width="0"/>')
    elif k in (SURF, CLOSET):
        cir(5.0, '#fff', LITE, 1.2); ln(cx - 3.5, cy + 3.5, cx + 3.5, cy - 3.5, LITE, 1); ln(cx - 3.5, cy - 3.5, cx + 3.5, cy + 3.5, LITE, 1)
    elif k == PEND:
        out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4.2" fill="{LITE}" stroke="{LITE}" stroke-width="0"/>')
    elif k == FANBOX:
        cir(5.6, '#fff', LITE, 1.2); txt('F', 5.5, LITE)
    elif k in (EF, EFL):
        rect(11.2, 11.2, '#fff', LITE, 1.2); txt('EF' if k == EF else 'EFL', 4.5 if k == EF else 3.4, LITE)
    elif k == SCONCE:
        if stem: ln(cx, cy, wx, wy, LITE, 1.4)
        cir(4.2, '#fff', LITE, 1.2); txt('W', 4.5, LITE)
    elif k == EXT:
        if stem: ln(cx, cy, wx, wy, LITE, 1.4)
        cir(4.2, '#fff', LITE, 1.2); out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="1.4" fill="{LITE}" stroke="{LITE}" stroke-width="0"/>')
    elif k == STRIP:
        ln(d['sx0'], d['sy0'], d['sx1'], d['sy1'], LITE, 2.5, '5,2')
    elif k == HOOD:
        if stem: ln(cx, cy, wx, wy, LITE, 1.2)
        rect(11.2, 22.4, '#fff', LITE, 1.2); txt('HD', 4.5, LITE)
    elif k in (SMOKE, COMBO):
        cir(5.9, '#fff', ALARM, 1.3); txt('SD' if k == SMOKE else 'SC', 4.5, ALARM)
    elif k == PANEL:
        if stem: ln(cx, cy, wx, wy, DARK, 1.2)
        rect(8.4, 28.0, DARK, DARK, 1); out.append(f'<text x="{cx:.1f}" y="{cy:.1f}" font-size="6" font-weight="700" fill="#fff" text-anchor="middle" dominant-baseline="middle" transform="rotate(-90 {cx:.1f} {cy:.1f})">P1</text>')
    elif k == MP:
        if stem: ln(cx, cy, wx, wy, DARK, 1.2)
        rect(8.4, 19.6, '#fff', DARK, 1.2); out.append(f'<text x="{cx:.1f}" y="{cy:.1f}" font-size="5.5" font-weight="700" fill="{DARK}" text-anchor="middle" dominant-baseline="middle" transform="rotate(-90 {cx:.1f} {cy:.1f})">MP</text>')
    elif k in (DISC, METER):
        if stem: ln(cx, cy, wx, wy, DARK, 1.2)
        rect(14.0, 11.2, '#fff', DARK, 1.2); txt('DS' if k == DISC else 'M', 5.0, DARK)
    sh.add(''.join(out))


def lay_out():
    """Symbol centres: wall devices sit a stem's length into the room; then nudge apart anything closer than 13 px."""
    for d in DEV:
        wx, wy = px(d['x']), py(d['y']); nx, ny = d['n']
        if d['kind'] == STRIP:
            if nx:
                d['sx0'] = d['sx1'] = wx + nx * 4.7; d['sy0'], d['sy1'] = py(d['y0']), py(d['y1'])
            d['cx'], d['cy'], d['wx'], d['wy'] = d['sx0'], (d['sy0'] + d['sy1']) / 2, None, None
            continue
        if nx or ny:
            stem = STEM + (8 if d['kind'] == HOOD else 3 if d['kind'] in (PANEL, MP) else 0)
            d['cx'], d['cy'], d['wx'], d['wy'] = wx + nx * stem, wy + ny * stem, wx, wy
        else:
            d['cx'], d['cy'], d['wx'], d['wy'] = wx, wy, None, None
    # nudges, along the wall for wall devices; up to 20 passes. Room labels on the base drawing are fixed obstacles.
    pts = [d for d in DEV if d['kind'] != STRIP]
    R = lambda d: 14.5 if d['kind'] in (PANEL, MP, HOOD) else 6.2
    labels = []
    for r in HOUSE['rooms']:
        if r['area_sf'] < 12: continue
        cx, cy = centroid(r)
        cx, cy = {'mud': (21.0, 33.6), 'garage': (15.5, 52.0), 'kitchen': (34.8, 20.5)}.get(r['id'], (cx, cy))
        size = 7.5 if r['area_sf'] > 40 else 6
        w = len(r['name']) * size * 0.68 + 4; lx, ly = px(cx), py(cy - 0.5)
        labels.append((lx - w / 2, ly - size * 0.65, lx + w / 2, ly + size * 0.65))
    for _ in range(12):
        for d in pts:
            for x0, y0, x1, y1 in labels:
                r = R(d) + 0.5
                qx, qy = min(max(d['cx'], x0), x1), min(max(d['cy'], y0), y1)
                if math.hypot(d['cx'] - qx, d['cy'] - qy) >= r: continue
                nx, ny = d['n']
                if nx or ny:     # slide along the wall to the nearer end of the label
                    if ny: tgt = (x0 - r if d['cx'] < (x0 + x1) / 2 else x1 + r) - d['cx']; dx, dy = tgt, 0
                    else: tgt = (y0 - r if d['cy'] < (y0 + y1) / 2 else y1 + r) - d['cy']; dx, dy = 0, tgt
                else:            # ceiling: step off the label vertically
                    dx, dy = 0, (y0 - r if d['cy'] < (y0 + y1) / 2 else y1 + r) - d['cy']
                d['cx'] += dx; d['cy'] += dy
                if d['wx'] is not None: d['wx'] += dx; d['wy'] += dy
    for _ in range(20):
        moved = False
        for i, a in enumerate(pts):
            for b in pts[i + 1:]:
                dx, dy = b['cx'] - a['cx'], b['cy'] - a['cy']; dd = math.hypot(dx, dy); need = R(a) + R(b) + 0.6
                if dd >= need: continue
                push = (need - dd) / 2 + 0.05
                for d, s in ((a, -1), (b, 1)):
                    nx, ny = d['n']
                    if nx or ny:
                        tx, ty = (0, 1) if nx else (1, 0)
                        sgn = (dx * tx + dy * ty)
                        sgn = (1 if sgn >= 0 else -1) if abs(sgn) > 1e-6 else 1
                        d['cx'] += s * sgn * push * tx; d['cy'] += s * sgn * push * ty
                        if d['wx'] is not None: d['wx'] += s * sgn * push * tx; d['wy'] += s * sgn * push * ty
                    else:
                        u = (dx / dd, dy / dd) if dd > 1e-6 else (1, 0)
                        d['cx'] += s * push * u[0]; d['cy'] += s * push * u[1]
                moved = True
        if not moved: break
    for d in pts:
        if (d['cx'] - px(d['x'])) ** 2 + (d['cy'] - py(d['y'])) ** 2 > (STEM + 16) ** 2: print('E-1 symbol moved far from its device:', d['id'])


def check():
    """Every wall device on a real wall face of its room, clear of doors and openings; every ceiling device inside its room."""
    from setlib import inside
    bad = []
    for d in DEV:
        nx, ny = d['n']; rm = ROOMS.get(d['room'])
        if not (nx or ny):
            if rm and not inside(rm, d['x'], d['y']): bad.append((d['id'], 'ceiling device outside its room'))
            continue
        if d['room'] in ('outside', 'porch', 'patio') or d.get('island'):
            continue
        on = False
        p = rm['poly']
        for i in range(len(p)):
            (x0, y0), (x1, y1) = p[i], p[(i + 1) % len(p)]
            if abs(y0 - y1) < 1e-6 and ny and abs(d['y'] - y0) < 0.02 and min(x0, x1) - 0.01 <= d['x'] <= max(x0, x1) + 0.01: on = True
            if abs(x0 - x1) < 1e-6 and nx and abs(d['x'] - x0) < 0.02 and min(y0, y1) - 0.01 <= d['y'] <= max(y0, y1) + 0.01: on = True
        if not on: bad.append((d['id'], f'not on a wall face of {d["room"]}'))
        for o in HOUSE['doors'] + HOUSE['windows']:
            s0, s1 = o['span']
            if 'head' in o and d['h'] is not None and (d['h'] / 12 < o['sill'] or d['h'] / 12 > o['head']): continue
            if o.get('kind') == 'glass': continue
            t = 0.46 if (o.get('ext') or 'head' in o) else 0.293
            if o['axis'] == 'y' and ny and o['at'] - 0.05 <= d['y'] <= o['at'] + t + 0.05 and s0 - 0.25 < d['x'] < s1 + 0.25: bad.append((d['id'], f'in opening {o["id"]}'))
            if o['axis'] == 'x' and nx and o['at'] - 0.05 <= d['x'] <= o['at'] + t + 0.05 and s0 - 0.25 < d['y'] < s1 + 0.25: bad.append((d['id'], f'in opening {o["id"]}'))
    # the kitchen's and living's open sides are not walls
    for d in DEV:
        if d['room'] == 'living' and d['n'] == (1, 0): bad.append((d['id'], 'on the living room\'s open (kitchen) side'))
        if d['room'] == 'kitchen' and d['n'] == (-1, 0) and not d.get('island'): bad.append((d['id'], 'on the kitchen\'s open (living) side'))
        if d['room'] in ('kitchen',) and d['n'] == (0, 1): bad.append((d['id'], 'on the kitchen\'s open (dining) side'))
        if d['room'] == 'dining' and d['n'] == (0, -1): bad.append((d['id'], 'on the dining room\'s open (kitchen) side'))
        if d['room'] == 'living' and d['n'] == (0, -1) and 44.0 <= d['x'] <= 51.08: bad.append((d['id'], 'on the living room\'s open (entry) side'))
    return bad


def spacing_check():
    """210.52(A): in each wall space of the habitable rooms (walls broken at doorways and openings, carried round corners),
    no point more than 6 ft along the floor line from a receptacle in that space."""
    gaps = []
    for rid in ('master_bed', 'dining', 'living', 'office', 'bed1', 'bed2', 'bed3'):
        rm = ROOMS[rid]; p = rm['poly']
        per = []   # (x, y, side normal, in_opening)
        for i in range(len(p)):
            (x0, y0), (x1, y1) = p[i], p[(i + 1) % len(p)]
            n = max(1, int(math.hypot(x1 - x0, y1 - y0) / 0.25))
            for j in range(n):
                x, y = x0 + (x1 - x0) * j / n, y0 + (y1 - y0) * j / n
                per.append((x, y, i, opening_at(rid, x, y, x0 == x1)))
        recs = [d for d in DEV if d['room'] == rid and d['kind'] in (REC, USB, GFCI, TV) and d['n'] != (0, 0) and (d['h'] or 0) < 60 or (d['room'] == rid and d['kind'] == TV)]
        idx = [min(range(len(per)), key=lambda i: math.hypot(per[i][0] - r['x'], per[i][1] - r['y'])) for r in recs]
        N = len(per)
        # start the walk at an opening so runs do not wrap
        start = next((i for i in range(N) if per[i][3]), 0)
        runs, cur = [], []
        for k in range(N):
            i = (start + k) % N
            if per[i][3]:
                if cur: runs.append(cur); cur = []
            else: cur.append(i)
        if cur: runs.append(cur)
        worst = 0
        for run in runs:
            if len(run) * 0.25 < 2.0: continue     # wall spaces under 2 ft need none
            pos = {i: 0.25 * j for j, i in enumerate(run)}
            rr = [pos[i] for i in idx if i in pos]
            for i in run:
                dmin = min((abs(pos[i] - t) for t in rr), default=99)
                worst = max(worst, dmin)
                if dmin > 6.05: gaps.append((rid, round(per[i][0], 1), round(per[i][1], 1), round(dmin, 1))); break
    return gaps


def opening_at(rid, x, y, vertical):
    """True where the room's boundary is a door, an opening or an open side (not wall space)."""
    for o in HOUSE['doors']:
        if o['kind'] == 'glass': continue
        t = 0.46 if o.get('ext') else 0.293
        s0, s1 = o['span']
        if o['axis'] == 'y' and not vertical and o['at'] - 0.05 <= y <= o['at'] + t + 0.05 and s0 <= x <= s1: return True
        if o['axis'] == 'x' and vertical and o['at'] - 0.05 <= x <= o['at'] + t + 0.05 and s0 <= y <= s1: return True
    if rid == 'living' and vertical and abs(x - 43.707) < 0.05: return True
    if rid == 'living' and not vertical and abs(y - 42.48) < 0.05 and 44.0 <= x <= 51.08: return True
    if rid == 'dining' and not vertical and abs(y - 16.12) < 0.05: return True
    return False


def build():
    number()
    bad = check()
    for b in bad: print('E-1 placement:', *b)
    for g in spacing_check(): print('E-1 210.52(A) gap (room, x, y, ft):', *g)
    lay_out()
    sh = Sheet('E-1', 'Electrical', 'Devices, switch legs and circuits for panel P1, drawn on the walls they go in.')
    sh.base()
    sh.add('<style>.wire{display:none}</style>', 'page')
    # cable runs: from P1 through every device on the circuit, nearest neighbour first (Zero Rd)
    panel = next(d for d in DEV if d['kind'] == PANEL)
    for key, c in CKT.items():
        devs = [d for d in DEV if d['ckt'] == key]
        if not devs: continue
        chain, cur, left = [], (panel['cx'], panel['cy']), devs[:]
        while left:
            nxt = min(left, key=lambda d: math.hypot(d['cx'] - cur[0], d['cy'] - cur[1])); left.remove(nxt)
            chain.append((cur, (nxt['cx'], nxt['cy']))); cur = (nxt['cx'], nxt['cy'])
        segs = []
        for (ax, ay), (bx, by) in chain:
            mx, my = (ax + bx) / 2, (ay + by) / 2; L = math.hypot(bx - ax, by - ay) or 1
            qx, qy = mx - (by - ay) / L * L * 0.12, my + (bx - ax) / L * L * 0.12
            dash = ' stroke-dasharray="4,2"' if c['kind'] == 'light' else ''
            segs.append(f'<path d="M{ax:.1f},{ay:.1f}Q{qx:.1f},{qy:.1f} {bx:.1f},{by:.1f}" fill="none" stroke="{WIRE[c["kind"]]}" stroke-width="1.1" stroke-linecap="round"{dash}/>')
        sh.add(f'<g class="wire" data-ckt="{key}">' + ''.join(segs) + '</g>', 'disc')
    # data: home runs to the media panel
    mp = next(d for d in DEV if d['kind'] == MP)
    runs = [f'<path d="M{mp["cx"]:.1f},{mp["cy"]:.1f}L{d["cx"]:.1f},{d["cy"]:.1f}" fill="none" stroke="{LVC}" stroke-width="0.9" stroke-dasharray="2,3" stroke-linecap="round"/>' for d in DEV if d['kind'] in (TV, DATA, LV)]
    sh.add('<g class="wire" data-ckt="data">' + ''.join(runs) + '</g>', 'disc')
    # devices: ceiling first, then walls, then switches on top
    for d in sorted(DEV, key=lambda d: (d['kind'] in SWITCHES, d['n'] != (0, 0))):
        c = CKT.get(d['ckt'])
        txt = f"{d['id']} {d['legend']}" + (f", {d['h']}\" AFF" if d['h'] else '') + (f", circuit {d['ckt']}" if c else '') + (f" — {d['note']}" if d['note'] else '') + f" ({where(d)})"
        attrs = f' data-ckt="{d["ckt"]}"' + (f' data-leg="{" ".join(d["legs"])}"' if d['legs'] else '') + (' data-net="1"' if d['kind'] in NET else '')
        sh.add(f'<g id="e1-{d["id"]}" class="sym" data-id="{d["id"]}"{attrs}><title>{esc(txt)}</title>'
               f'<circle class="hit" cx="{d["cx"]:.1f}" cy="{d["cy"]:.1f}" r="11.2" fill="#fff" fill-opacity="0" pointer-events="all"/>', 'disc')
        symbol(sh, d)
        sh.add('</g>', 'disc')

    # ---- tables
    picks = {}
    dev_rows = []
    for d in DEV:
        c = CKT.get(d['ckt'])
        rm = ROOMNAME.get(d['room'], d['room'])
        aff = (f"{d['h']}\"" if d['h'] is not None and d['h'] < 100 else 'ceiling' if d['h'] is None or d['h'] >= 100 else '')
        if d['kind'] in LIGHTS + (SMOKE, COMBO) and d['h'] is None: aff = 'ceiling'
        if d['kind'] == FLOOR: aff = 'floor'
        ck = d['ckt'] if c else ('—' if d['ckt'] != 'panel' else 'P1')
        note = d['note'] + (f"; legs {', '.join(d['legs'])}" if d['legs'] and d['kind'] in SWITCHES else '')
        dev_rows.append((d['id'], [d['id'], d['legend'], f"{rm}: {where(d)}", aff, ck, note]))
        fields = [('Device', d['legend']), ('Room', rm), ('Position', where(d)), ('Height', aff)]
        if c: fields.append(('Circuit', f"{d['ckt']}: {c['name']} ({c['breaker']}, {c['wire']})"))
        if d['legs']: fields.append(('Switch legs', ', '.join(f"{l} ({LEGS[l]['what']})" for l in d['legs'])))
        if d['note']: fields.append(('Note', d['note']))
        picks[d['id']] = dict(tag=d['id'], sub=rm, fields=fields, ckt=d['ckt'] if c else None, legs=d['legs'])
    ckt_rows = []
    for key, c in CKT.items():
        devs = [d for d in DEV if d['ckt'] == key]
        if c['kind'] == 'light':
            w = sum(WATTS.get(d['kind'], 0) for d in devs)
            serves = f"{c['serves']} (~{w} W LED at design wattages)"
            c['va'] = w
        else:
            serves = c['serves']
        ckt_rows.append((f'C{key}', [key, c['name'], c['breaker'] or '—', c['wire'] or '—', serves, str(len(devs))]))
    leg_rows = []
    for k, l in LEGS.items():
        sws = [d for d in DEV if k in d['legs'] and d['kind'] in SWITCHES]
        lts = [d for d in DEV if k in d['legs'] and d['kind'] not in SWITCHES]
        if not lts: print('E-1 leg with no lights:', k)
        sw = '; '.join(f"{d['id']} {d['legend'].split(',')[0]}" for d in sws) or '—'
        leg_rows.append((f'LEG:{k}', [k, l['what'], ROOMNAME.get(l['room'], l['room']), sw, ', '.join(d['id'] for d in lts), l['control'], l['note']]))
        for d in lts:
            if CKT.get(d['ckt']) and sws and any(s['ckt'] != d['ckt'] for s in sws): print('E-1 leg on two circuits:', k)
    for d in DEV:
        if d['kind'] in LIGHTS and not d['legs']: print('E-1 light with no leg:', d['id'])
        if d['ckt'] not in CKT and d['ckt'] != 'panel': print('E-1 unknown circuit:', d['id'], d['ckt'])

    # ---- service load, NEC 220.82 (dwelling, optional method)
    sq = HOUSE['totals']['heated_gross_sf']
    fixed = ['1-2', '3-4', '9-10', '14', '15', '16', '17', '29', '31', '32', '37']
    appl = sum(CKT[k]['va'] for k in fixed)
    general = 3 * sq + 3 * 1500 + 1500
    other = general + appl
    demand = 10000 + 0.4 * (other - 10000)
    hvac = CKT['5-6']['va'] + CKT['7-8']['va']
    total = demand + hvac; amps = total / 240
    load_rows = [
        (None, ['General lighting and receptacles', f'3 VA x {sq:,} sf', f'{3 * sq:,} VA']),
        (None, ['Small-appliance circuits', '3 x 1,500 VA (11, 12, 13)', '4,500 VA']),
        (None, ['Laundry circuit', '1 x 1,500 VA (18)', '1,500 VA']),
        (None, ['Fixed appliances, nameplate', 'range, dryer, EV-ready, fridge, DW, disposal, hood, openers, boiler, water heater, media', f'{appl:,} VA']),
        (None, ['All other load, demand', 'first 10 kVA at 100%, rest at 40% (220.82(B))', f'{demand:,.0f} VA']),
        (None, ['Heating / cooling', 'two mini-split outdoor units at 100% (220.82(C)); radiant boiler is gas', f'{hvac:,} VA']),
        (None, ['Calculated load', f'{total:,.0f} VA / 240 V', f'{amps:,.0f} A on a 200 A service']),
    ]
    spaces = sum(2 if '-' in k and k != '38-40' else 3 if k == '38-40' else 1 for k in CKT)
    notes = [
        'Panel P1, 200A main breaker, 40 spaces, in the garage on the mud room wall beside D6, 60" to centre, 36" clear in front (110.26). It sits next to the mechanical room (boiler, water heater) and the kitchen, the two heaviest groups of circuits. A meter-main outside on the garage\'s porch-side wall carries the service disconnect (NEC 2023 230.85 emergency disconnect) and feeds P1 with 4-wire 2/0 Al SER (or #2/0 Al in conduit), neutral isolated in P1.',
        'Code basis: NEC 2023 (confirm the edition Powell / Park County enforces). AFCI on every 120V 15A and 20A branch circuit in the house except the bath receptacle circuits and the garage and exterior circuits (210.12); GFCI in baths, kitchen counters and island, dishwasher, disposal, laundry, garage, outdoors, and within 6 ft of any sink (210.8). Tamper-resistant receptacles throughout (406.12).',
        'Positions: every wall device is drawn on the face of the wall it goes in, with its stem to that wall; the schedule gives the wall and the distance from the nearer corner. Ceiling devices give two distances. Final boxes are set to the studs at the owner walk-through.',
        'Mounting heights (standard): receptacles 16" to centre, switches 48", counter and laundry GFCIs 44", vanity GFCIs 40", vanity lights 84", exterior lights 72" or 84".',
        'Switch plan: every light belongs to one switch leg (table below), switched in the room it lights, at the latch side of the door you walk in through. Rooms with two ways in get 3-ways: the master hall, mud room, kitchen, bedroom hall and garage; the living cans have three control points (entry dimmer, 4-way at the patio doors, 3-way at the bedroom hall). A switch tag that appears in several legs is a multi-gang bank, one rocker per leg. On the page, picking a light or switch lights every device on its legs in blue.',
        'Circuit sheets E-1.1 onward show one circuit each with its cable run drawn from P1 through every device in nearest-neighbour order (solid for receptacle and appliance circuits, dashed for lighting). The run is a proposed order, not a required one. E-1.D shows the Cat6 home runs to the media panel.',
        'Kitchen: three 20A small-appliance circuits (11 left counter, 12 island and front counter, 13 dining and pantry, 210.11(C)(1)), counter receptacles at 4 ft spacing (210.52(C)); range, refrigerator, dishwasher, disposal and hood each on their own circuit. The island has a receptacle in each end panel on the living side, below the counter edge. Kitchen and living ceilings are vaulted 4:12: sloped-ceiling can trims and a fan downrod sized for the slope.',
        'Lighting circuits by area, whole switch legs only: 33 master suite, master hall, laundry, powder, mud room; 34 kitchen, dining, pantry, mech room, living, entry, coat closet, porch and patio; 35 office, bedroom wing and every smoke and CO alarm (so a tripped alarm circuit shows as dark lights). Garage and garage exterior lights on 36. Each is well under the 1,440 W continuous limit of a 15A circuit at LED design wattages.',
        'Smoke alarms in every bedroom and the office; smoke + CO combination alarms outside each sleeping area (master hall, bedroom hall, entry outside the office). All 120V, interconnected, battery backup (IRC R314, R315; CO because of the attached garage, the wood fireplace and the gas boiler).',
        'Bath exhaust fans 110 CFM with humidity sensing and an integrated LED light: the light switches with the room\'s other lights, the fan on its own rocker with a timer (14/3 from the bank). Ducted outside in rigid duct.',
        'Mini-splits: each outdoor unit has its own 2-pole circuit and a fused disconnect within sight; the indoor heads are fed from their outdoor unit through the interconnect cable, so they have no circuits of their own. CU-1 (18k) sits in the left side yard on the master closet wall and CU-2 (36k) in the right side yard behind the bedroom 3 closet, per M-1; breakers are sized from the nominal units until the nameplates are known. A weatherproof GFCI receptacle is within 25 ft of each outdoor unit (210.63).',
        'Radiant (R-1): the wall-hung boiler HS-1, its system circulator and the zone controller share 15A circuit 31 with a service switch at the boiler, and each remote manifold station has a receptacle on 31 for its actuator wiring module (MF-1 laundry, MF-2/MF-G on the garage side of the mud room wall with the garage circulator, MF-3 bedroom hall). The water heater\'s power vent is on 32. Thermostats are 24V back to the zone controller, not line voltage. The MF-3 cabinet sits below the hall 3-way S at 48".',
        'Low voltage: Cat6 home runs to the media panel on the pantry\'s mech-room wall (master and living TV boxes, office desk, video doorbell at the front door), powered from circuit 37.',
    ]
    open_items = [
        'Boiler and water heater fuel: gas or propane is drawn (200A service). An electric boiler or air-to-water heat pump with an electric water heater adds about 80-120A and needs a 320/400A service.',
        'Range fuel: the 48" range is drawn electric on a 50A circuit. A gas or dual-fuel range drops that to a 120V receptacle and adds a gas line.',
        'Mini-split breakers are sized from M-1\'s nominal units (CU-1 18k on 20A/#12, CU-2 36k on 40A/#8; 30A/#10 if the chosen model\'s MOP allows); set them to the nameplate MCA/MOCP of the units bought. If the living head moves to CU-1, CU-1 grows and 5-6 goes to 25-30A.',
        'Utility service: overhead or underground, and which side of the house the meter goes on. The meter-main is drawn on the garage wall facing the porch end.',
        'EV-ready: a 50A NEMA 14-50 receptacle is drawn in the garage. Keep, swap for a hardwired charger, or drop?',
        'Mounting heights: standard heights are drawn. Zero Rd used 30" receptacles and 42" switches for accessibility; say if this house should match.',
        'Ceiling fans in the master, living, three bedrooms and the patio: keep the fan-rated boxes, or cans instead?',
        'Low voltage: TVs in the bedrooms, ceiling Wi-Fi access points, cameras, and whether the media panel should move out of the pantry.',
    ]
    sh.title_block(['Receptacles R, switches S, lights and fans L, alarms A, panels and equipment X.', 'Pick a device for its circuit and switch legs; pick a circuit tab to see one circuit and its run from P1.',
                    f'Panel P1 in the garage. Calculated load {amps:,.0f} A on a 200 A service.'])
    legend_block(sh)
    tables = [
        dict(key='circuits', title='Circuit schedule, panel P1', feed='P1: 200A main-breaker panel, 40 spaces, in the garage beside the mud room door, fed from the meter-main outside. Circuit numbers are the panel spaces; two-pole circuits take two.',
             cols=['Ckt', 'Load', 'Breaker', 'Wire', 'Serves', 'Devices'], rows=ckt_rows),
        dict(key='legs', title='Switch plan', lede='One row per switch leg. Pick a row to light up its switch and lights on the drawing.', cols=['Leg', 'What', 'Room', 'Switch(es)', 'Lights', 'Control', 'Notes'], rows=leg_rows),
        dict(key='devices', title='Device schedule', cols=['Tag', 'Device', 'Position', 'AFF', 'Circuit', 'Notes'], rows=dev_rows),
        dict(key='load', title='Service load calculation (NEC 220.82)', cols=['Item', 'Basis', 'Load'], rows=load_rows),
    ]
    count = lambda ks: sum(1 for d in DEV if d['kind'] in ks)
    used = [k for k in CKT if CKT[k]['kind']]
    summary = dict(devices=len(DEV), circuits=len(used), spaces=spaces, amps=round(amps), receptacles=count(RECS + (WP,)), lights=count(LIGHTS), switches=count(SWITCHES))
    bom = [(None, ['Duplex receptacles, TR', str(count((REC,))), '15A, with boxes']),
           (None, ['Duplex + USB-C receptacles', str(count((USB,))), 'nightstands']),
           (None, ['GFCI receptacles, 20A', str(count((GFCI,))), 'kitchen, dining, baths, laundry, pantry, garage']),
           (None, ['Weatherproof GFCI receptacles', str(count((WP,))), 'in-use covers']),
           (None, ['Dedicated / 240V receptacles', str(count((R20, R240))), 'washer, fridge, DW, disposal, boiler, water heater, range 14-50, dryer 14-30, EV 14-50']),
           (None, ['Floor box', str(count((FLOOR,))), 'living']),
           (None, ['Switches and dimmers', str(count(SWITCHES)), 'single-pole, 3-way, 4-way, dimmers, one occupancy sensor; gangs per the switch plan']),
           (None, ['Recessed LED cans', str(count((CAN, WET))), '4", 2700K; sloped trims in the kitchen and living, wet-rated in showers, tubs, porch and patio']),
           (None, ['Surface / closet fixtures', str(count((SURF, CLOSET))), 'closet-rated with occupancy sensors in the small closets; 4 ft LED shop fixtures in the garage']),
           (None, ['Pendants and chandelier', str(count((PEND,))), 'island and dining']),
           (None, ['Vanity lights and exterior lights', str(count((SCONCE, EXT))), 'exterior dark-sky']),
           (None, ['Fan-rated boxes', str(count((FANBOX,))), 'master, living, three bedrooms, patio']),
           (None, ['Bath exhaust fans', str(count((EF, EFL))), '110 CFM, humidity sensing, integrated light']),
           (None, ['Smoke and smoke + CO alarms', str(count((SMOKE, COMBO))), 'hardwired, interconnected']),
           (None, ['Panel and meter-main', '1 + 1', '200A, 40 spaces, AFCI/GFCI breakers per the schedule; meter-main with the 230.85 disconnect']),
           (None, ['Fused disconnects', str(count((DISC,))), 'one per mini-split outdoor unit']),
           (None, ['Media panel, Cat6', '1', f"{count((TV, DATA, LV))} drops, ~{count((TV, DATA, LV)) * 55} ft of Cat6 (2 per TV box and desk)"]),
           (None, ['NM-B 14/2, 14/3, 12/2, 10/3, 6/3', f"~{round(len(DEV) * 24 / 250) * 250:,} ft", 'rough order from the device count (about 24 ft per device)'])]
    tables.append(dict(key='bom', title='Bill of materials', lede='Rough-order quantities from the device layout, for pricing. The electrician takes off the final list.', cols=['Item', 'Qty', 'Notes'], rows=bom))
    for t in tables:
        for rid, cells in t['rows']:
            if rid and rid.startswith(('C', 'LEG:')) and t['key'] in ('circuits', 'legs'):
                picks[rid] = None
    picks = {k: v for k, v in picks.items() if v}
    tabs = [k for k in CKT if CKT[k]['kind'] and any(d['ckt'] == k for d in DEV)]
    subtabs = ('<div class="subtabs" id="ckt-tabs" role="group" aria-label="Circuit sheets"><button type="button" data-ckt="all" aria-pressed="true">E-1 all</button>'
               + ''.join(f'<button type="button" data-ckt="{k}" aria-pressed="false" title="{esc(CKT[k]["name"])}, {esc(CKT[k]["breaker"])}">E-1.{i} <span>{k}</span></button>' for i, k in enumerate(tabs, 1))
               + '<button type="button" data-ckt="data" aria-pressed="false" title="Cat6 home runs to the media panel">E-1.D <span>data</span></button></div>'
               + '<p class="ckt-name" id="ckt-name">All circuits. Pick a circuit sheet to see just its devices and the cable run from P1.</p>')
    return dict(sheet=sh, picks=picks, tables=tables, notes=notes, open=open_items, summary=summary, subtabs_html=subtabs,
                legend=[('#c8650a', 'Receptacles R'), ('#8a5a00', 'Switches S'), ('#d9a400', 'Lights and fans L'), ('#b4462f', 'Alarms A'), ('#1f5f8b', 'Low voltage / Cat6'), ('#333333', 'Panels and equipment X')],
                load=dict(sq=sq, general=general, appl=appl, demand=round(demand), hvac=hvac, total=round(total), amps=round(amps)),
                circuits=[dict(n=k, name=c['name'], breaker=c['breaker']) for k, c in CKT.items()],
                devices=devices3d())


def legend_block(sh):
    """The Zero Rd symbol legend in the strip under the plan, drawn with the same symbols as the sheet."""
    rows = [(REC, 'duplex receptacle'), (GFCI, 'GFCI'), (USB, 'duplex + USB-C'), (R20, '20A dedicated'), (R240, '240V'), (WP, 'weatherproof GFCI'),
            (TV, 'TV box / Cat6'), (SW, 'switch S / 3 / 4 / D dimmer / o occupancy'), (CAN, 'recessed LED'), (SURF, 'surface / closet LED'), (PEND, 'pendant'),
            (FANBOX, 'fan-rated box'), (EFL, 'exhaust fan (+ light)'), (SCONCE, 'vanity light / sconce'), (EXT, 'exterior light'), (COMBO, 'smoke SD / smoke+CO SC'),
            (PANEL, 'panel P1'), (DISC, 'disconnect DS / meter M')]
    items = []
    for k, label in rows:
        tmp = Sheet('X', 'x'); symbol(tmp, dict(kind=k, cx=0, cy=0, wx=None, wy=None))
        items.append((''.join(x.replace('rotate(-90', 'rotate(0') if k == PANEL else x for x in tmp.L['disc']), label))
    sh.legend(items)


def devices3d():
    """Zero Rd's set-data electrical.devices shape: id, type, x, y, side, h (inches), ckt, legend, note."""
    T = {REC: 'rec', USB: 'rec', GFCI: 'rec', R20: 'rec', R240: 'rec', WP: 'rec', FLOOR: 'floor', TV: 'tv', DATA: 'data', LV: 'lv',
         SW: 'sw', SW3: 'sw3', SW4: 'sw3', DIM: 'dim', OCC: 'occ', CAN: 'can', WET: 'wet', SURF: 'surf', CLOSET: 'closet', PEND: 'pend', FANBOX: 'fanbox',
         EF: 'ef', EFL: 'ef', SCONCE: 'sconce', STRIP: 'strip', EXT: 'ext', HOOD: 'hood', SMOKE: 'smoke', COMBO: 'combo', PANEL: 'panel', MP: 'panel', DISC: 'panel', METER: 'panel'}
    out = []
    for d in DEV:
        side = {(0, 1): 'rear', (0, -1): 'front', (1, 0): 'left', (-1, 0): 'right', (0, 0): 'c'}[d['n']]
        e = dict(id=d['id'], type=T[d['kind']], x=round(d['x'], 3), y=round(d['y'], 3), side=side, h=d['h'] if d['h'] is not None else H_CEIL,
                 ckt=d['ckt'] if d['ckt'] in CKT else '', legend=d['legend'], note=d['note'], legs=d['legs'])
        if d['kind'] == STRIP: e.update(len=round(d['y1'] - d['y0'], 2), y0=round(d['y0'], 3), y1=round(d['y1'], 3))
        if d['kind'] in (MP, DISC, METER): e['part'] = d['kind']
        if d['kind'] == PEND: e['room'] = d['room']
        out.append(e)
    return out


if __name__ == '__main__':
    b = build()
    print(b['summary'], b['load'])
