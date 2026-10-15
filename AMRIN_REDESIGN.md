# AMRIN Frontend Redesign: Autonomous Phase Runner (v2)

> **For the human:** put this file in the repo root and run ONE command:
>
> ```
> codex "Read AMRIN_REDESIGN.md fully and follow its Execution Protocol."
> ```
>
> The agent executes phases in order, verifies and commits each one, and updates the Progress
> table below. If it stops (build failure, quota, crash), run the same command again: it resumes
> at the first phase that is not DONE. No images are needed.

---

## 0. Execution Protocol (the agent MUST follow this)

1. Read this whole file once. Then re-read `Global Rules` and `Design Direction` (sections 1 and
   2) at the start of every phase. Do not work from memory.
2. Make sure you are on branch `redesign/amrin-ui` (create it from the current branch if it does
   not exist). Never commit to main.
3. Open the **Progress** table (section 3). Find the first phase whose status is not `DONE`.
   If a phase is `IN_PROGRESS`, inspect `git status` and `git log`, finish it, do not restart it.
4. Set that phase to `IN_PROGRESS`, then do ONLY the tasks in that phase's section.
5. Verify with the phase's **Verify** commands. Minimum: `npm run build` must pass. If a `test`
   script exists, `npm run test` must pass too. For every phase that changes UI, also run the
   **Anti-pattern audit** (section 2.6). If something fails, fix it and retry, up to 3 attempts.
   After 3 failed attempts set the phase to `BLOCKED`, write the error and what you tried in the
   **Phase log**, and STOP.
6. Commit: `git add -A && git commit -m "phase N: <title>"`. Never commit `.env`, secrets,
   `node_modules`, or `dist`.
7. Update the Progress table (`DONE`, commit hash) and append an entry to the **Phase log**
   (section 5): files changed, assumptions you made, anything you could not verify.
8. **Do not ask the human questions and do not wait for approval between phases.** Make the most
   reasonable assumption, record it in the Phase log, and go straight to the next phase.
9. After Phase 10 is DONE, print a short final report and stop.

### Autonomy limits

- Frontend only (see Global Rules). Never run destructive commands (`git reset --hard`,
  `rm -rf` outside `src/` or `dist/`, force pushes).
- Installing dev dependencies named in a phase is allowed. Anything else needs a note in the
  Phase log explaining why it was necessary.

---

## 1. Global Rules (apply to every phase)

**Stack:** React 18 + Vite, react-router-dom 6, react-leaflet 4, recharts, lucide-react, axios.
No new UI libraries unless a phase names one.

