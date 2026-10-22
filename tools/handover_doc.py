"""The hand-over document: the demo's argument in order, with the screens it refers to.

Imported by tools/build_handover.py. Every number comes from `f`, which is read out of the engine, so the document
cannot drift away from the demo it describes.
"""

CSS = """
@page { size: A4; margin: 15mm 14mm 16mm 14mm; }
* { box-sizing: border-box; }
body { font-family: Roboto, 'Segoe UI', sans-serif; font-size: 10.2pt; line-height: 1.5; color: #333; margin: 0; }
h1 { font-size: 23pt; margin: 0 0 4px; color: #12121f; letter-spacing: -0.3px; }
h2 { font-size: 14pt; margin: 22px 0 7px; color: #1E8FBF; border-bottom: 2px solid #E1F5FE; padding-bottom: 4px; }
h3 { font-size: 11.4pt; margin: 15px 0 5px; color: #12121f; }
p { margin: 0 0 8px; }
ul, ol { margin: 0 0 9px; padding-left: 18px; } li { margin-bottom: 4px; }
table { width: 100%; border-collapse: collapse; font-size: 8.8pt; margin: 7px 0 11px; }
th { text-align: left; background: #f5f5f5; border-bottom: 1.5px solid #e0e0e0; padding: 5px 7px; font-size: 7.8pt;
     text-transform: uppercase; letter-spacing: .4px; color: #666; }
td { padding: 4px 7px; border-bottom: 1px solid #eee; vertical-align: top; }
td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; }
.cover { background: linear-gradient(120deg, #1a1a2e, #12121f); color: #fff; padding: 26px 28px; border-radius: 10px; margin-bottom: 16px; }
.cover h1 { color: #fff; } .cover .sub { color: #8fd4f0; font-size: 12pt; margin-top: 2px; }
.cover .meta { margin-top: 14px; font-size: 9.4pt; color: rgba(255,255,255,.78); line-height: 1.6; }
.cover .url { background: rgba(255,255,255,.1); border: 1px solid rgba(255,255,255,.2); border-radius: 6px;
              padding: 7px 11px; margin-top: 12px; font-size: 10pt; color: #fff; display: inline-block; }
.lead { font-size: 11pt; color: #444; }
.box { background: #fafafa; border: 1px solid #e0e0e0; border-left: 3px solid #25A9E0; border-radius: 5px;
       padding: 9px 12px; margin: 9px 0; font-size: 9.6pt; }
.box.warn { border-left-color: #f57c00; background: #fff8e1; }
.box.good { border-left-color: #388e3c; background: #f1f8f2; }
.box b { color: #12121f; }
.big { font-size: 20pt; font-weight: 700; color: #12121f; line-height: 1.1; }
.big.bad { color: #c62828; } .big.good { color: #2e7d32; }
.two { display: flex; gap: 14px; } .two > div { flex: 1; }
figure { margin: 10px 0 14px; page-break-inside: avoid; }
figure img { width: 100%; border: 1px solid #ddd; border-radius: 5px; display: block; }
figcaption { font-size: 8.6pt; color: #666; margin-top: 4px; font-style: italic; }
.tag { display: inline-block; font-size: 7.6pt; font-weight: 700; padding: 1px 6px; border-radius: 3px; letter-spacing: .3px; }
.tag-c { background: rgba(56,142,60,.14); color: #2e7d32; } .tag-e { background: rgba(245,124,0,.16); color: #e65100; }
.keep { page-break-inside: avoid; }
.pb { page-break-before: always; }
.q { font-weight: 600; color: #12121f; margin-top: 11px; }
.a { margin: 2px 0 0; color: #444; }
code { background: #f5f5f5; padding: 1px 4px; border-radius: 3px; font-size: 8.8pt; }
"""

