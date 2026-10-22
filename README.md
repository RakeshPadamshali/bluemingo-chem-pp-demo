# Bluemingo PP · Specialty Chemicals & APIs

A clickable demo of **production planning for a multiproduct API plant** — six reactors, four filters, four dryers, a
segregated high-potency suite, shared steam, brine and vacuum, an effluent plant, a solvent recovery train and a licensed
tank farm — running a real scheduler in the browser, with no server and no internet.

The argument it exists to make: **a chemical plant is limited by chemistry, not only by machines.** So the demo plans the
same order book twice, with the same scheduler and the same objective weights, and changes only seven rules:

| A generic planner assumes | This plant faces |
|---|---|
| a changeover time per product pair | a clean grade set by residue and compatibility |
| a fixed yield per product | yield that moves with assay and conversion |
| stock with unlimited shelf life | intermediates with hold-time windows |
| reactors as independent resources | shared steam, brine and vacuum |
| a production plan on its own | effluent, solvent recycle and consent limits |
| tanks sized by volume | licensed quantity ceilings by hazard class |
| allocation on quantity and date | allocation on spec, route and approval |

On the scoreboard a conventional plan is reported against, the generic plan **wins**. Replayed against the chemistry, it
loses — and the demo prices every rupee of it, event by event, naming the batch, the unit and what the chemical-aware plan
did instead.

Open `index.html` (the tab host) or any page on its own.

> **Everything in the dataset is fictional.** The site, the products, the customers, the people and the volumes are
> generated for the demo. What is *not* invented is the shape of the rules: the sixteen nuances come from Bluemingo's
> Specialty Chemicals deck, and the vocabulary — changeover matrix by attribute, links with a minimum and a maximum lag,
> campaign rules, secondary resources, block times — from the Bluemingo Production Planner design. Every generated
> parameter lives in `tools/gen/config.py` and is marked **generated** on the Master Data page.

## Run it

```bash
python serve.py            # http://localhost:8080  (any static server works)
```

No build step. Fonts, icons, ECharts and SheetJS are vendored in `assets/vendor/`, so the demo runs completely offline —
`tools/verify.py` fails the build if any request leaves the site.

## The modules

| Page | What it shows |
|---|---|
| **PP Dashboard** (`home.html`) | Is this plan honest, and what does the conventional plan cost? KPI row, the two-rule-set headline, a proof panel, the deck map of all sixteen nuances with a price on each, and the scenario launcher |
| **Plan Studio** (`studio.html`) | The two scoreboards side by side, the assumption ratchet, the full consequence ledger with cause / outcome / what-the-aware-plan-did-instead, the objective weights, and what the aware plan gave up on purpose |
| **Order Book & Promise** (`orders.html`) | Promised against balance-to-produce, and the constraint that sets each promise date |
| **Block Schedule** (`schedule.html`) | What runs where, and why this slot — rule by rule |
| **Cleaning & Campaigns** (`cleaning.html`) | The matrix by residue class, the campaign ladder, and the cleaning-hours ledger |
| **Multi-stage & Hold Times** (`stages.html`) | Stage chains as links with a minimum and a maximum lag, and the hold clock |
| **Utilities & Thermal Duty** (`utilities.html`) | Duty against cap by hour, the summer derate, and the concurrency board |
| **Effluent & Solvent Recovery** (`effluent.html`) | Daily load against consent, and the recovery balance |
| **Tank Farm & Hazard Licence** (`tanks.html`) | Tanks by bund, licence headroom over time, and the delivery calendar |
| **Batch Record & Yield** (`batches.html`) | Assay and yield against nameplate, where a campaign ended short, and the top-up |
| **Lots, Blending & Allocation** (`lots.html`) | The blend arithmetic, the allocation matrix with every reject named, and recall scope |
| **Capacity, Mix & Margin** (`capacity.html`) | Mix to capacity envelope, the bottleneck that moves, and margin per bottleneck hour |
| **Sourcing & Supply** (`sourcing.html`) | Make, buy or toll valued at the bottleneck, the approved-site matrix, and the price lag |
| **Stock, Shelf Life & Pack** (`stock.html`) | Season and shutdown pre-build, the remaining-life ladder, and bulk against packed |
| **Master Data** (`masters.html`) | Where every number comes from, the Configure / Extend route per rule, and the upload that re-plans the plant |

A header **role toggle** (Plant head · S&OP head · Both) reorders and dims the sidebar. It never hides a page: a plant
head can still open an S&OP screen, it just is not their first stop.

## Scenarios

The dashboard's launcher runs these on the live plan; every page then shows the same plan. **Reset demo** clears
everything. Thirteen cards stand on their own and three are reached from inside another — because these nuances compound.