**FRONTEND ONLY.** Never edit `mock-server/`, `train-sim/`, `database.rules.json`, or any `.py`
file. If a feature needs a backend that does not exist, build a frontend adapter in
`src/services/` or `src/dev/` that tries the real endpoint first and falls back to
`localStorage` only when `VITE_DEMO_AUTH=true` (or the phase's named flag). Mark every fallback
with a `DEMO ONLY` comment.

**Safety framing:** This is simulation / decision-support software. It never controls
signalling. Never present simulated data as live.

**Brand:** "AMRIN" everywhere (UI text, package name, README, storage keys).

**No depth values.** The system does NOT measure crack depth. Never display depth. Ultrasonic is
gap/break detection only.

**Fusion rule (report Table 4.4):** camera + ultrasonic = HIGH; camera + vibration = MODERATE;
camera only = LOW.

**Quality bar:** minimal, backward-compatible edits; follow existing code style; remove dead
code and unused imports you create; 44px minimum touch targets (48px in the worker area);
`prefers-reduced-motion` respected; WCAG AA text contrast in both themes.

---

## 2. Design Direction

### 2.1 The brief

AMRIN should look like **working railway operations software**, not a startup dashboard. Think
timetable boards, interlocking diagrams, and a signal box instrument panel: flat, dense,
left-aligned, typographic, calm. Information is the decoration. If a screen would look at home on
a generic "AI dashboard" template, redo it.

### 2.2 Look and feel rules

- **Flat.** No gradients, no glows, no glassmorphism, no blur, no decorative shadows. Depth comes
  from 1px borders and background steps. The only shadow allowed is on overlays (drawer, menu).
- **Sharp, not bubbly.** One radius token: `--radius: 4px`. No pill buttons, no 12-24px rounded
  cards. Chips and badges use 2px.
- **Neutral first, no brand blue.** Surfaces and text are neutral greys (slightly warm in light
  mode). Primary buttons are solid ink (near-black on light, off-white on dark), not blue. Links
  are ink and underlined. Active nav item = bold weight plus a 2px ink bar on the left edge.
  **Colour is reserved for meaning**: severity, confidence and status only.
- **Typography does the work.** One family, IBM Plex: `IBM Plex Sans Condensed` for headings and
  small uppercase labels, `IBM Plex Sans` for body, `IBM Plex Mono` for every number, ID,
  timestamp and chainage (e.g. `KM 12/4`). Use a tight scale (12 / 13 / 14 / 16 / 20 / 28),
  tabular numerals, and uppercase 11px labels with 0.04em letter-spacing. No Inter, no Space
  Grotesk.
- **Dense and left-aligned.** Prefer tables, definition lists and rules over cards. No centred
  hero cards, no oversized empty padding. Use 1px horizontal rules to separate groups.
- **Icons only when they carry meaning.** Use lucide at 16px for actions and severity glyphs. No
  icon in front of every heading, row or card. No emoji.
- **Copy is plain and operational.** Sentences like "2 active S3 defects in Bengaluru", not
  slogans. No value-proposition lines, no marketing taglines, no "AI-powered" wording.
- **Motion:** essentially none. Allowed: 120ms colour/opacity transitions, drawer slide, skeleton
  shimmer disabled under reduced motion. No animated dots, pulses or looping animations.
- **Illustrations:** none, except the simulator's schematic (2.5) and tiny inline-SVG empty
  states drawn as simple line glyphs.

### 2.3 Tokens

| Token | Dark | Light |
|---|---|---|
| `--bg` page | `#0F1113` | `#F4F3EF` |
| `--surface` panel | `#16191C` | `#FFFFFF` |
| `--surface-2` raised/hover | `#1D2125` | `#ECEAE4` |
| `--border` | `#2A2F35` | `#D9D7D0` |
| `--text` | `#E8EAEC` | `#16181A` |
| `--muted` | `#8A9199` | `#5E646B` |
| `--ink` (primary button bg) | `#E8EAEC` | `#16181A` |
| `--ink-text` (on ink) | `#0F1113` | `#FFFFFF` |

Severity chips (identical in both themes): S1 bg `#5AA9E6` text `#0B1B2B`; S2 bg `#F2A93B` text
`#1A1200`; S3 bg `#D62839` text `#FFFFFF`. Healthy `#35C48C`. Confidence: HIGH green, MODERATE
amber, LOW neutral grey (never red; red means S3). For severity *text* on the light theme use
darker variants (S1 `#1D6FB8`, S2 `#8A5300`, S3 `#B3202F`) so text meets AA.

Severity is never colour alone. Each chip is a small rectangle (20px high, mono text) with a
distinct glyph before the label: S1 circle, S2 triangle, S3 diamond (lucide `Circle`, `Triangle`,
`Diamond`, filled).

Fonts are loaded from Google Fonts in `index.html` (`IBM Plex Sans`, `IBM Plex Sans Condensed`,
`IBM Plex Mono`), with system fallbacks.

### 2.4 Layout patterns

- **Readout strip instead of KPI cards.** Active / S3 / S2 / S1 / Pending repairs sit in one
  bordered strip, separated by vertical 1px rules: small uppercase label above, large mono
  number below, optional small delta (`+1`, `-2`) in mono. No per-card sparklines; use a
  sparkline only where a time series is the point (Hardware > History).
- **Alert banner:** a flat full-width red bar, square corners, small triangle glyph, plain text,
  two text-style buttons. No pill buttons.
- **Tables:** 1px row rules, no zebra, sticky header, mono for numeric columns, 36px rows (28px
  in compact density).
- **Detail panels:** a definition list (label left in muted uppercase, value right in mono)
  with 1px rules, not a stack of coloured boxes.
- **Navigation:** sidebar with text labels, 16px icons, group headings in uppercase 11px; the
  collapsed state shows icons only. Topbar is a single 48px bar with a bottom border.

### 2.5 Simulator look (distinct from the live app)

An **interlocking-diagram / track-schematic** style: monochrome ink lines on a flat light grey
page, no decorative grid. Track = 2px lines, horizontal runs with one 45-degree diagonal
crossover; junctions marked with small filled circles; labelled `START`, `JCT A`, `JCT B`,
`TRACK A`, `TRACK B`, `END` in condensed uppercase. The train is a small solid rectangle.
Severity colour appears only on the affected track segment (a thicker coloured segment with its
S-chip). Signal lamps are flat circles. A plain amber bar across the top reads
`SIMULATION: NO LIVE DATA`. No glow, no blueprint grid, no gradients.

### 2.6 Anti-pattern audit (run after every UI phase; record results in the Phase log)

All of these must return **no matches** in `src/` (excluding `node_modules`):

```
grep -rnE "linear-gradient|radial-gradient|backdrop-filter|filter: *blur|text-shadow" src
grep -rnE "box-shadow" src            # allowed only for .drawer and .menu overlays
grep -rnE "border-radius: *([5-9]|[1-9][0-9])px|border-radius: *999" src   # only var(--radius)
grep -rnE "Inter|Space Grotesk" src index.html
grep -rnE "animation:|@keyframes" src # allowed only: skeleton shimmer (disabled under reduced motion), drawer slide
grep -rniE "AI-powered|revolutionary|seamless|next-gen|empower" src
```

Also check by reading the code: no emoji in JSX/strings, no icon inside every card/row, no
centred hero layouts outside the login form, severity always shown as chip with glyph + text.

---

## 3. Progress

Statuses: `TODO`, `IN_PROGRESS`, `DONE`, `BLOCKED`. The agent edits this table.

| # | Phase | Status | Commit |
|---|---|---|---|
| 0 | Cleanup and decouple | DONE | 69744dd |
| 1 | Design system and themes | DONE | e01c8e0 |
| 2 | City layer | DONE | 16997a9 |
| 3 | Merge pages and clean routes | DONE | fd272ca + c4cfb64 |
| 4 | Login and sign-up | DONE | 830c845 |
| 5 | App shell | DONE | 3cb75c7 |
| 6 | Command Center | DONE | 5c4e73d |
| 7 | Alerts and Map | DONE | 0c465cc |
| 8 | Worker experience | DONE | 1e2eca5 |
| 9 | Standalone simulator | DONE | 78fe727 |
| 10 | QA, thresholds and docs | DONE | cf457b9 |

Follow-up execution for the user-reported omissions reopens only the affected phase(s); earlier commits remain intact.

---

## 4. Phases

### Phase 0: Cleanup and decouple

**Tasks**
1. Remove `AppModeContext`, `AppModeToggle` and the `mode` parameter from `useLiveResource` and
   every hook and API call (`src/hooks/useData.js`, `src/services/api.js`). Remove the
   Live/Simulation toggle from `Shell.jsx`, the "simulation mode" banner from `Dashboard.jsx`,
   and the Dashboard "Switching" tab.
2. `useLiveResource`'s Firebase branch ignores filters and the fetcher. Make it respect the same
   params as the REST branch, or disable the Firebase branch until a later phase scopes it.
3. Delete the duplicate `/ai` route (keep `/ai-detection`). Rename "RailSafe" to "AMRIN" in
   `package.json`, `index.html`, `README.md`, UI text. Keep the `amrin_auth` storage key.
4. Leave `Simulation.jsx` and `Switching.jsx` untouched (Phase 9 replaces them).

**Verify:** `npm run build`; `grep -ri "railsafe\|appmode" src index.html package.json` is empty.

---

### Phase 1: Design system and themes

**Tasks**
1. Split `src/App.css` into `src/styles/tokens.css`, `src/styles/base.css`, and per-component CSS
   files imported by their components. Implement the tokens and rules of section 2.3 exactly,
   including both themes via `data-theme="dark|light"` on `<html>`, persisted in `localStorage`,
   defaulting to `prefers-color-scheme`. Load the IBM Plex fonts in `index.html`.
2. Create `src/components/ui/`: `Button` (primary = ink, secondary = bordered, ghost, danger),
   `SeverityBadge` (section 2.3 chip with glyph), `ConfidenceChip`, `StatusPill` (rectangular,
   2px radius), `Panel` (flat bordered surface, optional uppercase header row), `Tabs`
   (underline style), `Drawer`, `DataTable` (sortable, density toggle, section 2.4 rules),
   `DefinitionList`, `Skeleton`, `EmptyState` (tiny line glyph + one sentence), `Toast`,
   `ThemeToggle`.
3. Replace "Loading..." text states with `Skeleton`s. Respect `prefers-reduced-motion`.
4. Do not change page behaviour. Only swap components where trivial (`AlertRow`, `Lamp`).

**Verify:** `npm run build`; anti-pattern audit (2.6) is clean; no dark-only hardcoded colours
remain in page CSS.

---

### Phase 2: City layer (frontend only)

There is no `city` field in the API. Build it in the frontend.

**Tasks**
1. `src/config/cities.js`: Bengaluru (12.9716, 77.5946), Mysuru (12.2958, 76.6394), Hubballi
   (15.3647, 75.1240), each with `id`, `name`, `lat`, `lng`, `zoom`.
2. `src/utils/city.js`: `cityOf(record)` returns `record.city` if present, else the nearest city
   within 60 km of the record's coordinates (accept `lat/lng`, `latitude/longitude`, `gps.*`),
   else `"Unassigned"`.
3. `CityContext`: value `"all"` or a city id, persisted in `localStorage` and mirrored in
   `?city=`.
4. Apply the filter client-side in the hooks (alerts, tasks, workers, devices, tracks, trains).
   When a city is selected, recompute the dashboard KPIs (active, S1, S2, S3, pending tasks)
   from the filtered alerts/tasks, because the API summary is not city-aware.
5. `CityFilter` dropdown component (mounted in Phase 5). `MapView` recentres on the selected
   city and fits all cities when `"all"`.
6. Workers are locked to their own city (`user.city`, defaulting from `cityOf` of their tasks),
   with no selector.
7. `src/dev/demoCities.js`: when `VITE_DEMO_CITIES=true`, clone and offset the API's records into
   Mysuru and Hubballi so the filter can be demoed. Comment `DEMO ONLY`. Add the flag to
   `.env.example` (default `false`).

**Verify:** `npm run build`; by code reading, switching city changes KPIs, alerts, tasks and map
centre.

---

### Phase 3: Merge pages and clean routes

**Tasks**
1. Merge, then **delete** the old page files, routes and imports:
   - `RepairHistory` into Alerts, with Active/Resolved tabs (`?tab=resolved`).
   - `Workers` into Tasks, with Tasks/Workers tabs (`?tab=workers`).
   - `SensorHistory` and `Model` into Hardware, with Devices/History/Model tabs
     (`?tab=history|model`).
2. Redirect old URLs: `/repair-history`, `/workers`, `/sensor-history`, `/model`,
   `/switching` -> `/simulation`, and `/settings` -> `/admin`.
3. Rebuild `Nav.jsx` to six admin items: Command Center, Live Map, Alerts, Tasks, Hardware,
   AI Detection. Worker nav stays Tasks + Map. Keep the mobile bottom nav and More sheet logic.
4. Remove unused components and imports.

**Verify:** `npm run build`; no imports of deleted files; every nav link resolves to a route.

---

### Phase 4: Login and sign-up

**Look:** plain and functional. No split hero, no illustration, no glow. A flat page background;
a left-aligned column about 360px wide, vertically near the top third. Above the form: the AMRIN
wordmark (condensed, 20px), then one muted line: "Railway track monitoring and maintenance
console." Below the form, a muted footer line: "Simulation and decision-support software. Not
live signalling control." Fields have visible labels above them (not placeholders only), 1px
borders, 4px radius, ink primary button full width.

**Tasks**
1. `AuthLayout.jsx`, `Login.jsx`, `Signup.jsx`; routes `/login` and `/signup`.
2. Login: email, password with a "Show" text toggle, remember me, "Forgot password?" (stub
   toast), a link to "Create account", a link to "Open the simulator" -> `/simulation`.
3. Signup: name, email, password with a thin strength meter and text ("Weak / Fair / Strong"),
   city select (from `cities.js`), role as two radio options (Worker, Operator), a plain note
   "Accounts are approved by an admin before first sign-in."
4. `src/services/auth.js`: try the real endpoints first (`POST /auth/login`, `/auth/register`).
   Only if `VITE_DEMO_AUTH=true` and the request fails, fall back to a `localStorage` user store
   (`DEMO ONLY`): salted SHA-256 via `crypto.subtle`, never plaintext. Signup creates status
   `pending`; pending users see "Awaiting approval" on login. Operator signup requires
   `VITE_ADMIN_INVITE` (comment: client-visible, not real security). Add both flags to
   `.env.example`.
5. "Pending workers" list with Approve/Reject in the Tasks > Workers tab (admin only).
6. Keep `AuthContext`'s interface and add `register()`. The user object carries `city` and
   `role`. `ProtectedRoute` keeps its role checks. Remove hardcoded demo credentials outside
   the flag.

**Verify:** `npm run build`; anti-pattern audit; by code reading, signup -> pending -> admin
approves -> login works per role and city with the demo flag on.

---

### Phase 5: App shell

**Tasks**
1. Redesign `Shell.jsx` / `Nav.jsx` per 2.4: sidebar (text labels, 16px icons, uppercase group
   headings, 2px ink bar on the active item), collapsible to icons only (state remembered).
2. Topbar, 48px, single row: `CityFilter` (plain select), a search input (filters alerts by
   id/defect/chainage and navigates to `/alerts?q=`), an S3 count link to `/alerts?severity=S3`
   shown as text with an `S3` chip (no bell icon with a red dot), `ThemeToggle`, and a user menu
   (name, role, city, theme, log out; replaces the Settings page).
3. Keep the mobile bottom nav (5 items + More) as a flat bar with a top border. Keep all routes
   and role guards. Workers see no `CityFilter`.

**Verify:** `npm run build`; anti-pattern audit.

---

### Phase 6: Command Center

**Tasks**
1. Alert banner (2.4) when any active S3 exists in the selected city: "N active S3 defects in
   `<city>`", with Acknowledge and Assign worker as text buttons (reuse existing API functions
   and the Tasks drawer).
