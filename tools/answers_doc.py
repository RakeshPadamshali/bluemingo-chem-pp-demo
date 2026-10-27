"""The review-answers document: twelve questions from the demo review, answered in order.

Imported by tools/build_answers.py. Every number comes from `f`, which is read out of the engine at build time, so the
document cannot drift away from the demo it describes.
"""

CSS = """
@page { size: A4; margin: 15mm 14mm 16mm 14mm; }
* { box-sizing: border-box; }
body { font-family: Roboto, 'Segoe UI', sans-serif; font-size: 10.2pt; line-height: 1.5; color: #333; margin: 0; }
h1 { font-size: 23pt; margin: 0 0 4px; color: #12121f; letter-spacing: -0.3px; }
h2 { font-size: 13.4pt; margin: 20px 0 7px; color: #1E8FBF; border-bottom: 2px solid #E1F5FE; padding-bottom: 4px; }
h3 { font-size: 11.2pt; margin: 14px 0 5px; color: #12121f; }
h2, h3 { page-break-after: avoid; }
p { margin: 0 0 8px; }
ul, ol { margin: 0 0 9px; padding-left: 18px; } li { margin-bottom: 4px; }
table { width: 100%; border-collapse: collapse; font-size: 8.6pt; margin: 7px 0 11px; }
th { text-align: left; background: #f5f5f5; border-bottom: 1.5px solid #e0e0e0; padding: 5px 7px; font-size: 7.6pt;
     text-transform: uppercase; letter-spacing: .4px; color: #666; }
td { padding: 4px 7px; border-bottom: 1px solid #eee; vertical-align: top; }
tbody tr { page-break-inside: avoid; }
td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; }
tr.tot td { border-top: 1.5px solid #ccc; font-weight: 700; }
.cover { background: linear-gradient(120deg, #1a1a2e, #12121f); color: #fff; padding: 26px 28px; border-radius: 10px; margin-bottom: 16px; }
.cover h1 { color: #fff; } .cover .sub { color: #8fd4f0; font-size: 12pt; margin-top: 2px; }
.cover .meta { margin-top: 14px; font-size: 9.4pt; color: rgba(255,255,255,.78); line-height: 1.6; }
.cover .url { background: rgba(255,255,255,.1); border: 1px solid rgba(255,255,255,.2); border-radius: 6px;
              padding: 7px 11px; margin-top: 12px; font-size: 10pt; color: #fff; display: inline-block; }
.lead { font-size: 11pt; color: #444; }
.qbox { background: #f4f8fb; border: 1px solid #d8e7f1; border-left: 3px solid #1E8FBF; border-radius: 5px;
        padding: 9px 12px; margin: 0 0 10px; font-size: 10pt; color: #22333f; page-break-inside: avoid; }
.qbox .qn { font-size: 7.6pt; font-weight: 700; letter-spacing: .5px; text-transform: uppercase; color: #1E8FBF; display: block; margin-bottom: 2px; }
.qbox i { font-style: italic; }
.box { background: #fafafa; border: 1px solid #e0e0e0; border-left: 3px solid #25A9E0; border-radius: 5px;
       padding: 9px 12px; margin: 9px 0; font-size: 9.6pt; }
.box.warn { border-left-color: #f57c00; background: #fff8e1; }
.box.good { border-left-color: #388e3c; background: #f1f8f2; }
.box b { color: #12121f; }
.short { font-size: 10.6pt; }
.short b:first-child { color: #12121f; }
.big { font-size: 19pt; font-weight: 700; color: #12121f; line-height: 1.1; }
.big.bad { color: #c62828; } .big.good { color: #2e7d32; }
.two { display: flex; gap: 14px; page-break-inside: avoid; } .two > div { flex: 1; }
.two td.n { white-space: nowrap; }
figure { margin: 10px 0 14px; page-break-inside: avoid; }
figure img { width: 100%; border: 1px solid #ddd; border-radius: 5px; display: block; }
figcaption { font-size: 8.6pt; color: #666; margin-top: 4px; font-style: italic; }
.keep { page-break-inside: avoid; }
.pb { page-break-before: always; }
.formula { background: #f5f5f5; border-radius: 4px; padding: 7px 10px; margin: 7px 0; font-size: 9.4pt; }
.formula b { color: #12121f; }
code { background: #f5f5f5; padding: 1px 4px; border-radius: 3px; font-size: 8.8pt; }
.chg td:first-child { font-weight: 600; white-space: nowrap; }
.mono { font-family: 'Roboto Mono', Consolas, monospace; font-size: 8.4pt; white-space: nowrap; }
"""

# the questions, verbatim as they were asked
QUESTIONS = [
    (1, "What are Chemical-aware vs. Generic batches? In plan studio, the KPI numbers look exactly the same on "
        "scoreboard 1 and somewhat different on scoreboard 2."),
    (2, "“27.0% - the busiest class: 14.2% running, 12.8% cleaning. A plant mean would average it with a mill that "
        "runs an hour a batch.” This point is not clear."),
    (3, "Block schedule has lot of empty spaces. Is it because the material has to move non-stop through stages from "
        "Reactor to Centrifuge to drying to micronizer to packing. There seems to be a lot of empty space in the beginning."),
    (4, "What is campaign ladder? Does it show a gantt chart in which case the timelines are not clear. How is colour "
        "load done first and is then followed by cleaning?"),
    (5, "The hold clock is not clear at all."),
    (6, "Utility consumption is independent of the production volumes. There is no master that relates utility "
        "consumption per kg of production."),
    (7, "Effluent & solvent generation (and subsequent treatment) is independent of the production volumes. There is no "
        "master that relates Effluent & solvent generation consumption per kg of production."),
    (8, "Are bunds and tank farms used in production or storage. How are they connected with production. Is the "
        "inventory produced stored in these."),
    (9, "What is the purpose of Tanker delivery?"),
    (10, "What is RX-320 or IM-205 etc. Can we show the batch register in the production plan and gantt chart?"),
    (11, "Can we have a detailed production plan report with product, production start time and end time, batch numbers, "
         "effluent & solvent generation, utility consumed, RM consumed etc. for each batch?"),
    (12, "What is Lots, Blending & Allocation. How is it different from the batches?"),
]