NUANCES = [
    ("P1", "1", "Cleaning-matrix sequencing", "Sequence is set by the cleaning matrix, not by setup time",
     "Cleaning & Campaigns", "Configure", "Production Planning and Scheduling"),
    ("P2", "2", "Yield and assay", "The batch count is an estimate, because every batch yields differently",
     "Batch Record & Yield", "Extend", "Scheduling with Plant Analytics"),
    ("P3", "3", "Intermediates and hold times", "Intermediates turn stock into a timing decision",
     "Multi-stage & Hold Times", "Configure", "Multi-stage Production Scheduling"),
    ("P4", "4", "Utilities and thermal duty", "Reactors cannot all run at once, because utilities set the limit",
     "Utilities & Thermal Duty", "Extend", "Scheduling with shared-resource rules"),
    ("P5", "5", "Effluent, solvents, recycle", "Effluent and solvent recovery are capacity, not afterthoughts",
     "Effluent & Solvent Recovery", "Extend", "Scheduling with Supply Planning"),
    ("P6", "6", "Hazard and storage limits", "Safety and licence limits are hard constraints on the plan",
     "Tank Farm & Hazard Licence", "Extend", "Supply Planning, Inventory Optimization"),
    ("P7", "7", "Spec-driven lot blending", "Orders match on specification, route and approval, not only quantity",
     "Lots, Blending & Allocation", "Extend", "Material Allocator"),
    ("S1", "1", "Capacity and product mix", "Capacity moves with the product mix, so one tonnage number misleads",
     "Capacity, Mix & Margin", "Configure", "S&OP, Network Optimization"),
    ("S2", "2", "Margin per bottleneck hour", "Rank products by margin per bottleneck hour, not per tonne",
     "Capacity, Mix & Margin", "Configure", "S&OP, Network Optimization"),
    ("S3", "3", "Make, buy or toll", "Make, buy or toll is a recurring call, not a one-time decision",
     "Sourcing & Supply", "Configure", "S&OP, Network Optimization"),
    ("S4", "4", "Co-products", "A co-product can cap the main product",
     "Capacity, Mix & Margin", "Extend", "Supply Planning, Inventory and Network Optimization"),
    ("S5", "5", "Supply blocks and price lag", "Raw materials arrive in blocks, and their price moves before yours does",
     "Sourcing & Supply", "Configure", "Supply, Demand, Inventory Optimization"),
    ("S6", "6", "Shelf life", "Inventory has an expiry, so stock is not all equal",
     "Stock, Shelf Life & Pack", "Extend", "Supply Planning, Inventory and Network Optimization"),
    ("S7", "7", "Approved sites", "Which site can supply which customer is a planning constraint",
     "Sourcing & Supply", "Extend", "Supply Planning, Inventory and Network Optimization"),
    ("S8", "8", "Season and shutdown", "Seasonal peaks and annual shutdowns are met with stock built early",
     "Stock, Shelf Life & Pack", "Configure", "Supply, Demand, Inventory Optimization"),
    ("S9", "9", "Pack and postponement", "Hold bulk, and decide pack and label late",
     "Stock, Shelf Life & Pack", "Configure", "Supply, Demand, Inventory Optimization"),
]