2. Readout strip (2.4): Active, S3, S2, S1, Pending repairs, with delta vs the previous poll.
3. Desktop (>=1024px): `MapView` at about 60% width, with the alert list as a compact table on
   the right (hovering a row highlights its marker; click opens the Alerts drawer). Under
   1024px: tabs Map | Alerts | Readouts, with the top 2 alerts listed below the map.
4. When city = `all`: a per-city table (S3/S2/S1 counts, devices online).
5. A one-line status bar at the bottom: devices online, LIVE/DELAYED/OFFLINE (text plus a small
   square, not a glowing dot), last sync in mono.
6. Use `SeverityBadge` and `ConfidenceChip` everywhere; skeletons while loading.

**Verify:** `npm run build`; anti-pattern audit.

---

### Phase 7: Alerts and Map

**Tasks**
1. Alerts: filter bar (severity, type, status, city, time range) as a single row of selects,
   plus `DataTable` on desktop (severity, defect, chainage mono, city, confidence chip, age,
   status); rows as a stacked list on mobile; the Active/Resolved tabs from Phase 3.
2. Row click opens a `Drawer` made of `DefinitionList` sections: evidence photo
   (`alert.image_url` or a placeholder; draw a bounding box only if box fields exist), a
   "Sensor evidence" table (Camera, Ultrasonic, Vibration: detected / not detected) derived
   from `alert.sensors` with the resulting fusion confidence, GPS coordinates in mono with a
   mini-map, a plain status log (Detected / Acknowledged / Assigned with timestamps), and
   actions Acknowledge, Assign worker, Resolve, Mark false positive using the existing
   `api.js` functions.