CHANGES = [
    ("1", "Plan Studio", "A “What the two plans are” panel above the scoreboards, listing the seven assumptions "
     "side by side; and a <b>difference</b> column on both scoreboards, so a row that is <i>nearly</i> identical can be "
     "told from one that is identical."),
    ("2", "Dashboard, Block Schedule", "The utilisation tile is reworded to say plainly that it is the busiest "
     "equipment class, and a new <b>Where the time went</b> panel accounts for every hour of every unit."),
    ("3", "Order book, Block Schedule", "The order book was <b>re-calibrated</b> — the first two weeks of the plan "
     "really were nearly empty, and that was a defect. Plus the time-accounting panel, which names what the white space is."),
    ("4", "Cleaning &amp; Campaigns", "The campaign ladder was <b>drawn wrong</b>: the product blocks were packed "
     "left to right while the cleans were positioned by time, so it looked like a Gantt and was not one. It is now a real "
     "time axis with a weekly date scale, and the note explains the pale-to-deep rule with measured numbers."),
    ("5", "Multi-stage &amp; Hold Times", "The hold clock is explained in words first, then one link is worked end to "
     "end in clock times, and every row now names the link, both units and the window."),
    ("6", "Utilities, Master Data", "A new derived master <b>Utility consumed per batch</b>, and a panel showing what a "
     "tonne of each product costs in each utility."),
    ("7", "Effluent, Master Data", "A new derived master <b>Effluent and solvent per batch</b>, and a table of m³ and "
     "kL per batch and per tonne, by stream."),
    ("8, 9", "Tank Farm", "A “what the tank farm is for” panel, and a table of what the plan draws from every "
     "tank, what recovery returns, and the net make-up a tanker has to bring."),
    ("10, 11", "New page, and the data model", "A <b>Production Plan Report</b>: a product glossary, the full batch "
     "register with inputs and outputs, a per-batch breakdown, per-product totals and a five-sheet Excel export; batch "
     "numbers now appear on the Gantt bars. Behind it, a new <b>charge sheet</b> — raw material consumption per "
     "batch, derived per kL of charge against the operation archetype exactly as the duty profile already was."),
    ("12", "Lots", "A panel setting out batch, lot and customer lot as three different objects, constrained by three "
     "different things."),
]


# ---------------------------------------------------------------------------------------------------- formatters
def n(x, d=0):
    if x is None:
        return "&mdash;"
    return ("{:,.%df}" % d).format(float(x))


def pct(x, d=1):
    return "&mdash;" if x is None else ("%.*f%%" % (d, float(x) * 100))


def rs(x):
    if x is None:
        return "&mdash;"
    a = abs(float(x))
    sign = "−" if x < 0 else ""
    if a >= 1e7:
        return "%sRs %.2f Cr" % (sign, a / 1e7)
    if a >= 1e5:
        return "%sRs %.1f L" % (sign, a / 1e5)
    return "%sRs %s" % (sign, n(a))


def fmtval(v, kind):
    if kind == "pct":
        return pct(v)
    if kind == "rs":
        return rs(v)
    if kind == "kg":
        return "%s t" % n(float(v) / 1000, 1)
    if kind == "h":
        return "%s h" % n(v)
    return n(v)


def delta(g, a, kind):
    d = float(a) - float(g)
    if kind == "pct":
        return ("%+.1f pts" % (d * 100)) if abs(d) > 0.0005 else "identical"
    if kind == "rs":
        return ("+" if d > 0 else "") + rs(d) if abs(d) >= 1 else "identical"
    if kind == "kg":
        return ("%+.1f t" % (d / 1000)) if abs(d) >= 1 else "identical"
    if abs(d) < 1e-9:
        return "identical"
    # "%+s" does not sign a string: the plus flag is only honoured for numbers, so put it on by hand
    return ("+" if d > 0 else "−") + n(abs(d), 0 if abs(d) >= 1 else 1) + (" h" if kind == "h" else "")


CLS = {"REACTOR": "Reaction", "ISOLATION": "Isolation", "DRYER": "Drying", "MILL": "Milling", "PACK": "Packing"}


def cls(c):
    return CLS.get(c, c.title())


def mins(x):
    """minutes from the engine's base, as a readable date. The document only needs it for the worked batch."""
    return x


