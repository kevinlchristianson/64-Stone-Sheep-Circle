# 64 Stone Sheep Circle

Two web apps built from the owner's plans for 64 Stone Sheep Circle ("Larson House", six sheets dated 6/11/26, in `plan/source/`).

| Folder | App | Who it's for |
| --- | --- | --- |
| `contractor/` | **Contractor App**: one page with a 3D model, the A-1 plan, S-1 framing, E-1 electrical, P-1 plumbing and M-1 HVAC sheets (every symbol tappable), printable packets, the owner's original sheets, and crew chat. Installs as a phone app. | The crews |
| `property/` | **Property App**: construction budget and payment ledger, rooms and open questions, hour-by-hour heating and cooling on Casper weather, and the contractor app inside it. Installs as a phone app. | The owner |

`index.html` at the root links to both. Everything is static files, so any static host works (GitHub Pages from the repo root, for example).

## How it is built

```
plan/source/larson-house-plans-2026-06-11.pdf   the owner's plans
plan/tools/extract_walls.py                     pulls the wall rectangles out of the PDF
plan/house.py  ->  plan/house.json              rooms, walls, doors, windows, fixtures (the single source)
plan/ANALYSIS.md                                the plan breakdown and the discrepancies found
build/*.py                                      one generator per sheet (plan, framing, electrical, plumbing, hvac)
build/build.py                                  writes contractor/index.html, sheets, packets and property/data/*.json
build/render_packets.mjs                        prints the packets to PDF (Playwright)
```

To rebuild after changing `plan/house.py` or a generator:

```
python3 plan/house.py
python3 build/build.py
node build/render_packets.mjs        # needs Playwright and Chromium
```

Then bump `VERSION` in `build/build.py`, `contractor/sw.js` and `property/sw.js` so installed phones pick up the new copy.

Coordinates on every sheet are feet from the outside of the garage-door wall (X) and from the outside of the master bedroom's rear wall (Y).

## Crew chat

The chat tab is off until a Firebase project is set up for it. See `contractor/CHAT-SETUP.md`.

## Assumptions to confirm

The plans have no site dimensions, structural or MEP sheets. The apps assume Casper, WY weather, an all-electric house with a cold-climate heat pump, and a south-facing front porch. Each sheet lists its open questions, and `property/rooms.html` gathers them in one place.
