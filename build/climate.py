"""Design climate and envelope assumptions, in one place.

64 Stone Sheep Circle is in Powell, WY (Park County, IECC zone 6B). Powell has
no TMY3 or ASHRAE station of its own, so the design temperatures and the
Property App's weather year (property/data/weather-tmy3.json) come from the
nearest one, Cody Municipal (WMO 726700), about 22 miles southwest and ~700 ft
higher. The air-density correction uses Powell's own elevation. Change the values
here and rerun build.py; M-1 and the Property App's energy model both read these.
"""

CLIMATE = dict(
    name='Powell, WY',
    source='ASHRAE 2009, Cody Muni AWOS (nearest station to Powell), 99.6 % heating / 1 % cooling',
    heat_design_f=-11.4,
    cool_design_f=87.8,
    indoor_heat_f=70,
    indoor_cool_f=75,
    elevation_ft=4370,
    altitude_factor=0.85,       # air density at Powell's ~4,370 ft
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