| | Scenario | Nuance | Lands on |
|---|---|---|---|
| C1 | Deep colour, then a pale product | Plant 1 cleaning matrix | `cleaning.html` |
| C2 | The campaign that ends short | Plant 2 yield and assay | `batches.html` |
| C3 | The intermediate that spoils | Plant 3 hold times | `stages.html` |
| C4 | Three exotherms in one hour | Plant 4 utilities | `utilities.html` |
| C5 | Two heavy-effluent campaigns back to back | Plant 5 effluent | `effluent.html` |
| C6 | A delivery that breaches the licence | Plant 6 hazard limits | `tanks.html` |
| C7 | Three batches blended into one lot | Plant 7 spec blending | `lots.html` |
| C8 | Same plant, a different mix | S&OP 1 capacity | `capacity.html` |
| C9 | Margin per tonne against margin per bottleneck hour | S&OP 2 margin | `capacity.html` |
| C10 | A co-product that fills the tank | S&OP 4 co-products | `capacity.html` |
| C11 | A lot too old for this customer | S&OP 6 shelf life | `stock.html` |
| C12 | A site the customer has not approved | S&OP 7 approved sites | `sourcing.html` |
| C13 | A pre-build before the shutdown | S&OP 8 season | `stock.html` |
| → C2b | Cover the shortfall: make, buy or toll | S&OP 3 sourcing | `sourcing.html` |
| → C13b | Book the raw-material block | S&OP 5 supply blocks | `sourcing.html` |
| → C13c | Hold it as bulk, pack it late | S&OP 9 pack | `stock.html` |

Two guided tours — the plant head's story (C1→C7) and the S&OP head's story (C8→C13) — chain the cards with one line of
narration each.

## How it is put together

- **`data/chm-data.js`** — the whole dataset (`window.CHM`), written by `tools/generate_data.py`. **Generated, never
  hand-edited**: change `tools/gen/*.py` and re-run.

  ```bash
  python tools/generate_data.py                  # as-of = today 09:30
  python tools/generate_data.py --asof 2026-10-22
  ```

  The generator re-bases every date on the as-of moment, checks its own output (unique ids, every reference resolves,
  every operation has an eligible unit, every hold window is a window, every scenario anchor exists, the demand sits where
  the tension gate wants it) and writes the data dictionary `data/README.md`. It also emits
  **`data/planner-input.sample.json`** — the same plant in the Bluemingo Production Planner's own input contract, as a
  real specialty-chemicals test case for the product team.

- **`assets/chm-engine.js`** — the scheduler. DOM-free, so it also runs in Node. **One scheduler, two rule sets**:
  `E.RULES.aware` and `E.RULES.generic` are capability flags, not two code paths. The generic set keeps everything a real
  APS keeps — equipment non-overlap, eligibility, block times, batch sizes, due-date order, campaign grouping — and swaps
  only the seven rules in the table above. Forking the builder would be a straw man, and would deserve to be called one.

- **`assets/chm-results.js`** — allocation, the one KPI basis, the consequence replay, the repair sweep, the proof and
  S&OP. `consequence()` **replays** the generic plan on its own timeline and prices what its assumptions cost; it never
  re-schedules. Only the first-order consequence per batch is carried through to a status, and the count that is priced
  but not propagated is reported rather than hidden.

- **`assets/chm-core.js`** — one shared runtime for every page: the live-demo state in `localStorage`, the host-shared
  comparison (the tab host computes once, every tab reads it), formatting with the basis of each quantity attached, the
  validated data palette, the Gantt with its window pager, Excel export and the scenario definitions.

- **`assets/chm-nuances.js`** — the registry of all sixteen nuances with the deck's claim verbatim, the owning page, the
  scenario that demonstrates it and the Configure / Extend route. The sidebar, the deck map, every page header and
  `tools/verify.py` all read it, and the verifier asserts the bijection: sixteen owned, none twice, none orphaned.

### Decisions in the engine worth knowing before changing it

- **Physics is seeded on (product, nth batch of that product)**, never on plan order — so both rule sets face identical
  yields, assays and QC times, and only their *reaction* differs. That one detail is what makes the comparison valid.
- **A clean-down is validated for a product**, and a forbidden pair survives every clean. Cleaning the train for A does
  not make it clean for B.
- **Cleaning starts when the unit frees, not when the upstream stage ends** — a filter is cleaned while the reactor it
  feeds from is still running. Attach the clean to the batch instead and any link whose hold window is shorter than its
  boil-out becomes impossible, which is not how a plant works.
- **An operation's utility draw is the maximum of the segments touching each hour, never their sum**, and the admission
  test sees the rest of the train. Both halves of that were wrong once and the plan silently broke its own caps.
- **The tank farm is settled in strict time order after the plan is committed**, because the scheduler commits trains in
  score order; a day-cumulative level depended on the order chains happened to be placed.