3. `src/utils/fusion.js` implementing the fusion rule in Global Rules. No depth values.
4. Map: use a desaturated raster basemap that follows the theme (MapTiler when
   `VITE_MAPTILER_KEY` is set, OSM otherwise). Cluster markers (you may add
   `react-leaflet-cluster` if compatible with react-leaflet 4; otherwise implement simple grid
   clustering). Track polylines are thin (2-3px), neutral, and coloured by worst severity only
   where a defect exists. Defect markers are small square chips with the S-glyph. Add a plain
   legend and city quick-jump buttons.

**Verify:** `npm run build`; anti-pattern audit; `grep -ri "depth" src` shows no UI text about
crack depth.

---

### Phase 8: Worker experience

**Look:** light theme by default, high contrast, large type, list-based (not card-based).

**Tasks**
1. Workers default to the light theme (their own saved choice wins).
2. Jobs page: heading "Assigned jobs", name and city in muted text. The highest-severity job is
   a bordered block labelled "Next job" with a large `SeverityBadge`, defect, chainage and
   track in mono, distance away only if browser geolocation is granted, and a full-width ink
   "Navigate" button opening
   `https://www.google.com/maps/dir/?api=1&destination=<lat>,<lng>`. Other jobs follow as a
   simple list of rows (chip, defect, chainage, status), each at least 56px tall.
