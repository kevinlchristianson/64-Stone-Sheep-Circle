# 64 Stone Sheep Circle

Two web apps built from the owner's plans for 64 Stone Sheep Circle ("Larson House", six sheets dated 6/11/26, in `plan/source/`).

| Folder | App | Who it's for |
| --- | --- | --- |
| `contractor/` | **Contractor App**: the same format, layers and features as the 7824 Zero Rd contractor app. A 3D model with layers, the A-1 plan, S-1 framing, E-1 electrical, P-1 plumbing, M-1 HVAC and R-1 radiant slab sheets (every symbol tappable, schedules one pane at a time), shared open items you can resolve or comment on, printable packets, the owner's original sheets, and crew chat. Installs as a phone app. | The crews |
| `property/` | **Property App**: construction budget and payment ledger, rooms and open questions, hour-by-hour heating and cooling on Powell, WY weather, and the contractor app inside it. Installs as a phone app. | The owner |

`index.html` at the root links to both. Everything is static files, so any static host works.

## Hosting

- **GitHub Pages** (Settings > Pages > deploy from `main`, root) gives the crews a public address for the contractor app: `https://kevinlchristianson.github.io/64-Stone-Sheep-Circle/contractor/`.
- **Cloudflare** hosts the owner's copy privately and keeps the budget in step between devices. `wrangler.jsonc` and `worker/index.js` define it: the Worker serves the repo's files, and `/property/*` and `/api/*` are served only to a Cloudflare Access sign-in, checked by the Worker itself.

### Hosting on Cloudflare

1. Cloudflare dashboard > **Workers & Pages > Create > Import a repository**: pick `64-Stone-Sheep-Circle`, branch `main`, and keep the default deploy command (`npx wrangler deploy`). It deploys as `64-stone-sheep-circle.<your-subdomain>.workers.dev`, and redeploys on every push to `main`.
2. In the new Worker: **Settings > Domains & Routes > workers.dev > Enable Cloudflare Access**. Open the Access application it creates (**Zero Trust > Access > Applications**), set its policy to allow only your email, and copy its **Application Audience (AUD) tag**. Your **team name** is under **Zero Trust > Settings > Custom pages** (the part before `.cloudflareaccess.com`).
3. Put both in `wrangler.jsonc` as `ACCESS_TEAM` and `ACCESS_AUD` and push. Until they're set, the property pages answer "finish the Access setup" instead of opening.
4. If the property pages still say "finish the Access setup" after that, the live Worker is an old build: check **Settings > Builds** shows the repo connected (not "disconnected from your Git account") with production branch `main`, and that **Deployments** lists a build of the latest `main` commit.

The budget then saves to the Worker's store as well as the browser, and every device signed in sees the same ledger (the newer copy wins). Opened anywhere else (GitHub Pages, from disk) it stays in that browser only.

## Crew chat

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

The chat tab is off until a Firebase project is set up for it. See `contractor/CHAT-SETUP.md`.

## Assumptions to confirm

The plans have no site dimensions, structural or MEP sheets. The house is in Powell, WY; weather and design temperatures come from Cody, the nearest station. The apps assume an all-electric house with a cold-climate heat pump, and a north-facing front porch (owner, 2026-10-25: the top of every sheet is south, the garage side east). Each sheet lists its open questions, and `property/rooms.html` gathers them in one place.