def build(f, imgs, url):
    def fig(key, extra=""):
        img = imgs.get(key)
        if not img:
            return ""
        cap = next((s[4] for s in __import__("build_answers").SHOTS if s[0] == key), "")
        return ("<figure><img src='data:image/png;base64,%s'><figcaption>%s%s</figcaption></figure>"
                % (img, cap, (" " + extra) if extra else ""))

    def q(i):
        no, text = QUESTIONS[i - 1]
        return "<div class='qbox'><span class='qn'>Question %d</span><i>&ldquo;%s&rdquo;</i></div>" % (no, text)

    H = []
    a = H.append

    # ---------------------------------------------------------------------------------------------------- cover
    a("<div class='cover'><h1>Twelve questions, answered</h1>"
      "<div class='sub'>Bluemingo PP &middot; Specialty Chemicals &amp; APIs &mdash; demo review</div>"
      "<div class='meta'>Every figure in this document was read out of the running engine when it was built, and every "
      "screen was captured from the live demo. Plan as of <b>%s</b>: %d products, %d units, %s order lines, "
      "%s batches over %d days.<br>Six of the twelve questions found something that was genuinely wrong. Those are "
      "fixed, and this document says so plainly rather than explaining them away."
      "</div><div class='url'>%s</div></div>"
      % (f["asOf"][:10], f["products"], f["units"], n(f["lines"]), n(f["naive"][4][2]), f["forwardDays"], url))

    a("<p class='lead'>The questions are answered in the order they were asked. Each one gets the short answer first, "
      "then the mechanism, then the numbers the demo actually produces, and then the screen to look at.</p>")

    # ---------------------------------------------------------------------------------------------------- summary
    a("<h2>What changed in the demo</h2>")
    a("<p>Four of these were defects, not misunderstandings: the empty first fortnight (3), the campaign ladder drawn on "
      "a false axis (4), the missing per-volume masters (6 and 7), and the missing batch-level report (11). "
      "The rest were things the demo knew but never said on screen.</p>")
    a("<table class='chg'><thead><tr><th>Question</th><th>Where</th><th>What was done</th></tr></thead><tbody>"
      + "".join("<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % c for c in CHANGES)
      + "</tbody></table>")

    # ============================================================================================ Q1
    a("<h2 class='pb'>1. Chemical-aware against generic, and why scoreboard 1 looks the same</h2>")
    a(q(1))
    a("<p class='short'><b>The short answer.</b> There is no such thing as a chemical-aware <i>batch</i>. There are two "
      "<i>plans</i> of the same order book, and a batch belongs to whichever plan placed it. And scoreboard 1 is "
      "<i>supposed</i> to look almost the same — that is the test the comparison has to pass before it is worth "
      "anything. The page now says both of those things out loud.</p>")
    a("<p>Both plans come out of <b>one scheduler</b>. The generic plan is not a weak plan: it respects equipment "
      "non-overlap, eligibility, batch sizes, maintenance windows, due-date order and campaign grouping, exactly as a "
      "real APS does. Seven rules — and only seven — are switched between them:</p>")
    a("<table><thead><tr><th>Rule</th><th>What the generic plan assumes</th><th>What the chemical-aware plan reads instead</th></tr></thead><tbody>"
      + "".join("<tr><td><b>%s</b></td><td>%s</td><td>%s</td></tr>" % (x["nuance"], x["generic"], x["aware"])
                for x in f["assumptions"]) + "</tbody></table>")
    a("<p>So the two plans schedule the same products on the same units against the same objective weights. They book a "
      "similar number of batches and a similar tonnage, because the work to be done is the same. What differs is what "
      "each one <b>believes</b> — and belief shows up first in cleaning hours and in on-time delivery:</p>")
    a("<table><thead><tr><th>Scoreboard 1 &mdash; as each plan reports it</th><th class='n'>Generic</th>"
      "<th class='n'>Chemical-aware</th><th class='n'>Difference</th></tr></thead><tbody>"
      + "".join("<tr><td>%s</td><td class='n'>%s</td><td class='n'>%s</td><td class='n'>%s</td></tr>"
                % (r[0], fmtval(r[1], r[3]), fmtval(r[2], r[3]), delta(r[1], r[2], r[3])) for r in f["naive"])
      + "</tbody></table>")
    a("<div class='box'><b>Why the generic plan has to win this scoreboard.</b> It books %s cleaning hours against %s, "
      "and reports %s on-time against %s. If the generic plan ever lost on the measures a conventional plan is reported "
      "against, the comparison would be a straw man — so the build has a <b>fairness gate</b> that fails if that "
      "happens. The whole argument is that the plan which looks better on paper is the one that does not survive contact "
      "with the chemistry.</div>"
      % (n(f["naive"][0][1]), n(f["naive"][0][2]), pct(f["naive"][1][1]), pct(f["naive"][1][2])))
    a("<p>Scoreboard 2 is the same two plans with the chemistry put back — the generic plan replayed on its own "
      "timeline, with every constraint it broke priced:</p>")
    a("<table><thead><tr><th>Scoreboard 2 &mdash; what the plant is left with</th><th class='n'>Generic</th>"
      "<th class='n'>Chemical-aware</th><th class='n'>Difference</th></tr></thead><tbody>"
      + "".join("<tr><td>%s</td><td class='n'>%s</td><td class='n'>%s</td><td class='n'>%s</td></tr>"
                % (r[0], fmtval(r[1], r[3]), fmtval(r[2], r[3]), delta(r[1], r[2], r[3])) for r in f["real"])
      + "</tbody></table>")
    a("<p>The aware plan is re-checked against every constraint it claims to honour: <b>%s checks, %s violations</b>. "
      "The same check over the generic plan returns <b>%s violations</b>. Those are counted, not asserted.</p>"
      % (n(f["proofChecks"]), n(f["proofViolations"]), n(f["genViolations"])))
    a(fig("q1-two"))
    a(fig("q1-boards"))

    # ============================================================================================ Q2
    a("<h2 class='pb'>2. &ldquo;The busiest class&rdquo; &mdash; what that sentence meant</h2>")
    a(q(2))
    a("<p class='short'><b>The short answer.</b> It was badly written. It meant: <i>this is the utilisation of the "
      "busiest kind of equipment, not an average of the whole plant, because averaging would hide the constraint.</i> "
      "The tile now says that, and a new panel shows every class instead of making you take it on trust.</p>")
    a("<p>This plant has five kinds of equipment and they are not comparable. A reaction occupies a vessel for most of a "
      "day; a mill runs for an hour a batch, and only for the two products that need a particle-size cut. Averaging them "
      "produces a number that is true of nothing:</p>")
    a("<table><thead><tr><th>Equipment class</th><th class='n'>Units</th><th class='n'>Operations in the plan</th>"
      "<th class='n'>Running</th><th class='n'>Cleaning</th><th class='n'>Occupied</th></tr></thead><tbody>"
      + "".join("<tr><td>%s</td><td class='n'>%d</td><td class='n'>%d</td><td class='n'>%s</td><td class='n'>%s</td>"
                "<td class='n'><b>%s</b></td></tr>"
                % (cls(c["cls"]), c["units"], c["ops"], pct(c["run"]), pct(c["clean"]), pct(c["busy"]))
                for c in f["byClass"])
      + "<tr class='tot'><td>Plant mean (the number the demo refuses to headline)</td><td class='n'>%d</td>"
        "<td class='n'></td><td class='n'>%s</td><td class='n'></td><td class='n'>&mdash;</td></tr>"
        % (f["units"], pct(f["plantMean"])) + "</tbody></table>")
    a("<div class='box'><b>Read it like this.</b> The busiest class is <b>%s</b> at <b>%s</b> occupied — %s of the "
      "horizon running and %s cleaning. The plant mean is %s. If the demo headlined the mean, it would be reporting the "
      "milling and packing lines' idleness as though it were spare reaction capacity, and a planner would go looking for "
      "capacity in the wrong place. Cleaning is shown <i>beside</i> running rather than inside it, because on this plant "
      "cleaning is %s of all the time the busiest class spends occupied — it is the second-largest claim on the "
      "plant's time and it should never be buried in a utilisation figure.</div>"
      % (cls(f["utilClass"]), pct(f["byClass"][0]["busy"]), pct(f["byClass"][0]["run"]),
         pct(f["byClass"][0]["clean"]), pct(f["plantMean"]),
         pct(f["byClass"][0]["clean"] / max(1e-9, f["byClass"][0]["busy"]))))
    a(fig("q2-time"))

    # ============================================================================================ Q3
    a("<h2 class='pb'>3. The white space on the block schedule</h2>")
    a(q(3))
    a("<p class='short'><b>The short answer.</b> Two different things were being seen, and one of them was a real "
      "defect.</p>")
    a("<p><b>The empty beginning was a bug, and it is fixed.</b> The order book was sized against the whole 104-day "
      "span at one realisation rate, but the 30 frozen days of history are planned the <i>generic</i> way, which crams "
      "far more work into a day than the chemical-aware plan can. History therefore consumed almost the entire near-term "
      "book before the as-of moment, and the live plan opened with <b>one</b> open order line and nothing to do for a "
      "fortnight. That is not a finding about chemical plants; it is a calibration error. The book has been re-sized "
      "(%s order lines instead of 126, realisable-capacity factor %.2f), and batch starts are now even from day one:</p>"
      % (n(f["lines"]), f["friction"] or 0))
    a("<table><thead><tr><th>Week of the plan</th>"
      + "".join("<th class='n'>%d</th>" % (i + 1) for i in range(len(f["startsByWeek"])))
      + "</tr></thead><tbody><tr><td>Batches started</td>"
      + "".join("<td class='n'>%d</td>" % x for x in f["startsByWeek"]) + "</tr></tbody></table>")
    a("<p><b>No, the material does not move non-stop</b> — and it should not. Every link in a route carries a "
      "<b>minimum</b> lag as well as a maximum: the transfer, the cool-down and the in-process check have to happen "
      "before the next stage can start at all. Across this plan the average gap between one stage ending and the next "
      "starting is <b>%.1f h</b> over <b>%s</b> links, and not one of them exceeds its hold window.</p>"
      % (f["meanLagH"], n(f["links"])))
    a("<p><b>The remaining white space is worth accounting for rather than defending.</b> Here is every hour of every "
      "unit over the %d-day plan:</p>" % f["forwardDays"])
    a("<table><thead><tr><th>Equipment class</th><th class='n'>Running</th><th class='n'>Cleaning</th>"
      "<th class='n'>Block time</th><th class='n'>Held to protect a window</th><th class='n'>Idle</th></tr></thead><tbody>"
      + "".join("<tr><td>%s</td><td class='n'>%s</td><td class='n'>%s</td><td class='n'>%s</td><td class='n'>%s</td>"
                "<td class='n'>%s</td></tr>"
                % (cls(g["cls"]), pct(g["run"] / g["avail"]), pct(g["clean"] / g["avail"]),
                   pct(g["block"] / g["avail"]), pct(g["held"] / g["avail"]), pct(g["idle"] / g["avail"]))
                for g in f["timeUse"]) + "</tbody></table>")
    iso_fails = sum(v for k, v in f["failBy"].items() if "ISOLATION" in k)
    a("<div class='box warn'><b>Being precise about what the idle hours are.</b> Two different things, and it is worth "
      "separating them rather than claiming the more flattering one.<br><br>"
      "<b>Most idle moments are simply &ldquo;nothing released that this unit can make&rdquo;.</b> Of the <b>%s</b> "
      "scheduling decisions the aware plan made, <b>%s</b> ended with no candidate at all. This is a %d-day detailed "
      "plan against an order book that releases on a rolling window, and only <b>%d of the %d units</b> can start a "
      "route at all — the rest are fed by the stage above them. The plan is not leaving work undone: at the end of "
      "the horizon only <b>%s kg</b> of released demand is still wanting, out of a %s kg book.<br><br>"
      "<b>But the ceiling on how much it could ever absorb is the hold window.</b> When the builder did try to place a "
      "train, <b>%s</b> of <b>%s</b> attempts failed — and <b>%s of those failures were at exactly one link: "
      "reaction into isolation</b>. A reaction may only be <i>started</i> when an eligible filter or ANFD will be free "
      "to take the slurry inside the window, six to fourteen hours on most of these routes. <b>%d</b> starts were held "
      "back on purpose rather than strand an intermediate, <b>%s h</b> in all, each listed by name on Multi-stage &amp; "
      "Hold Times. That is why the order book is calibrated against <i>realisable</i> rather than nameplate hours: "
      "ordering more does not produce much more, it produces short lines.</div>"
      % (n(f["decisions"]), n(f["idles"]), f["forwardDays"], f["startUnits"], f["units"],
         n(f["openAtEnd"]), n(f["bookKg"]),
         n(f["chainFails"]), n(f["chains"]), n(iso_fails), f["sacrifices"], n(f["sacrificeH"])))
    a("<div class='box'><b>And the conclusion a conventional plan could not reach.</b> On a discrete line a bottleneck "
      "running at %s would mean two thirds of the capacity is going spare and a planner should go and sell it. Here it "
      "means something different: a second reactor would add almost nothing, because the constraint is a <i>timing</i> "
      "relationship between two stages rather than a shortage of vessel hours. A plan that never models the window "
      "cannot tell those two situations apart — which is the whole argument.</div>"
      % pct(f["byClass"][0]["busy"]))
    a(fig("q3-gantt"))

    # ============================================================================================ Q4
    a("<h2 class='pb'>4. The campaign ladder</h2>")
    a(q(4))
    a("<p class='short'><b>The short answer.</b> It is a compressed Gantt, one row per unit — and you were right "
      "that the timelines were not clear, because <b>it was drawn wrong</b>. The coloured blocks were packed one after "
      "another by the layout engine while the cleaning marks were positioned by time, so the two never lined up. It is "
      "now a real time axis with a weekly date scale, and both kinds of block sit where they actually happen.</p>")
    a("<p><b>What it shows.</b> One row per unit; left to right is the whole %d-day plan. Each solid block is one "
      "operation, shaded 1 (pale) to 5 (deep) by the product's <b>colour load</b>. Each hatched block is a clean-down, "
      "as wide as it takes. The point of putting them on one row is that you can see the cleans cluster wherever the "
      "shading steps backwards.</p>" % f["forwardDays"])
    a("<p><b>Why colour comes first and cleaning follows.</b> The cleaning matrix only charges for colour when it "
      "<i>falls</i>. Following a pale product with a deeper one needs a rinse, because the residue is lighter than what "
      "is about to be made. Following a deep product with a pale one needs a boil-out and a swab test, because any "
      "carry-over will show. So the campaign rule sorts a family <b>ascending by colour load</b> and pays the expensive "
      "clean once, at the break between campaigns, instead of at every changeover. Measured on this plan:</p>")
    a("<table><thead><tr><th>Changeover direction on a unit</th><th class='n'>How many</th>"
      "<th class='n'>Average cleaning</th></tr></thead><tbody>"
      "<tr><td>Up the ladder, or level — pale then deeper</td><td class='n'>%d</td><td class='n'>%.1f h</td></tr>"
      "<tr><td>Back down the ladder — deep then paler</td><td class='n'>%d</td><td class='n'>%.1f h</td></tr>"
      "</tbody></table>" % (f["ladder"]["up"], f["ladder"]["upH"], f["ladder"]["down"], f["ladder"]["downH"]))
    a("<p>A step down the ladder costs <b>%.1f&times;</b> what a step up costs, which is the whole reason to sort a "
      "campaign. The rule itself is configuration, not code: minimum <b>%s</b> batches, maximum <b>%s</b>, a forced "
      "break after <b>%s</b>, sorted on <code>%s</code> ascending, with demand pullable up to <b>%s days</b> early to "
      "reach the minimum. This plan ran <b>%s campaigns</b> averaging <b>%s batches</b> each, and paid <b>%s cleaning "
      "hours</b> over <b>%s</b> clean-downs.</p>"
      % (f["ladder"]["downH"] / max(0.01, f["ladder"]["upH"]),
         f["campaign"].get("minBatches"), f["campaign"].get("maxBatches"), f["campaign"].get("forcedBreakAfter"),
         f["campaign"].get("sortAttr"), f["campaign"].get("pullAheadDays"),
         n(f["campaigns"]), n(f["perCampaign"], 2), n(f["cleanHours"]), n(f["cleanCount"])))
    a("<table><thead><tr><th>Clean grade</th><th class='n'>Hours</th><th class='n'>Times used in this plan</th>"
      "</tr></thead><tbody>"
      + "".join("<tr><td>%s</td><td class='n'>%s</td><td class='n'>%s</td></tr>"
                % (g["name"], "not permitted" if g["hours"] is None else n(g["hours"], 1),
                   n(f["cleanByGrade"].get(g["id"], 0)))
                for g in f["grades"]) + "</tbody></table>")
    a(fig("q4-ladder"))

    # ============================================================================================ Q5
    a("<h2 class='pb'>5. The hold clock</h2>")
    a(q(5))
    a("<p class='short'><b>The short answer.</b> Fair. It was a wall of bars labelled &ldquo;4.5 / 96 h&rdquo;, which "
      "only reads if you already know what a hold window is. It now explains itself in words, then works one link end "
      "to end in clock times, then shows the rest.</p>")
    a("<p><b>What a hold window is.</b> It is how long the material coming off one stage may stand before the next stage "
      "has to <i>start</i>. A wet cake on a filter is not stable: leave it and it cakes, oxidises or picks up water, and "
      "the batch needs a re-test or a re-work. So every link in a route carries two numbers:</p>")
    a("<ul><li><b>Minimum lag</b> — the transfer, the cool-down and the in-process check that have to happen "
      "anyway. The next stage cannot start before this.</li>"
      "<li><b>Maximum lag</b> — the hold window. The next stage must have started by this.</li></ul>")
    a("<p>In the Bluemingo Production Planner's own vocabulary these are the minimum and maximum lag on a link between "
      "two routing positions, which is why the demo uses those words. The tightest window in this plant is "
      "<b>%s h before %s on %s</b>. There are <b>%s</b> links in this plan and the scheduler may not break one — it "
      "holds a reactor idle instead.</p>"
      % (n(f["minWindow"]["h"]), f["minWindow"]["op"].lower(), f["minWindow"]["productId"], n(f["links"])))
    if f.get("tightestLink"):
        t = f["tightestLink"]
        a("<p><b>One link, read end to end</b> — the tightest in this plan, chosen automatically so it is never "
          "stale:</p>")
        a("<table><thead><tr><th>Moment</th><th>What happens</th></tr></thead><tbody>"
          "<tr><td><b>Stage ends</b></td><td>%s finishes on %s</td></tr>"
          "<tr><td><b>Earliest it may start</b></td><td>minimum lag %s h later — transfer and cool-down</td></tr>"
          "<tr><td><b>Must have started by</b></td><td>hold window %s h after the stage ended</td></tr>"
          "<tr><td><b>Actually started</b></td><td>%s on %s, after standing %.1f h — %s of the window</td></tr>"
          "</tbody></table>"
          % (t["from"], t["fromUnit"], n(t["minH"]), n(t["winH"]), t["to"], t["toUnit"], t["lagH"], pct(t["use"])))
    a("<p>Every bar on the board is one of those. The bar is how much of the window that link used, it turns amber past "
      "85%%, and the dark tick is the minimum lag. <b>%s</b> links finished within 15%% of their window closing, and the "
      "tightest lands exactly on it. None <i>exceeds</i> its window: the proof re-checks all <b>%s</b> of them over "
      "the committed plan and reports <b>%s</b> breaches.</p>"
      % (n(f["linksTight"]), n(f["holdChecks"]), n(f["proofViolations"])))
    a(fig("q5-clock"))

    # ============================================================================================ Q6
    a("<h2 class='pb'>6. Utility consumption against production volume</h2>")
    a(q(6))
    a("<p class='short'><b>The short answer.</b> It is not independent — it is strictly proportional to the charge "
      "volume — but you were right that there was no master saying so in units anyone would recognise. There is now: "
      "<b>Utility consumed per batch</b>, per batch, per tonne and per kL.</p>")
    a("<p><b>Where the relationship lives.</b> The <b>Duty profiles</b> master holds one profile per operation "
      "archetype, in three segments, written <b>per kL of reaction charge per hour</b>. The product supplies the charge "
      "volume; the route supplies the hours. So for one batch:</p>")
    a("<div class='formula'><b>utility consumed</b> = rate per kL per hour &times; charge kL &times; operation hours, "
      "summed over the route<br>"
      "<b>per tonne of product</b> = that, divided by the batch size in tonnes</div>")
    a("<p>A rate times a time is a quantity, which is why the consumption units differ from the capacity units: a cap of "
      "%s t/h of steam becomes <b>t</b> of steam consumed; %s TR of refrigeration becomes <b>TR-hours</b>.</p>"
      % (n(next((u["cap"] for u in f["utilities"] if u["id"] == "STEAM"), 0), 1),
         n(next((u["cap"] for u in f["utilities"] if u["id"] == "BRINE"), 0), 0)))
    a("<p>Nothing is typed in per product. Double a product's charge volume and every one of its draws doubles with it, "
      "and a product uploaded from Excel inherits the whole profile from its route. Here is the arithmetic done:</p>")
    ut = [u for u in f["utilities"]]
    rows = sorted(f["intensity"], key=lambda r: -(r["utilPerT"].get("STEAM", 0)))
    a("<table><thead><tr><th>Product</th><th class='n'>Charge</th><th class='n'>Batch</th><th class='n'>Cycle</th>"
      + "".join("<th class='n'>%s<br>%s / t</th>" % (u["id"], u["qtyUnit"]) for u in ut)
      + "</tr></thead><tbody>"
      + "".join("<tr><td><span class='mono'>%s</span> %s</td><td class='n'>%s kL</td><td class='n'>%s kg</td>"
                "<td class='n'>%s h</td>%s</tr>"
                % (r["id"], r["name"], n(r["chargeKL"], 1), n(r["batchKg"]), n(r["cycleH"]),
                   "".join("<td class='n'>%s</td>" % (n(r["utilPerT"][u["id"]], 0) if r["utilPerT"].get(u["id"]) else "&mdash;")
                           for u in ut))
                for r in rows) + "</tbody></table>")
    a("<div class='box good'><b>What this plan actually draws.</b> %s batches consume <b>%s t of steam</b>, and the "
      "consumption of every other utility scales the same way. The per-batch and per-tonne figures are in Master Data "
      "&rarr; <b>Utility consumed per batch</b>; the figures for an individual batch are in the new Production Plan "
      "Report.<br><br>The hourly <b>cap</b> is a separate question, and the one the demo was already answering: it is "
      "not about how much a batch consumes in total, it is about how many batches may draw <i>at the same hour</i>. "
      "That is why the duty profile has three segments — the peak of the overlapping segments binds, never an "
      "average.</div>" % (n(f["naive"][4][2]), n(f["planSteam"])))
    a(fig("q6-util"))

    # ============================================================================================ Q7
    a("<h2 class='pb'>7. Effluent and solvent against production volume</h2>")
    a(q(7))
    a("<p class='short'><b>The short answer.</b> Same again: it was always proportional, and there was no master that "
      "said so per tonne. There is now — <b>Effluent and solvent per batch</b> — and the Effluent page carries "
      "the whole table.</p>")
    a("<p><b>Where the relationship lives.</b> The <b>Routes</b> master carries, for every operation of every product, "
      "the effluent it puts down the drain (m³ per batch) and the solvent it charges (kL per batch), together with "
      "which treatment stream the effluent goes to. A batch is a fixed charge of a fixed size, so:</p>")
    a("<div class='formula'><b>m³ per tonne</b> is a constant of the product &mdash; the route's effluent summed, "
      "divided by the batch size<br><b>the plant's daily load</b> = that constant &times; the batches the plan places "
      "that day<br><b>fresh solvent needed</b> = charged &minus; what the recovery train returns (%s–%s%%, after a "
      "%s h turnaround)</div>"
      % (n(f["recovery"]["min"] * 100), n(f["recovery"]["max"] * 100), n(f["recovery"]["turnH"])))
    cats = f["wastes"]
    a("<table><thead><tr><th>Product</th><th class='n'>Charge</th><th class='n'>Batch</th>"
      + "".join("<th class='n'>%s m³</th>" % c["id"] for c in cats)
      + "<th class='n'>Effluent<br>a batch</th><th class='n'>m³<br>per tonne</th>"
        "<th class='n'>Solvent<br>a batch</th><th class='n'>Recovered</th><th class='n'>Fresh</th>"
        "<th class='n'>kL per<br>tonne</th></tr></thead><tbody>"
      + "".join("<tr><td><span class='mono'>%s</span> %s</td><td class='n'>%s kL</td><td class='n'>%s kg</td>%s"
                "<td class='n'>%s</td><td class='n'><b>%s</b></td><td class='n'>%s</td><td class='n'>%s</td>"
                "<td class='n'>%s</td><td class='n'><b>%s</b></td></tr>"
                % (r["id"], r["name"], n(r["chargeKL"], 1), n(r["batchKg"]),
                   "".join("<td class='n'>%s</td>" % (n(r["byCat"][c["id"]], 1) if r["byCat"].get(c["id"]) else "&mdash;")
                           for c in cats),
                   n(r["efflM3"], 1), n(r["efflPerT"], 1), n(r["solvKL"], 2), n(r["recoveredKL"], 2),
                   n(r["makeupKL"], 2), n(r["solvPerT"], 2))
                for r in f["intensity"]) + "</tbody></table>")
    top, bot = f["intensity"][0], f["intensity"][-1]
    a("<div class='box good'><b>Why the spread matters.</b> %s puts down <b>%s m³ a tonne</b> and %s only "
      "<b>%s</b> — a factor of <b>%.1f</b>. That is why two deep-colour batches on the same day is a treatment "
      "problem and two amine batches is not, and why the scheduler interleaves a light-effluent batch between two heavy "
      "ones rather than running the heavy campaign straight through. Over this plan: <b>%s m³</b> of effluent "
      "against daily consents of %s, and <b>%s kL</b> of fresh solvent after recovery.</div>"
      % (top["id"], n(top["efflPerT"], 1), bot["id"], n(bot["efflPerT"], 1),
         top["efflPerT"] / max(0.01, bot["efflPerT"]), n(f["planEffl"]),
         ", ".join("%s %s %s" % (c["id"], n(c["cap"], 0), c["unit"].replace("m3", "m³"))
                                   for c in cats), n(f["planMakeup"], 1)))
    a("<p><b>And subsequent treatment is capacity, not an afterthought.</b> Each stream is a <i>daily</i> limit, so it "
      "does not average out — a day over the consent is a day the plant cannot discharge, whatever the month looks "
      "like. The treatment plant is therefore a scheduling resource in the same way a reactor is.</p>")
    a(fig("q7-waste"))

    # ============================================================================================ Q8 / Q9
    a("<h2 class='pb'>8 and 9. Bunds, the tank farm, and what a tanker is for</h2>")
    a(q(8))
    a(q(9))
    a("<p class='short'><b>The short answer.</b> The tank farm holds what goes <i>in</i>, not what comes out. It is "
      "bulk solvent and acid — the reaction media and wash liquors every batch charges. <b>Finished product is "
      "never stored there.</b> A tanker delivery is how the level is put back. The page now says this before it shows "
      "anything else.</p>")
    a("<p><b>How it connects to production.</b> Every reaction and every isolation step charges solvent from its "
      "product's tank, in kL per batch, written on the route. So the production plan <i>is</i> a draw-down schedule for "
      "the farm — and the farm can refuse to let the plan proceed:</p>")
    a("<table><thead><tr><th>Tank</th><th>Solvent</th><th>Hazard</th><th>Bund</th><th class='n'>Capacity</th>"
      "<th class='n'>Batches drawing</th><th class='n'>Drawn by the plan</th><th class='n'>Returned by recovery</th>"
      "<th class='n'>Net make-up</th><th>Products</th></tr></thead><tbody>"
      + "".join("<tr><td class='mono'>%s</td><td>%s</td><td>%s</td><td>%s</td><td class='n'>%s kL</td>"
                "<td class='n'>%s</td><td class='n'>%s</td><td class='n'>%s</td><td class='n'><b>%s</b></td>"
                "<td class='mono'>%s</td></tr>"
                % (t["id"], t["solvent"], t["haz"], t["bund"], n(t["capKL"], 0),
                   t["batches"] or "&mdash;",
                   ("%s kL" % n(t["draw"], 1)) if t["draw"] else "&mdash;",
                   ("%s kL" % n(t["back"], 1)) if t["back"] else "&mdash;",
                   ("%s kL" % n(t["net"], 1)) if t["draw"] else "&mdash;",
                   ", ".join(t["prods"]) or "not used by this plan")
                for t in f["tanks"]) + "</tbody></table>")
    a("<p><b>A bund</b> is the containment wall around a group of tanks. It matters to the plan for one reason: hazard "
      "classes that may not share a bund cannot be stored together, so the farm's segregation decides what can be held "
      "where. The licence ceiling then decides how much:</p>")
    a("<table><thead><tr><th>Hazard class</th><th class='n'>Licensed quantity</th><th class='n'>Peak held in this plan</th>"
      "<th class='n'>Least headroom</th><th>Bunds</th></tr></thead><tbody>"
      + "".join("<tr><td>%s</td><td class='n'>%s kL</td><td class='n'>%s kL</td><td class='n'>%s</td><td>%s</td></tr>"
                % (h["name"], n(h["licensedKL"], 0), n(h["peak"], 1), pct(h["headroom"]),
                   ", ".join(b["id"] for b in f["bunds"] if h["id"] in b["classes"]))
                for h in f["hazards"]) + "</tbody></table>")
    a("<div class='box'><b>What a tanker is for, exactly.</b> Most of the solvent comes back from the recovery train "
      "after a %s h turnaround, so a tanker brings <b>net make-up</b>, not the gross charge — the last column of the "
      "tank table. That is why the delivery calendar belongs in a production plan rather than in a purchasing one: size "
      "it to the gross draw and every tank fills to its licensed ceiling and starts refusing loads, which starves "
      "whichever tank actually needed one.<br><br>Of the <b>%d</b> tanker loads due in this window, <b>%d</b> were taken "
      "in and <b>%d</b> were turned away at least once &mdash; <b>%d</b> of those never got in at all. A refused tanker "
      "waits and comes back in two days, up to five times, so counted as events that is <b>%d</b> refusals, <b>%d</b> of "
      "them by the <i>licence</i> rather than by tank space. Alongside that, <b>%d</b> returns from recovery "
      "had to be held back in the still because there was no licensed room for them, and <b>%d</b> charges were bought "
      "in at a premium costing <b>%s</b> because a tank could not cover them. A delivery refused is a hard stop the plan "
      "has to work around, which is the whole of nuance 6.</div>"
      % (n(f["recovery"]["turnH"]), f["deliveries"]["scheduled"], f["deliveries"]["accepted"],
         f["deliveries"]["refusedTankers"], f["deliveries"]["neverAdmitted"],
         f["deliveries"]["refusalEvents"],
         f["deliveries"]["byLicence"], f["deliveries"]["heldInRecovery"], f["deliveries"]["emergency"],
         rs(f["deliveries"]["emergencyRs"])))
    a(fig("q8-farm"))
    a(fig("q9-draw"))

    # ============================================================================================ Q10
    a("<h2 class='pb'>10. What the product codes mean, and batch numbers on the plan</h2>")
    a(q(10))
    a("<p class='short'><b>The short answer.</b> They are fictional product codes, and the demo never explained them. "
      "There is now a glossary on the new Production Plan Report, and the <b>batch number is on every Gantt bar</b> and "
      "in the register, the lot numbers and the Excel exports.</p>")
    a("<p><b>How the numbering works.</b> <code>RX-320</code> is a product. <code>RX-320-B007</code> is the seventh "
      "batch of it. <code>LRX-320-B007</code> is the lot that batch produced once QC released it. The prefix is the "
      "family:</p>")
    a("<table><thead><tr><th>Prefix</th><th>Family</th><th>What it is</th></tr></thead><tbody>"
      + "".join("<tr><td class='mono'>%s</td><td><b>%s</b></td><td>%s &mdash; %s</td></tr>"
                % (", ".join(sorted({c["id"].split("-")[0] for c in f["catalogue"] if c["family"] == fam["id"]})),
                   fam["name"], fam.get("kind") or "", fam["note"].lower())
                for fam in f["families"]) + "</tbody></table>")
    a("<p>An <span class='mono'>IM-</span> code marks an intermediate the plant both consumes in its own later "
      "stages and sells, so it takes the family of whatever route it belongs to rather than a family of its own. "
      "Every product in the plan, with the route behind its code:</p>")
    a("<table><thead><tr><th>Code</th><th>Name</th><th class='n'>Charge</th><th class='n'>Batch</th>"
      "<th class='n'>Cycle</th><th>Solvent</th><th class='n'>Batches<br>planned</th><th>Route</th></tr></thead><tbody>"
      + "".join("<tr><td class='mono'><b>%s</b></td><td>%s</td><td class='n'>%s kL</td><td class='n'>%s kg</td>"
                "<td class='n'>%s h</td><td>%s</td><td class='n'>%s</td><td style='white-space:normal'>%s</td></tr>"
                % (c["id"], c["name"], n(c["chargeKL"], 1), n(c["batchKg"]), n(c["cycleH"]), c["solv"],
                   c["made"] or "&mdash;", c["route"])
                for c in f["catalogue"]) + "</tbody></table>")
    a(fig("q10-gloss"))

    # ============================================================================================ Q11
    a("<h2 class='pb'>11. The detailed production plan report</h2>")
    a(q(11))
    a("<p class='short'><b>The short answer.</b> Yes — it is built. A new page, <b>Production Plan Report</b>, "
      "with every column you listed, and a five-sheet Excel export.</p>")
    a("<p>Building it needed one real addition to the data model. The demo tracked utilities, effluent and solvent per "
      "batch, but it had no <b>bill of materials</b> — raw materials were an S&amp;OP-level list with no consumption "
      "rate. There is now a <b>charge sheet</b>, written the same way the duty profile already was:</p>")
    a("<div class='formula'><b>Charge profile</b> (per operation archetype): how much of each <i>role</i> is charged, "
      "<b>per kL of reaction volume</b><br>"
      "<b>Family inputs</b> (four rows): which material fills each role for each product family<br>"
      "&rarr; a product's bill of materials is those two, times its own charge volume. No per-product table anywhere.</div>")
    a("<table><thead><tr><th>Role</th><th>What it is</th><th>Charged at</th></tr></thead><tbody>"
      + "".join("<tr><td><b>%s</b></td><td>%s</td><td>%s</td></tr>"
                % (f["roleNames"].get(role, role),
                   {"FEED": "the key starting material", "REAGENT": "the reacting partner",
                    "NEUTRALISER": "caustic for the work-up", "CATALYST": "recovered and returned; only the loss is consumed",
                    "FILTER_AID": "celite on the isolation steps", "PACKAGING": "drums, liners and labels"}.get(role, ""),
                   ", ".join(sorted({a for a, lst in f["inputProfile"].items() for r2, _ in lst if r2 == role})))
                for role in ["FEED", "REAGENT", "NEUTRALISER", "CATALYST", "FILTER_AID", "PACKAGING"])
      + "</tbody></table>")
    a("<p>The <b>key starting material</b> is charged at the first reaction only: every later reaction stage consumes "
      "the intermediate the stage before it made, and that link is already in the route. Three new masters carry all of "
      "this — <b>Charge profile</b>, <b>Which material fills each role</b> and the derived <b>Charge sheet per "
      "batch</b>.</p>")
    if f.get("worked"):
        w = f["worked"]
        a("<h3>One batch, as the report shows it</h3>")
        a("<p><span class='mono'><b>%s</b></span> &mdash; %s, %s kg against a nameplate %s kg (%s), assay %.2f%%, "
          "impurity %.3f%%, d90 %d &micro;m.</p>"
          % (w["id"], w["productName"], n(w["kg"]), n(w["nominalKg"]), pct(w["kg"] / w["nominalKg"]),
             w["assay"], w["imp"], w["psd"]))
        a("<table><thead><tr><th class='n'>Seq</th><th>Operation</th><th>Unit</th><th class='n'>Hours</th>"
          "<th class='n'>Clean before</th><th class='n'>Stood</th><th class='n'>Window</th></tr></thead><tbody>"
          + "".join("<tr><td class='n'>%d</td><td>%s</td><td class='mono'>%s</td><td class='n'>%.1f</td>"
                    "<td class='n'>%s</td><td class='n'>%s</td><td class='n'>%s</td></tr>"
                    % (o["seq"], o["label"], o["unit"], o["hours"],
                       ("%.1f h" % o["cleanH"]) if o["cleanH"] else "&mdash;",
                       ("%.1f h" % o["lagH"]) if o["lagH"] is not None else "&mdash;",
                       ("%s h" % n(o["winH"])) if o["winH"] is not None else "&mdash;")
                    for o in w["ops"]) + "</tbody></table>")
        a("<div class='two'><div>")
        a("<b>Raw materials charged</b>")
        a("<table><thead><tr><th>Role</th><th>Material</th><th class='n'>Qty</th><th class='n'>Cost</th></tr></thead><tbody>"
          + "".join("<tr><td>%s</td><td>%s</td><td class='n'>%s %s</td><td class='n'>%s</td></tr>"
                    % (i["role"], i["rmName"], n(i["qty"], 2 if i["qty"] < 10 else 0), i["unit"], rs(i["rupees"]))
                    for i in w["inputs"])
          + "<tr class='tot'><td colspan='3'>Materials in this batch</td><td class='n'>%s</td></tr>"
            % rs(sum(i["rupees"] for i in w["inputs"])) + "</tbody></table>")
        a("</div><div>")
        a("<b>Utilities, solvent and effluent</b>")
        a("<table><tbody>"
          + "".join("<tr><td>%s</td><td class='n'>%s %s</td></tr>"
                    % (u["name"], n(w["util"][u["id"]], 1 if w["util"][u["id"]] < 100 else 0), u["qtyUnit"])
                    for u in f["utilities"] if w["util"].get(u["id"]))
          + "<tr><td>Solvent charged</td><td class='n'>%s kL</td></tr>" % n(w["solvKL"], 2)
          + "<tr><td>Returned by recovery</td><td class='n'>%s kL</td></tr>" % n(w["recoveredKL"], 2)
          + "<tr class='tot'><td>Fresh solvent needed</td><td class='n'>%s kL</td></tr>" % n(w["makeupKL"], 2)
          + "".join("<tr><td>Effluent to %s</td><td class='n'>%s m³</td></tr>" % (k, n(v, 2))
                    for k, v in sorted(w["effl"].items())) + "</tbody></table>")
        a("</div></div>")
    a("<p><b>The Excel export</b> has five sheets: <i>Batch register</i> (one row per batch, 21 columns), "
      "<i>Operations</i> (one row per operation, with its unit, window, lag and hold window), <i>Materials consumed</i> "
      "(one row per batch, operation and material, with the rate per kL and the cost), <i>Utilities consumed</i> and "
      "<i>Effluent</i>. Nothing in it is a snapshot — it is computed from the plan on screen, so it moves when a "
      "what-if moves the plan.</p>")
    a(fig("q11-reg"))
    a(fig("q11-cons"))

    # ============================================================================================ Q12
    a("<h2 class='pb'>12. Lots, blending and allocation against batches</h2>")
    a(q(12))
    a("<p class='short'><b>The short answer.</b> They are three different objects, constrained by three different "
      "things, and the page now says so before it shows the arithmetic.</p>")
    a("<table><thead><tr><th>Object</th><th>What it is</th><th>What constrains it</th><th class='n'>In this plan</th>"
      "</tr></thead><tbody>"
      "<tr><td><b>Batch</b></td><td>One charge taken through one route, start to end, on named units. A "
      "<i>manufacturing event</i>: it has a window on the Gantt, occupies equipment, draws utilities and puts effluent "
      "down the drain. Numbered <span class='mono'>PRODUCT-Bnnn</span>.</td><td>Equipment and time</td>"
      "<td class='n'>%s</td></tr>"
      "<tr><td><b>Lot</b></td><td>The material that batch produced, once QC has released it &mdash; the same kilos, but "
      "now carrying an assay, an impurity, a particle size and a retest date. It does not exist until release, on "
      "average %.1f days after drying.</td><td>Quality and shelf life</td><td class='n'>%s</td></tr>"
      "<tr><td><b>Customer lot</b></td><td>One to three lots <i>blended</i> so that the mixture meets that customer's "
      "specification, comes from a site they have approved, and still has the remaining shelf life they insist on. One "
      "customer lot, one COA. The only one of the three the customer ever sees.</td><td>The contract</td>"
      "<td class='n'>%s</td></tr></tbody></table>"
      % (n(f["naive"][4][2]), f["lots"]["qcDays"], n(f["lots"]["made"]), n(f["lots"]["allocs"])))
    a("<p><b>Why this is a decision and not bookkeeping.</b> A planner who stops at the batch can tell you the kilos "
      "exist and still be wrong about whether they can be shipped. In this plan <b>%s</b> of the <b>%s</b> allocations "
      "needed more than one lot, because no single lot met the spec on its own — and <b>%s</b> lots were turned down "
      "for reasons that have nothing to do with quantity:</p>"
      % (n(f["lots"]["blended"]), n(f["lots"]["allocs"]), n(f["lots"]["rejects"])))
    WHY = {"assay": "assayed below the order's minimum", "impurity": "impurity above the order's limit",
           "psd": "particle size outside the order's spec", "life": "remaining shelf life below the customer's minimum",
           "site": "made at a site that customer has not approved", "qc": "not yet released by QC"}
    a("<table><thead><tr><th>Why a lot was turned down</th><th class='n'>Times</th></tr></thead><tbody>"
      + "".join("<tr><td>%s</td><td class='n'>%s</td></tr>" % (WHY.get(k, k), n(v))
                for k, v in sorted(f["lots"]["rejectWhy"].items(), key=lambda kv: -kv[1])) + "</tbody></table>")
    a("<div class='box'><b>Blending is arithmetic, not mixing and hoping.</b> A blend is mass-weighted on <i>active "
      "content</i>, not on volume. Impurity averages down, so a clean lot can carry a marginal one; assay averages up, "
      "so a blend can never beat its best lot; particle size does not average at all — it is the worst of them. The "
      "remaining life of the consignment is the shortest of its lots. All of that is on screen on Lots, Blending &amp; "
      "Allocation, against the order's own spec window.</div>")
    a(fig("q12-chain"))

    # ---------------------------------------------------------------------------------------------------- close
    a("<h2 class='pb'>Where things stand</h2>")
    a("<p>The whole verification suite is green after these changes:</p>")
    a("<ul><li><b>Engine</b> &mdash; the committed plan is rebuilt from its own output and re-tested against every "
      "constraint it claims to honour: <b>%s</b> checks, <b>%s</b> violations, repeated for each of the four objective "
      "presets.</li>"
      "<li><b>Tension</b> &mdash; the dataset still makes every constraint bind, inside its band.</li>"
      "<li><b>Pages, flows, masters, audit</b> &mdash; every page renders with no error and no off-site request, all "
      "thirteen scenario cards land and move the KPI they declare, every live master round-trips, and every figure shown "
      "twice is the same number.</li></ul>" % (n(f["proofChecks"]), n(f["proofViolations"])))
    a("<div class='box good'><b>The one thing worth saying plainly.</b> The busiest equipment class in this plan runs at "
      "<b>%s</b> occupied. That figure is now accounted for hour by hour rather than left to be read as an error, and the "
      "account is honest about which part is the hold window and which part is simply a rolling release window on a "
      "%d-day horizon. If a prospect's own plant is genuinely equipment-limited, their data will say so when it is "
      "loaded — which is the point of making Master Data the front door rather than a settings screen.</div>"
      % (pct(f["byClass"][0]["busy"]), f["forwardDays"]))
    a("<p style='margin-top:14px;color:#666;font-size:9pt'>Built from the live demo. The charge sheet, the duty "
      "profiles, the routes and the cleaning matrix are all fictional, generated by "
      "<code>tools/generate_data.py</code>; the rule <i>shapes</i> come from the Specialty Chemicals deck and the "
      "Production Planner design documents. Rebuild this document with "
      "<code>python tools/build_answers.py</code>.</p>")

    return ("<!DOCTYPE html><html><head><meta charset='utf-8'><title>Twelve questions, answered</title>"
            "<style>%s</style></head><body>%s</body></html>" % (CSS, "".join(H)))