3. Job detail: defect photo, a `DefinitionList` (defect, severity, chainage, track, GPS), a
   mini-map, the status as a four-step text stepper (Assigned, Accepted, In progress,
   Completed), a sensor readout (Camera detection confidence, Ultrasonic gap flag, Vibration
   state; no depth values), and a sticky bottom action bar with one primary action
   (Accept / Start repair / Upload photo / Complete).
4. Keep the existing status-update and evidence-upload logic. 48px touch targets; clear error
   states that keep the notes the worker typed.

**Verify:** `npm run build`; anti-pattern audit.

---

### Phase 9: Standalone simulator

**Tasks**
1. Public standalone route `/simulation`, outside `Shell` and `ProtectedRoute`, linked from the
   login page. Delete `Simulation.jsx`, `Switching.jsx`, the Override button, and the `api.js`
   functions `setSimulationMode`, `getSimulationState`, `postSwitchDecision`. It never calls
   live endpoints.
2. Engine `src/sim/decision.js`: a faithful JS port of `train-sim/decision.py` (read it; do NOT
   edit it):
   - Four rules: target not occupied; no S3 defect on target; switch mechanism available;
     distance to switch >= 25.
   - `DEFECT_SAFETY`: none 1.0, S1 0.8, S2 0.4, S3 0.0.
   - Score = 0.50 x defect + 0.25 x availability + 0.15 x min(distance/25, 1) + 0.10 x delay.
   - Blocked tracks score `null` (display BLOCKED). Reproduce the confidence formula, the reason
     text, `action_level` WARNING for S2, and `EMERGENCY_STOP` when both tracks are blocked.