TOUR = [
    ("C1", "Deep colour, then a pale product", "Cleaning & Campaigns",
     "Open the matrix and click the cell the card names. The grade is not a setup time — it is read off family, solvent "
     "class, colour load and potency, and the plant's own overrides sit on top marked with an asterisk. Then look at the "
     "campaign ladder: pale to deep inside a family, and a boil-out wherever the colour load falls."),
    ("C2", "The campaign that ends short", "Batch Record & Yield",
     "The bar is what came out; the tick is the theoretical yield a generic plan books. Run the card and the campaign "
     "assays low: the batch count was an estimate, and the top-up arrives after the train has been broken down, paying a "
     "clean in and a clean out."),
    ("C3", "The intermediate that spoils", "Multi-stage & Hold Times",
     "The route is drawn as links with a minimum and a maximum lag — the planner's own vocabulary. Run the card and the "
     "window on the link the plan is leaning on tightens below the lag it was taking, so the next plan cannot keep it."),
    ("C4", "Three exotherms in one hour", "Utilities & Thermal Duty",
     "Find the hour the plan had least room in: the contributing batches add up to exactly the cap. Run the card and the "
     "brine plant derates — the same batches can no longer run together, and the plan staggers them rather than trip."),
    ("C5", "Two heavy-effluent campaigns back to back", "Effluent & Solvent Recovery",
     "A daily consent does not average out. Run the card and the treatment plant decides when the two heaviest products "
     "can run; the solvent loop shows what comes back, what is held in the train and what had to be bought in."),
    ("C6", "A delivery that breaches the licence", "Tank Farm & Hazard Licence",
     "The ceiling that refuses a tanker is the licence, not the tank — a half-empty tank is no use if the site is at its "
     "licensed quantity, and recovered solvent counts towards it. Run the card and watch the tanker wait at the gate."),
    ("C7", "Three batches blended into one lot", "Lots, Blending & Allocation",
     "The blend is mass-weighted on ACTIVE content, not on volume, and the remaining life of the consignment is the "
     "shortest of its lots. Run the card and the impurity limit tightens below what the current blend carries."),
]


def nuance_table(f):
    rows = []
    for nid, no, name, claim, page, route, module in NUANCES:
        c = f["byNuance"].get(nid)
        cost = ("Rs %.2f Cr" % (c["rupees"] / 1e7)) if c and c["rupees"] >= 1e7 else \
               ("Rs %.1f L" % (c["rupees"] / 1e5)) if c and c["rupees"] else ("S&OP horizon" if nid.startswith("S") else "—")
        n = str(c["n"]) if c and c["n"] else ""
        tag = "tag-c" if route == "Configure" else "tag-e"
        rows.append(
            "<tr><td><b>%s %s</b></td><td>%s</td><td>%s</td><td>%s</td><td class='n'>%s</td><td class='n'>%s</td>"
            "<td><span class='tag %s'>%s</span></td></tr>"
            % ("Plant" if nid.startswith("P") else "S&OP", no, name, claim, page, n, cost, tag, route))
    return ("<table><thead><tr><th>Nuance</th><th>Name</th><th>The deck's claim, verbatim</th><th>Where it is in the demo</th>"
            "<th class='n'>Events</th><th class='n'>What it costs a generic plan</th><th>Slide 39</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table>")


EQ = {"REACTOR": "the reactors", "ISOLATION": "the isolation train — the filters and filter-dryers",
      "DRYER": "the dryers", "MILL": "the mill", "PACK": "the packing lines"}


def rs(x):
    a = abs(x)
    return ("-" if x < 0 else "") + ("Rs %.2f Cr" % (a / 1e7) if a >= 1e7 else "Rs %.1f L" % (a / 1e5) if a >= 1e5 else "Rs %d" % a)