- **What-ifs record how to undo themselves.** The model is cached and shared, so a what-if that writes into it would
  survive Reset demo and poison every later plan.
- **The campaign rule has a minimum as well as a maximum.** Only demand inside its release window can be seen, and at any
  instant that is roughly one line per product — so without a minimum the plan never starts a campaign and pays a
  clean-down for every single batch. When a unit is mid-campaign and short of the minimum, the next batch of that product
  is pulled forward from inside `pullAheadDays` and belongs to that train while it holds the product. Both rule sets get
  this: it is a planning policy, not a chemical rule. What differs is what each believes breaking a campaign costs.
  Build-ahead for its own sake was tried and removed — on a plant limited by the window into isolation it *spends* the
  scarce downstream slots on work that is not due, and output falls.
- **Utilisation is reported per equipment class, never as a plant mean.** A mill runs an hour a batch and a packing line a
  shift a week; averaging them with the reactors says a plant is idle when the train that matters is full.
- **Reported caps apply the same inherited-history rule as the proof.** Work already in progress at the as-of moment can
  put an hour over its cap before this plan places anything, and no plan can undo that; the constraint is that it may not
  *add* to such an hour. Report the raw peak instead and the plan reads as breaking its own cap — which it is not.
- **Five scenario anchors and two Master Data worked examples are resolved at run time from the plan**, not chosen when
  the data is generated — a cap has to be cut below the load this plan actually puts on it, a spec tightened against the lot pool it actually makes, a lot
  aged that a regulated line actually depends on. Chosen up front, three of those cards changed nothing at all.
- **C7 tightens an impurity limit, never an assay minimum.** A blend's assay is the mass-weighted mean of its lots, so
  blending can never beat the best lot in the pool; impurity averages down, which is what blending is for.
- **Allocation tests a lot against the date the line must ship**, not against the moment the planner is looking, and a
  line already past its date is *late*, not short.
- **The order book calibrates by line count as well as quantity.** A line consumes a whole batch however small it is, so
  once every line sits on the minimum-size floor the book has a cost in batches that no scaling can reduce; past that the
  generator trims the book instead, open domestic and furthest-due first.
- **A product uploaded without a route is held back with a reason**, not crashed on. It is the first thing anyone does.

## Verify

```bash
node tools/check_pages.js        # every page's inline script, syntax only -- a second, and it names the line
node tools/verify_engine.js      # ~70k invariants, rebuilt from the plan's output, for every preset
node tools/verify_tension.js     # does the data still give every claim something to bite on?
python tools/verify.py           # all 15 pages + the host, headless: no JS error, nothing leaves the site
python tools/verify_flows.py     # all 16 scenarios end to end, Reset demo, the role toggle
python tools/verify_masters.py   # the Excel round trip on every uploadable master, and the negative path
python tools/audit.py [preset]   # every figure shown on more than one page is the same number
node tools/run_engine.js [preset] # the two plans, the ledger and the proof, on the terminal
node tools/calibrate.js [pctl]   # what the plant demands of each shared resource, to set the caps from
```

Run them in that order: the first two take seconds and catch most of what breaks.

`verify_engine.js` deliberately **rebuilds every series from the plan's output** — the batches, their operations, the
cleans, the lots, the accepted deliveries — and never reads the scheduler's own buckets. If it checked those, the
scheduler would be certifying itself and a bucketing bug would pass twice. It also holds the **fairness gate**: the
generic plan has to *win* the naive scoreboard. If it ever loses on paper too, the comparison is a straw man and the build
fails.

## Look and feel

The demo follows the **Bluemingo MES v2 design system** (`UI-Style-Guide-Prompt.md`, kept with the MES workspace — not
copied into this repo), the same one the other Bluemingo POCs use:

| | |
|---|---|
| Primary | `#25A9E0`, hover `#1E8FBF`, light `#E1F5FE` — interactive elements only |
| Chrome | header `#1a1a2e → #12121f`, sidebar `#1e1e32 → #16213e`, content `#f5f5f5`, cards white with an `#e0e0e0` border |
| Status | success `#388e3c`, warning `#f57c00`, danger `#d32f2f`, info `#2196f3` — always an `rgba(colour, .12)` tint with solid text, never a solid fill |
| Type | Roboto; tables 12 px with 10.5 px uppercase headers; 4 px spacing grid; radius 4 px inputs / 6 px panels |
| Focus | 3 px primary glow `rgba(37,169,224,.15)` |

`assets/chm-shell.css` holds those tokens, so a change there re-themes the whole demo. **Data colours are a separate,
validated set** (`COLOR` in `assets/chm-core.js`): a four-slot categorical palette for product families, an ordinal ramp
for clean grades — because the grades *are* ordered, from no clean to not permitted — the reserved status steps for caps
and limits, always with a label beside them, and one colour per utility.