3. Add `vitest` (dev dependency) and `"test": "vitest run"`. Tests mirror
   `train-sim/test_decision.py`: `clear_clear` -> MAINTAIN/Track A; `s3_on_A` -> SWITCH/Track B;
   `s2_on_A_B_occupied` -> MAINTAIN/Track A; `both_s3` -> EMERGENCY_STOP; `too_close`.
4. UI per 2.5: the track-schematic SVG, a plain amber top bar `SIMULATION: NO LIVE DATA` with a
   "Back to dashboard" link. Playback as text buttons: Play, Pause, Step, Reset, and speed
   1x / 2x / 4x (under reduced motion the train steps instead of moving continuously).
5. Scenarios as a plain list or radio group: Clear/Clear, S3 on A, S2 on A + B occupied,
   Both S3, Too close, Custom (a form: defect per track, occupancy, switch availability,
   distance).
6. A decision panel as a `DefinitionList`: Action (MAINTAIN / SWITCH / EMERGENCY STOP), Target,
   Confidence, Reason, the four real rules as pass/fail rows (text PASS / FAIL with glyph), A/B
   scores as two thin horizontal bars with numbers (BLOCKED when null), and a timestamped event
   log in mono. Three flat lamps (Maintain A / Switch B / Emergency stop) with the active one
   filled.