def build(f, imgs, url):
    def fig(key, cap):
        if key not in imgs:
            return ""
        return "<figure><img src='data:image/png;base64,%s'><figcaption>%s</figcaption></figure>" % (imgs[key], cap)

    gen_net = f["genContribution"] - f["genDelay"] - f["consTotal"]
    aw_net = f["awareContribution"] - f["awareDelay"]

    html = ["<!DOCTYPE html><html><head><meta charset='utf-8'><style>%s</style></head><body>" % CSS]

    # ---- cover
    html.append(
        "<div class='cover'><h1>Bluemingo PP &middot; Specialty Chemicals &amp; APIs</h1>"
        "<div class='sub'>A clickable demo of the sixteen nuances, argued on screen</div>"
        "<div class='meta'>A multiproduct API plant &mdash; %d units, %d products in four families, %d customers, "
        "%d order lines &mdash; planned twice by one scheduler: once the way a generic planner would, and once with the "
        "chemistry put back. The difference is priced, event by event.<br>"
        "Plan as of %s &middot; %d days of frozen history &middot; %d-day detailed plan &middot; twelve monthly buckets."
        "</div><div class='url'>%s</div></div>"
        % (f["units"], f["products"], f["customers"], f["lines"], f["asOf"][:10],
           f["historyDays"], f["forwardDays"], url))

    html.append(
        "<p class='lead'>This document is for whoever wrote the Specialty Chemicals deck. It goes through the demo in the "
        "order the argument runs, says which claims are yours to validate with the product team, and answers the questions "
        "a prospect will ask. Everything in the dataset is fictional; what is not invented is the shape of the rules.</p>")

    # ---- the argument
    html.append("<h2>The argument, in one page</h2>")
    html.append(
        "<div class='two'><div><div class='big bad'>%s</div>"
        "<p>is what the generic plan's seven assumptions cost once its own plan is replayed against the chemistry: "
        "%s kg of product and %s hours of plant across %d priced events. %d of them change a batch's status; %d more are "
        "priced but not carried through, and that count is shown rather than hidden.</p></div>"
        "<div><div class='big good'>%s</div>"
        "<p>constraint checks over the chemical-aware plan, with <b>%d</b> broken. It gives up %d starts on purpose &mdash; "
        "%d hours of deliberate idle &mdash; rather than strand an intermediate.</p></div></div>"
        % (rs(f["consTotal"]), "{:,}".format(int(f["consKg"])), "{:,}".format(int(f["consHours"])),
           f["consRows"], f["statusChanging"], f["unmodelled"],
           "{:,}".format(f["proofChecks"]), f["proofViolations"], f["sacrifices"], f["sacrificeH"]))

    html.append(
        "<h3>Read the left-hand scoreboard first</h3>"
        "<table><thead><tr><th>On the measures a conventional plan is reported against</th><th class='n'>Generic</th>"
        "<th class='n'>Chemical-aware</th></tr></thead><tbody>"
        "<tr><td>On time, in full</td><td class='n'>%.1f%%</td><td class='n'>%.1f%%</td></tr>"
        "<tr><td>Output booked, at the yield each plan books</td><td class='n'>%s t</td><td class='n'>%s t</td></tr>"
        "<tr><td>Cleaning hours booked</td><td class='n'>%s</td><td class='n'>%s</td></tr>"
        "<tr><td>Late lines</td><td class='n'>%d</td><td class='n'>%d</td></tr>"
        "<tr><td>Batches per campaign</td><td class='n'>%.2f</td><td class='n'>%.2f</td></tr>"
        "</tbody></table>"
        "<div class='box warn'>That is the point. It is not a weak plan &mdash; it is a plan scored on what it assumes "
        "about itself. Every one of those figures is what the generic rule set believes, and the demo lets it be believed "
        "for as long as it takes to turn the page.</div>"
        % (f["genOtif"] * 100, f["awareOtif"] * 100,
           "%.1f" % (f["genNominalKg"] / 1000), "%.1f" % (f["nominalKg"] / 1000),
           "{:,}".format(int(f["genClean"])), "{:,}".format(int(f["awareClean"])),
           f["genLate"], f["awareLate"], f["genPerCampaign"], f["perCampaign"]))

    html.append(
        "<table><thead><tr><th>What the plant is actually left with</th><th class='n'>Generic</th>"
        "<th class='n'>Chemical-aware</th></tr></thead><tbody>"
        "<tr><td>Constraints broken</td><td class='n'>%d</td><td class='n'>%d</td></tr>"
        "<tr><td>Product written off or re-worked</td><td class='n'>%s kg</td><td class='n'>0 kg</td></tr>"
        "<tr><td>Plant hours lost to the consequences</td><td class='n'>%s h</td><td class='n'>0 h</td></tr>"
        "<tr><td>Contribution</td><td class='n'>%s</td><td class='n'>%s</td></tr>"
        "<tr><td>Late-delivery penalties</td><td class='n'>%s</td><td class='n'>%s</td></tr>"
        "<tr><td>Cost of the assumptions</td><td class='n'>%s</td><td class='n'>Rs 0</td></tr>"
        "<tr><td><b>Net</b></td><td class='n'><b>%s</b></td><td class='n'><b>%s</b></td></tr>"
        "</tbody></table>"
        % (f["genViolations"], f["proofViolations"], "{:,}".format(int(f["consKg"])), "{:,}".format(int(f["consHours"])),
           rs(f["genContribution"]), rs(f["awareContribution"]), rs(-f["genDelay"]), rs(-f["awareDelay"]),
           rs(-f["consTotal"]), rs(gen_net), rs(aw_net)))

    html.append(
        "<h3>What limits this plant, and what a utilisation figure hides</h3>"
        "<p>The busiest class of equipment is %s: <b>%.0f%%</b> of its calendar is spoken for — %.0f%% running and "
        "%.0f%% being cleaned. A plant-wide average would be a far smaller number and would say nothing, because it would "
        "average the reactors with a mill that runs an hour a batch and a packing line that runs a shift a week. Every "
        "page in the demo reports the class for that reason, never the plant mean.</p>"
        "<p>What stops the reactors running harder is not the reactors. It is the window into isolation: a reaction that "
        "cannot be filtered inside its hold time cannot be started, so a free reactor stays free. That is nuance 3 showing "
        "up as a capacity figure rather than as a rule, and it is also why cleaning takes <b>%.0f%%</b> as many hours as "
        "processing — in a plant this constrained campaigns are short and changeovers frequent. The campaign rule is what "
        "keeps that number from being far worse: it pulls the next batch of a product forward to reach a minimum campaign, "
        "and in this plan it does so %d times.</p>"
        % (EQ.get(f["utilClass"], str(f["utilClass"]).lower()), f["utilBusiest"] * 100, f["utilRun"] * 100, f["utilClean"] * 100,
           f["cleanShareOfRun"] * 100, f["pulled"]))
    html.append(fig("studio-0", "Plan Studio. The two scoreboards sit side by side, with the assumption ratchet beneath "
                                "them: switch one generic assumption to the chemical rule and watch its consequence disappear."))

    # ---- how to run it
    html.append("<h2 class='pb'>Running the demo: the plant head's story</h2>")
    html.append("<p>Seven cards, in the order the constraints hit the floor. Each one re-plans the plant and lands on the "
                "page that owns the nuance. <b>Reset demo</b> in the header puts everything back.</p>")
    for cid, title, page, how in TOUR:
        html.append("<div class='keep'><div class='q'>%s &nbsp;%s <span style='font-weight:400;color:#666'>&rarr; %s</span></div>"
                    "<p class='a'>%s</p></div>" % (cid, title, page, how))
    html.append("<div class='box'>Start on the <b>PP Dashboard</b>: the headline, the proof panel, and the deck map of all "
                "sixteen nuances with a price on each. Click any nuance to open the page that carries it. The launcher at the "
                "bottom runs the cards, and <b>the plant head's story</b> chains these seven with one line of narration each.</div>")
    html.append(fig("home-0", "The PP Dashboard. The figure on the left is what the conventional plan costs; the figure on "
                              "the right is the number of constraint checks the recommended plan passes."))
    html.append(fig("home-1", "The deck map. Sixteen nuances, each with the deck's claim, the page that carries it, and what "
                              "it costs a plan that does not see it."))

    html.append("<h2>And the S&amp;OP head's story</h2>")
    html.append(
        "<p>Six cards a quarter out, where the question is mix and sourcing rather than sequence. C8 shifts the mix and the "
        "single tonnage number stops being true; C9 shows the ranking reverse when it is measured per bottleneck hour; C10 "
        "lets a co-product cap the product that pays for the campaign; C11 ages a lot past a customer's minimum; C12 takes "
        "away a site approval; C13 builds stock before the shutdown. Three further cards sit <i>inside</i> C2 and C13 &mdash; "
        "make, buy or toll; the raw-material block; holding bulk and packing late &mdash; because these nuances compound "
        "rather than stand alone, which is the deck's actual thesis.</p>")
    html.append("<div class='box good'>The headline the S&amp;OP pages carry: <b>nameplate capacity of this mix %.1f t a "
                "month; at the rate the plan realises, %.1f t</b>. The difference is the cleaning this mix requires, and it "
                "belongs inside the envelope, not as a footnote beneath it. The bottleneck for this mix is the %s &mdash; "
                "and a different mix moves it.</div>"
                % (f["nameplateT"], f["realisedT"], str(f["bottleneck"]).lower()))
    html.append(fig("capacity-0", "One tonnage number struck through, and the two products whose ranking reverses when "
                                  "margin is measured per bottleneck hour instead of per tonne."))

    # ---- the sixteen
    html.append("<h2 class='pb'>All sixteen nuances, and where each one lives</h2>")
    html.append(nuance_table(f))
    html.append(
        "<div class='box warn'><b>This is the column to validate with the product team.</b> The Configure and Extend routes "
        "are the deck's own, from slide 39, and the demo repeats them without arguing. Working through the Production "
        "Planner design documents while building this, two of them look well supported and five look like genuine new "
        "rules:<br><br>"
        "<b>Configure</b> &mdash; the cleaning matrix is a <i>changeover matrix by attribute</i>, which the planner already "
        "has; a forbidden pair is the only gap, because a cell that means &lsquo;never&rsquo; cannot be expressed as a very "
        "large changeover time without an optimiser eventually buying it. Hold times are <i>links with a minimum and a "
        "maximum lag</i>, which the design states outright.<br><br>"
        "<b>Extend</b> &mdash; yield and assay, utility concurrency with a duty profile, a daily effluent limit with "
        "carry-over, a licensed quantity per hazard class checked across time, and allocation on spec, route and remaining "
        "life. The sample input file in <code>data/planner-input.sample.json</code> writes this plant in the planner's own "
        "contract and lists each of these under <code>_extensions</code>, with the nuance it serves.</div>")

    # ---- how it works
    html.append("<h2>How the demo works, in one page</h2>")
    html.append(
        "<ul>"
        "<li><b>One scheduler, two rule sets.</b> Not two code paths: a set of capability flags that every rule site reads. "
        "The generic set keeps everything a real APS keeps &mdash; equipment non-overlap, eligibility, block times, batch "
        "sizes, due-date order, campaign grouping &mdash; and swaps only the seven rules the deck names. Forking the "
        "builder would be a straw man, and would deserve to be called one.</li>"
        "<li><b>Both plans face the same physics.</b> Every yield, assay, particle size and QC time is seeded on the product "
        "and which batch of it this is, never on the order the scheduler chose. Only the <i>reaction</i> to the assay "
        "differs. That one detail is what makes the comparison valid at all, and the verifier asserts the draws match.</li>"
        "<li><b>The consequence pass replays, it never re-schedules.</b> It walks the generic plan on its own timeline, "
        "rebuilds every clock and level from scratch, and prices what each assumption cost &mdash; with the aware plan's "
        "answer joined onto each row. Only the first-order consequence per batch is carried through to a status; the rest "
        "are priced and the unmodelled count is printed on screen.</li>"
        "<li><b>Everything is generated and re-based on today.</b> <code>python tools/generate_data.py</code> rewrites the "
        "whole dataset against the current date, so the demo is never stale. It checks its own output, and a separate gate "
        "fails the build if the data stops giving the claims anything to bite on.</li>"
        "<li><b>It runs with no server and no internet.</b> Fonts, icons and every library are vendored; a verifier fails "
        "the build if any request leaves the site. The whole comparison computes in about %d ms in the browser.</li>"
        "</ul>" % f["ms"])
    html.append(fig("cleaning-0", "The cleaning matrix is a view of a rule, not a table someone types: grades are derived "
                                  "from attributes, with the plant's own validated overrides marked."))
    html.append(fig("stages-0", "Hold times as the planner states them: links with a minimum and a maximum lag, and a clock "
                                "showing how much of each window the plan used."))

    # ---- what it does not do
    html.append("<h2 class='pb'>What this demo does not do</h2>")
    html.append(
        "<p>Worth saying before a prospect finds it.</p>"
        "<ul>"
        "<li><b>It is not their plant.</b> Every product, customer, volume and capacity is generated. What is real is the "
        "shape of the rules and the fact that the plan obeys them. Master Data is the front door: the matrix, the windows, "
        "the caps, the licensed quantities and the customers' specs are all uploadable, and the plant re-plans from the "
        "change in the room.</li>"
        "<li><b>It plans one site in detail.</b> The other sites exist so that sourcing and site approval are real choices, "
        "but they are S&amp;OP-level only.</li>"
        "<li><b>It models one consequence per batch.</b> A real plant's second- and third-order effects compound; the demo "
        "prices them and says how many it did not carry through, so the figure on screen is a floor rather than a worst case.</li>"
        "<li><b>Co-products and by-products are coarse.</b> A fixed ratio with a storage ceiling, not a yield model.</li>"
        "<li><b>It is not a costing engine.</b> The money is margin, the delay penalty and the value of an hour of the "
        "bottleneck. It is enough to rank decisions, not to close a month.</li>"
        "<li><b>The S&amp;OP horizon is arithmetic, not a second optimiser.</b> It uses the same masters and is calibrated "
        "from the detailed plan, which is why the two horizons reconcile &mdash; but it schedules nothing.</li>"
        "</ul>")

    # ---- questions
    html.append("<h2>Questions a prospect will ask</h2>")
    qs = [
        ("Is your generic plan a straw man?",
         "It is the same scheduler with the same objective weights, and it keeps every constraint a real APS keeps. Only "
         "the seven rules in the deck are swapped. The build itself enforces this: a fairness gate fails if the generic "
         "plan does not <i>win</i> the scoreboard it is normally reported against &mdash; and today it wins it by "
         "%.1f%% to %.1f%% on time. The assumption ratchet then proves the whole difference is seven identifiable "
         "assumptions, one switch at a time." % (f["genOtif"] * 100, f["awareOtif"] * 100)),
        ("Where did these numbers come from?",
         "Every parameter is generated and lives in one file; every figure on screen links back to the master row it came "
         "from. Nothing here claims to be chemistry &mdash; the demo asserts rules it was <i>given</i>, which is why the "
         "first question back is always &lsquo;give us your residue classes and your hold times&rsquo;."),
        ("Our cleaning matrix is different.",
         "Good &mdash; upload it. The grid on screen is a view of a rule over attributes, so a matrix with your residue "
         "classes produces a whole row and column for every product, including ones added afterwards. Change a cell and "
         "the cleaning hours <i>and</i> the campaign order both move."),
        ("Can it handle a product we add next month?",
         "Add it to the Products master with its attributes and its route. It inherits its eligible units from the charge "
         "volume, the material of construction and the containment class; its clean grades from family, solvent class, "
         "colour load and potency; its utility duty from the operation archetype times the charge; its effluent and its "
         "hazard class from the route. No mapping table anywhere. The demo shows exactly what was inherited."),
        ("Why is the recommended plan later than the generic one?",
         "Because it only counts what it can actually ship. The generic plan's delivery performance is built on allocating "
         "on quantity and date: %s kg of it would be rejected on the certificate of analysis. Honest allocation costs "
         "delivery on paper and saves it in fact." % "{:,}".format(int((f["byNuance"].get("P7") or {}).get("kg", 0)))),
        ("How long to make this our plant?",
         "Eight masters carry the demonstration: products and their attributes, routes with their hold windows, the "
         "cleaning overrides, equipment, utilities, waste limits, hazard ceilings and customers. Every one is an Excel "
         "round trip in the product. That is the Discovery conversation on slide 41, and the eight discovery questions on "
         "slide 40 are exactly the inputs it needs."),
    ]
    for q, a in qs:
        html.append("<div class='keep'><div class='q'>%s</div><p class='a'>%s</p></div>" % (q, a))

    html.append(fig("lots-0", "The blend arithmetic on screen: each lot against the order's window, weighted on active "
                              "content, and every refusal named."))
    html.append(fig("tanks-0", "The licensed quantity held day by day. The ceiling that refuses a tanker is the licence, "
                               "not the tank."))

    # ---- what we need
    html.append("<h2 class='pb'>What this needs from a customer</h2>")
    html.append(
        "<table><thead><tr><th>Master</th><th>What it is</th><th>Slide 39</th></tr></thead><tbody>"
        "<tr><td>Products and attributes</td><td>Family, solvent, colour or residue load, potency, charge volume, batch "
        "size, assay and impurity spec, retest period, price and cost</td><td><span class='tag tag-c'>Configure</span></td></tr>"
        "<tr><td>Routes and hold windows</td><td>The operations in order, hours each, and the minimum and maximum lag on "
        "each link</td><td><span class='tag tag-c'>Configure</span></td></tr>"
        "<tr><td>Cleaning overrides</td><td>The pairs your validation data treats differently from the derived rule, "
        "including any that are not permitted at all</td><td><span class='tag tag-c'>Configure</span></td></tr>"
        "<tr><td>Equipment</td><td>Class, block, working volume, material of construction, special service, and planned "
        "block times</td><td><span class='tag tag-c'>Configure</span></td></tr>"
        "<tr><td>Utilities</td><td>Hourly capacity per shared resource, any seasonal derate, and the duty each operation "
        "draws</td><td><span class='tag tag-e'>Extend</span></td></tr>"
        "<tr><td>Waste limits</td><td>The daily consented load per category, and your solvent recovery capacity and "
        "recovery band</td><td><span class='tag tag-e'>Extend</span></td></tr>"
        "<tr><td>Hazard ceilings</td><td>Licensed quantity per class, the bunds, and the segregation rules</td>"
        "<td><span class='tag tag-e'>Extend</span></td></tr>"
        "<tr><td>Customers</td><td>Approved sites and routes, COA requirement, and the minimum remaining shelf life each "
        "one insists on</td><td><span class='tag tag-e'>Extend</span></td></tr>"
        "</tbody></table>")
    html.append(fig("masters-0", "Master Data. Every master carries its provenance and its Configure or Extend route; the "
                                 "eight that carry the demonstration are an Excel round trip that re-plans the plant."))

    html.append(
        "<div class='box'><b>Verifying it yourself.</b> From the repository: <code>node tools/verify_engine.js</code> "
        "re-checks every constraint by rebuilding the series from the plan's output rather than from the scheduler's own "
        "buckets, for every preset; <code>node tools/verify_tension.js</code> checks the data still gives every claim "
        "something to bite on; <code>python tools/verify.py</code> loads all fifteen pages headless and fails if anything "
        "reaches for the network; <code>python tools/verify_flows.py</code> runs all sixteen scenario cards end to end; "
        "<code>python tools/verify_masters.py</code> does the Excel round trip on every uploadable master, including the "
        "refusals; <code>python tools/audit.py</code> checks that every figure shown on more than one page is the same "
        "number.</div>")

    html.append("</body></html>")
    return "".join(html)
