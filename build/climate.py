"""Design climate and envelope assumptions, in one place.

The plans don't say where 64 Stone Sheep Circle is. Until that's confirmed
these are Casper, WY values (ASHRAE 2009 design conditions for Casper Natrona
Co Intl AP, WMO 725690, the same station as data/casper-tmy3.json in the
Property App). Change LOCATION here and rerun build.py; M-1 and the Property
App's energy model both read these.
"""

CLIMATE = dict(
    name='Casper, WY (assumed)',
    source='ASHRAE 2009, Casper Natrona Co Intl AP, 99.6 % heating / 1 % cooling',
    heat_design_f=-10.3,
    cool_design_f=89.6,
    indoor_heat_f=70,
    indoor_cool_f=75,
    elevation_ft=5338,
    altitude_factor=0.82,       # air density at ~5,300 ft
    solar_btu_sf=70,            # average peak solar through glass per sq ft per unit SHGC, mixed orientations
    hp_capacity_at_design=0.85,  # cold-climate (variable-speed) heat pump: share of rated capacity left at the heating design temperature
    iecc_zone='6B',
)

# IECC 2021 prescriptive minimums for climate zone 6, as U-values (Btu/h·sf·°F).
ENVELOPE = dict(
    wall_u=0.045,      # R-20 cavity + R-5 continuous, whole-wall
    ceiling_u=0.026,   # R-49 attic
    vault_u=0.030,     # R-38 in the vaulted kitchen/living ceiling
    window_u=0.30,
    window_shgc=0.40,
    door_u=0.20,
    slab_f=0.54,       # F-factor, R-10 slab edge, Btu/h·ft·°F
    ach50=3.0,
    ach_nat=0.25,      # design-day natural air changes, ~ACH50 / 12 for a windy site
)