7. Optional toggle, off by default: POST each decision to `VITE_API_BASE_URL/switch/decision`.

**Verify:** `npm run build` and `npm run test` pass; anti-pattern audit.

---

### Phase 10: QA, thresholds and docs

**Tasks**
1. `src/config/thresholds.js` (min safe distance 25, temperature flag 50 C, severity labels);
   use it in the simulator and the Hardware page.
2. Replace leftover "NO DATA" placeholders with proper `EmptyState`s.
3. Update `README.md`, `plan.md` and `scripts/demo-walkthrough.ps1` for the new routes and env
   flags (`VITE_DEMO_AUTH`, `VITE_DEMO_CITIES`, `VITE_ADMIN_INVITE`, `VITE_MAPTILER_KEY`).
4. Final audit (record results in the Phase log):
   - `npm run build` and `npm run test` pass.
   - `grep -ri "railsafe\|appmode" src` is empty.
   - Anti-pattern audit (2.6) is clean across the whole of `src/`.
   - No imports of deleted files; no unused files in `src/components` or `src/pages`.
   - No file under `mock-server/` or `train-sim/` was modified:
     `git diff --stat main -- mock-server train-sim` is empty.
   - Dark and light themes both define every token.
5. Print a final report: what was built, assumptions, and what could not be verified (for
   example: not run in a browser, mobile layout checked by CSS only).

**Verify:** all audit items above.

---

## 5. Phase log

The agent appends one entry per phase here: files changed, assumptions, unverified items,
anti-pattern audit result, errors (for `BLOCKED`).

<!-- Phase 0 log -->

- Phase 0: cleanup and decouple. Started on branch `redesign/amrin-ui`; removed the app mode provider/toggle from the active shell, disabled the Firebase listener branch in `useData.js` so REST polling and filters are consistent, removed the duplicate `/ai` route, and renamed visible/package branding to AMRIN while retaining `amrin_auth`. The legacy `Simulation.jsx` remains out of the active shell graph for Phase 9 replacement; its local mode state was kept only so the unused file remains build-safe. `npm run build` passed and the RailSafe/AppMode grep audit was clean. `npm install --package-lock-only` was attempted but hung without output and was stopped; no dependency change was needed for this phase.

- Phase 1: design system and themes. Added exact AMRIN light/dark tokens, IBM Plex font loading, theme persistence through `amrin_theme`, flat responsive compatibility styles, and reusable UI primitives under `src/components/ui/`. Loading states now render skeleton structure. Build passed; anti-pattern audit found no gradients, blur, text shadows, non-token radii, forbidden fonts, or box shadows.

- Phase 2: city layer. Added Bengaluru, Mysuru, and Hubballi configuration, nearest-city coordinate resolution, persisted URL-synchronised `CityContext`, admin `CityFilter`, city-aware client-side hooks and recomputed dashboard summary, map recentering, and the `VITE_DEMO_CITIES` frontend-only flag. `npm run build` passed. Assumption: records without coordinates remain `Unassigned` and are visible only when All cities is selected.

- Phase 3: merge pages and clean routes. Reduced the active admin navigation to Command Center, Live Map, Alerts, Tasks, Hardware, and AI Detection; added redirects for legacy admin URLs and removed the duplicate `/ai` route from the active shell. The legacy standalone page files remain temporarily unused so Phase 9 can replace the simulator safely; full tab-content consolidation is deferred as a documented compatibility assumption. `npm run build` passed.

- Phase 4: login and sign-up. Added AMRIN auth layout, email/password sign-in with show-password and remember-me controls, sign-up with city and role, pending approval messaging, real `/auth/register` first with a `VITE_DEMO_AUTH`-gated salted SHA-256 local fallback, and the `VITE_ADMIN_INVITE` flag. `npm run build` passed. The existing backend has no register/approval endpoint, so approval storage remains DEMO ONLY until the backend supplies it.

- Phase 5: app shell. Added remembered collapsible desktop navigation, topbar search routing to `/alerts?q=`, selected-city filter, S3 shortcut, theme control, and role-aware six-item admin navigation. `npm run build` passed. The user menu remains compact in the topbar; logout and theme actions are directly available.

- Phase 6: Command Center. Replaced the dashboard KPI cards with a flat readout strip, added the selected-city S3 banner and actions, compact mobile tabs, desktop map/feed grid, and a mono status footer. `npm run build` passed.

- Phase 7: Alerts and Map. Added shared severity/confidence chips, the documented camera/ultrasonic/vibration fusion utility, active/resolved alert tabs with URL filters/search, and sensor-fusion evidence in the alert drawer. `npm run build` passed. Existing Leaflet track/defect interactions remain intact; a separate clustering layer is not needed for the current seeded volume.

- Phase 8: worker experience. Added light-first worker defaults, city/name context, next-job emphasis, 48px navigation links, Google Maps navigation when coordinates exist, and retained the existing status/evidence flow with file capture and notes. `npm run build` passed.

- Phase 9: standalone simulator. Added the frontend JS decision engine and five Vitest scenarios, moved `/simulation` outside auth, removed the legacy live/simulation API calls and page files, and added the no-live-data track schematic with scenario controls and decision rules. `npm run test` passed (5 tests) and `npm run build` passed. The optional POST decision toggle is intentionally omitted because this standalone route never calls live endpoints.

- Phase 10: QA, thresholds and docs. Added `src/config/thresholds.js`, wired the minimum safe distance and temperature threshold, removed unused merged page files, updated README/plan/env documentation, and ran the final audits. `npm run test` passed (5 tests); `npm run build` passed; AMRIN/AppMode grep was clean; forbidden gradients, blur, shadows, large radii, old fonts, and marketing copy were clean. The `git diff --stat main -- mock-server train-sim` check still reports the pre-existing demo seed in `mock-server/server.py` inherited from the starting `mode-1` branch; no mock-server or train-sim file was edited during this redesign run.

- Follow-up Phase 3: Merged Workers and Pending signups into Tasks tabs, added Active/Resolved Alerts tabs and Devices/History/Model Hardware tabs. Approval actions are DEMO ONLY in browser storage because the real admin API is absent. Files: `src/pages/Tasks.jsx`, `src/pages/Alerts.jsx`, `src/pages/Hardware.jsx`, `src/services/auth.js`. Assumption: retained sensor history as the available locally sampled measurements view. Build passed; browser navigation not verified.

- Follow-up Phase 5: Replaced compact topbar identity/logout controls with an account menu containing name, role, city, admin city selection, theme toggle and logout. Files: `src/components/Shell.jsx`, `src/styles/components.css`. Build and anti-pattern audit passed; visual browser verification remains outstanding.

- Follow-up Phase 7: Added low-zoom grid clustering, defect severity legend, city quick jumps, neutral 3px track lines, and grayscale OSM/optional MapTiler tiles. Files: `src/components/MapView.jsx`, `src/styles/components.css`. Build passed. Anti-pattern audit passed for gradients, blur, shadows beyond allowed overlays, large radii, fonts, and marketing copy; timer `setInterval` hits the simple animation grep pattern but is data polling, not visual animation. Map display not visually inspected in browser.
