"""Every GENERATED parameter of the Bluemingo specialty-chemicals demo lives here, in one place, so each value is visible
and easy to change — and so the Master Data page can mark every one of them "generated".

NOTHING here is a real plant. The site, the products, the customers, the people and the volumes are fictional. The only
things taken from outside are the *rule shapes* argued in the Bluemingo Specialty Chemicals deck (cleaning matrix, yield and
assay, hold-time windows, utility concurrency, effluent and recycle, hazard ceilings, spec-driven blending) and the
vocabulary of the Bluemingo Production Planner design (changeover matrix by attribute, links with a minimum and a maximum
lag, campaign rules, secondary resources, block times).

Units, once, everywhere:
  mass kg · volume kL · time minutes in the engine, hours in this file · steam t/h · refrigeration TR · vacuum m3/h
  effluent m3 · money INR
"""

SEED = 2210

PLANT = dict(company="Bluemingo", site="API Site · Unit 2", title="PP — Production Planning for Specialty Chemicals & APIs",
             product="Bluemingo PP", subtitle="Specialty Chemicals & APIs")

HISTORY_DAYS = 30        # frozen history, planned the generic way, with its consequences recorded
FORWARD_DAYS = 60        # the detailed plan horizon from the as-of moment
SOP_MONTHS = 12          # monthly buckets; months 1-3 are derived from the detailed plan
ASOF_HOUR, ASOF_MIN = 9, 30

# =====================================================================================================================
# EQUIPMENT — primary resources. Block A is the general plant; Block B is segregated for high-potency work.
# "vol" is the working volume. A batch is eligible on a unit when its charge fits AND the unit is not grossly oversized
# (a 0.6 kL charge in a 10 kL reactor does not mix) — a real constraint, derived from attributes, never a lookup table.
# =====================================================================================================================
UNITS = [
    dict(id="R-101", name="Reactor 101", cls="REACTOR", block="A", vol=6.0, mat="GL", cryo=False, note="Glass-lined, jacketed"),
    dict(id="R-102", name="Reactor 102", cls="REACTOR", block="A", vol=6.0, mat="GL", cryo=False, note="Glass-lined, jacketed"),
    dict(id="R-103", name="Reactor 103", cls="REACTOR", block="A", vol=4.0, mat="SS", cryo=True, note="Stainless on brine, no halogenated service"),
    dict(id="R-104", name="Reactor 104", cls="REACTOR", block="A", vol=10.0, mat="GL", cryo=False, note="Glass-lined, large charge"),
    dict(id="R-105", name="Reactor 105", cls="REACTOR", block="A", vol=4.0, mat="GL", cryo=True, note="Brine / cryo service to -15 C"),
    dict(id="R-201", name="Reactor 201", cls="REACTOR", block="B", vol=4.0, mat="GL", cryo=True, note="Segregated high-potency suite, brine service"),
    dict(id="CF-01", name="Centrifuge 01", cls="ISOLATION", block="A", vol=4.0, mat="SS", cryo=False, note="Peeler centrifuge"),
    dict(id="ANFD-01", name="ANFD 01", cls="ISOLATION", block="A", vol=4.0, mat="SS", cryo=False, note="Agitated Nutsche filter-dryer"),
    dict(id="ANFD-02", name="ANFD 02", cls="ISOLATION", block="B", vol=2.5, mat="SS", cryo=False, note="ANFD, high-potency suite"),
    dict(id="ANFD-03", name="ANFD 03", cls="ISOLATION", block="A", vol=6.0, mat="SS", cryo=False, note="ANFD, large cake"),
    dict(id="VTD-01", name="Vacuum tray dryer 01", cls="DRYER", block="A", vol=6.0, mat="SS", cryo=False, note="Vacuum tray dryer"),
    dict(id="SFD-01", name="Spin-flash dryer 01", cls="DRYER", block="A", vol=8.0, mat="SS", cryo=False, note="Continuous spin-flash"),
    dict(id="VTD-02", name="Vacuum tray dryer 02", cls="DRYER", block="B", vol=3.0, mat="SS", cryo=False, note="Vacuum tray dryer, high-potency suite"),
    dict(id="VTD-03", name="Vacuum tray dryer 03", cls="DRYER", block="A", vol=6.0, mat="SS", cryo=False, note="Vacuum tray dryer"),
    dict(id="MC-01", name="Micronizer 01", cls="MILL", block="A", vol=9.0, mat="SS", cryo=False, note="Jet mill, PSD control"),
    dict(id="PK-01", name="Pack line 01", cls="PACK", block="A", vol=9.0, mat="SS", cryo=False, note="Drum / bag pack"),
    dict(id="PK-02", name="Pack line 02", cls="PACK", block="B", vol=9.0, mat="SS", cryo=False, note="Contained pack, high potency"),
]
OVERSIZE_FACTOR = 2.6     # a reactor charge may not be smaller than its volume / this (agitation limit)
OVERSIZE_CLASSES = ["REACTOR"]   # the agitation limit applies to reactors only: a filter or dryer runs a part load
# vessel volume an operation needs, as a share of the reaction charge: a filter holds the slurry, a dryer
# only the wet cake, a mill and a pack line only the dry solid. Derived once here, never per product.
OP_VOL_SHARE = {"REACTOR": 1.00, "ISOLATION": 0.62, "DRYER": 0.34, "MILL": 0.20, "PACK": 0.20}
UNIT_UPTIME = 0.92        # block time (maintenance, utility shutdown, shift gap) takes the rest

# planned block times per unit: weekday 0=Mon, start hour, hours. Maintenance windows are staggered.
BLOCK_TIMES = [
    dict(unit="R-101", every=7, dow=6, start=6, hours=8, reason="Planned maintenance"),
    dict(unit="R-102", every=7, dow=6, start=14, hours=8, reason="Planned maintenance"),
    dict(unit="R-103", every=7, dow=0, start=6, hours=6, reason="Planned maintenance"),
    dict(unit="R-104", every=7, dow=2, start=6, hours=8, reason="Planned maintenance"),
    dict(unit="R-105", every=7, dow=3, start=6, hours=6, reason="Brine circuit service"),
    dict(unit="R-201", every=7, dow=4, start=6, hours=10, reason="Containment verification"),
    dict(unit="CF-01", every=7, dow=1, start=6, hours=5, reason="Planned maintenance"),
    dict(unit="ANFD-01", every=7, dow=5, start=6, hours=6, reason="Planned maintenance"),
    dict(unit="ANFD-02", every=14, dow=5, start=14, hours=6, reason="Planned maintenance"),
    dict(unit="ANFD-03", every=7, dow=4, start=14, hours=6, reason="Planned maintenance"),
    dict(unit="VTD-01", every=7, dow=0, start=14, hours=5, reason="Planned maintenance"),
    dict(unit="SFD-01", every=7, dow=3, start=14, hours=5, reason="Planned maintenance"),
    dict(unit="VTD-02", every=14, dow=3, start=6, hours=5, reason="Planned maintenance"),
    dict(unit="VTD-03", every=7, dow=5, start=14, hours=5, reason="Planned maintenance"),
    dict(unit="MC-01", every=7, dow=2, start=14, hours=4, reason="Screen change"),
    dict(unit="PK-01", every=7, dow=1, start=14, hours=4, reason="Line clean"),
    dict(unit="PK-02", every=14, dow=1, start=6, hours=4, reason="Line clean"),
]

# =====================================================================================================================
# SECONDARY RESOURCES — utilities. The cap is per hour, and what a batch draws is a three-segment duty profile, so the
# PEAK of concurrent batches binds, not a flattened average. The brine plant is derated in the hot months.
# =====================================================================================================================
UTILITIES = [
    dict(id="STEAM", name="Steam (8 bar)", unit="t/h", cap=4.2, kind="heat"),
    dict(id="BRINE", name="Brine (-15 C)", unit="TR", cap=132.0, kind="cool", derate=dict(months=[4, 5, 6], cap=110.0, why="Ambient derating of the brine chillers, April to June")),
    dict(id="CHW", name="Chilled water (7 C)", unit="TR", cap=130.0, kind="cool"),
    dict(id="VAC", name="Vacuum", unit="m3/h", cap=1150.0, kind="vacuum"),
    dict(id="N2", name="Nitrogen", unit="Nm3/h", cap=100.0, kind="inert"),
]

# Operation archetypes. Duty is per kL of charge per hour, so a bigger batch draws more — the profile scales with the
# charge instead of being retyped per product. segs = (share of the operation's duration, draw per kL).
OP_ARCHETYPES = {
    "RXN_EXO":  dict(label="Exothermic reaction", cls="REACTOR", clean=True,
                     segs=[(0.15, dict(N2=8.0)), (0.55, dict(BRINE=11.0, N2=4.0)), (0.30, dict(STEAM=0.22, VAC=70.0))]),
    "RXN_HOT":  dict(label="Reflux reaction", cls="REACTOR", clean=True,
                     segs=[(0.15, dict(STEAM=0.18, N2=6.0)), (0.60, dict(STEAM=0.30, CHW=9.0)), (0.25, dict(CHW=14.0, VAC=55.0))]),
    "RXN_CRYO": dict(label="Cryogenic reaction", cls="REACTOR", clean=True,
                     segs=[(0.20, dict(BRINE=9.0, N2=10.0)), (0.60, dict(BRINE=26.0, N2=6.0)), (0.20, dict(CHW=10.0))]),
    "RXN_HYD":  dict(label="Hydrogenation", cls="REACTOR", clean=True,
                     segs=[(0.20, dict(N2=14.0, STEAM=0.10)), (0.55, dict(CHW=12.0, N2=6.0)), (0.25, dict(STEAM=0.26, VAC=60.0))]),
    "ISO_CFG":  dict(label="Centrifugation and wash", cls="ISOLATION", clean=True,
                     segs=[(0.30, dict(CHW=5.0, N2=3.0)), (0.45, dict(CHW=7.0)), (0.25, dict(VAC=40.0))]),
    "ISO_ANFD": dict(label="Filtration and wash", cls="ISOLATION", clean=True,
                     segs=[(0.25, dict(N2=5.0)), (0.45, dict(VAC=55.0, N2=3.0)), (0.30, dict(STEAM=0.14, VAC=75.0))]),
    "DRY_VTD":  dict(label="Vacuum tray drying", cls="DRYER", clean=True,
                     segs=[(0.20, dict(STEAM=0.12, VAC=60.0)), (0.60, dict(STEAM=0.20, VAC=85.0)), (0.20, dict(CHW=5.0, VAC=40.0))]),
    "DRY_SFD":  dict(label="Spin-flash drying", cls="DRYER", clean=True,
                     segs=[(0.20, dict(STEAM=0.24)), (0.60, dict(STEAM=0.34, N2=5.0)), (0.20, dict(CHW=4.0))]),
    "MILL":     dict(label="Micronizing to PSD", cls="MILL", clean=True,
                     segs=[(0.20, dict(N2=16.0)), (0.60, dict(N2=22.0)), (0.20, dict(N2=10.0))]),
    "PACK":     dict(label="Pack and label", cls="PACK", clean=False,
                     segs=[(0.25, dict()), (0.50, dict(N2=4.0)), (0.25, dict())]),
}

# =====================================================================================================================
# THE CHARGE SHEET — what one batch CONSUMES in materials, written the same way the duty profile is written: per kL of
# charge, against the OPERATION ARCHETYPE. So a 6 kL batch consumes proportionally more than a 2 kL one without a second
# table, and a product added from Excel inherits its whole bill of materials from its family and its route.
#
# Roles, not material ids, hang off the archetype. FAMILY_INPUTS says which material fills each role for each family —
# four rows, and the only place a product id comes anywhere near a material id.
#   FEED          the key starting material. Charged at the FIRST reaction only: every later reaction stage consumes the
#                 intermediate the stage before it made, which the route already tracks.
#   REAGENT       the reacting partner, every reaction
#   NEUTRALISER   caustic for the work-up, on the reactions that need one
#   CATALYST      hydrogenations only, and recovered rather than consumed
#   FILTER_AID    the isolation steps
#   PACKAGING     drums and liners, on the pack line
# Rates are kg per kL of charge, except PACKAGING, which is drums per kL.
# =====================================================================================================================
INPUT_PROFILE = {
    "RXN_EXO":  [("FEED", 185.0), ("REAGENT", 96.0), ("NEUTRALISER", 34.0)],
    "RXN_HOT":  [("FEED", 172.0), ("REAGENT", 78.0), ("NEUTRALISER", 28.0)],
    "RXN_CRYO": [("FEED", 164.0), ("REAGENT", 112.0)],
    "RXN_HYD":  [("FEED", 178.0), ("REAGENT", 44.0), ("CATALYST", 1.6)],
    "ISO_CFG":  [("FILTER_AID", 7.0)],
    "ISO_ANFD": [("FILTER_AID", 9.0)],
    "DRY_VTD":  [],
    "DRY_SFD":  [],
    "MILL":     [],
    "PACK":     [("PACKAGING", 1.8)],
}
FAMILY_INPUTS = {
    "F1": dict(FEED="RM-01", REAGENT="RM-03", NEUTRALISER="RM-07", CATALYST="RM-04", FILTER_AID="RM-09", PACKAGING="RM-10"),
    "F2": dict(FEED="RM-02", REAGENT="RM-03", NEUTRALISER="RM-07", CATALYST="RM-04", FILTER_AID="RM-09", PACKAGING="RM-10"),
    "F3": dict(FEED="RM-05", REAGENT="RM-08", NEUTRALISER="RM-07", CATALYST="RM-04", FILTER_AID="RM-09", PACKAGING="RM-10"),
    "F4": dict(FEED="RM-05", REAGENT="RM-06", NEUTRALISER="RM-07", CATALYST="RM-04", FILTER_AID="RM-09", PACKAGING="RM-10"),
}
# The catalogue. Prices and lead times are fixed, not drawn, so a batch's material cost is the same number every run.
RAW_MATERIALS = [
    dict(id="RM-01", name="Aniline", unit="kg", minBlock=24000, priceUnit=138, leadDays=28, onHand=41000),
    dict(id="RM-02", name="Toluene feedstock", unit="kg", minBlock=25000, priceUnit=96, leadDays=24, onHand=37500),
    dict(id="RM-03", name="Sodium nitrite", unit="kg", minBlock=10000, priceUnit=84, leadDays=21, onHand=16200),
    dict(id="RM-04", name="Catalyst (Pd/C 5%)", unit="kg", minBlock=25, priceUnit=286000, leadDays=52, onHand=46.0),
    dict(id="RM-05", name="Protected amine", unit="kg", minBlock=2000, priceUnit=780, leadDays=45, onHand=3400),
    dict(id="RM-06", name="Chiral auxiliary", unit="kg", minBlock=150, priceUnit=18600, leadDays=48, onHand=265),
    dict(id="RM-07", name="Caustic lye 48%", unit="kg", minBlock=20000, priceUnit=31, leadDays=18, onHand=34000),
    dict(id="RM-08", name="Acetic anhydride", unit="kg", minBlock=20000, priceUnit=118, leadDays=26, onHand=28500),
    dict(id="RM-09", name="Filter aid (celite)", unit="kg", minBlock=2000, priceUnit=210, leadDays=20, onHand=3900),
    dict(id="RM-10", name="Drums, liners and labels", unit="drum", minBlock=500, priceUnit=1450, leadDays=14, onHand=820),
]
ROLE_NAMES = dict(FEED="Key starting material", REAGENT="Reagent", NEUTRALISER="Neutraliser",
                  CATALYST="Catalyst", FILTER_AID="Filter aid", PACKAGING="Packaging")
CATALYST_RECOVERY = 0.94        # catalyst is filtered off and returned; only the loss is a real consumption

# =====================================================================================================================
# WASTE AND RECOVERY — daily limits per category, with carry-over. Recovered solvent is credited to a later batch.
# =====================================================================================================================
WASTE = [
    dict(id="ETP", name="Effluent treatment plant", unit="m3/day", cap=30.0, note="Aqueous effluent, consented load"),
    dict(id="MEE", name="Multiple-effect evaporator", unit="m3/day", cap=38.0, note="High-TDS stream to the MEE"),
    dict(id="INC", name="Incinerable residue", unit="t/day", cap=5.4, note="Off-site incineration, drummed"),
]
SOLVENT_RECOVERY = dict(cap=13.0, unit="kL/day", recoveryMin=0.70, recoveryMax=0.92, turnaroundHours=36,
                        note="Distillation train; recovered solvent returns to the tank farm after QC")

# =====================================================================================================================
# TANK FARM AND HAZARD LICENCE — the ceiling is the LICENCE per hazard class, not the steel.
# =====================================================================================================================
HAZARD_CLASSES = [
    dict(id="FLAM", name="Flammable (Class A/B)", licensedKL=205.0, note="Petroleum class A and B, licensed quantity"),
    dict(id="TOX", name="Toxic", licensedKL=18.0, note="Toxic chemicals rules, licensed quantity"),
    dict(id="OXID", name="Oxidiser", licensedKL=11.0, note="Segregated storage, licensed quantity"),
    dict(id="CORR", name="Corrosive", licensedKL=72.0, note="Acid / alkali day tanks"),
]
BUNDS = [dict(id="B-1", name="Bund 1 — solvent farm", classes=["FLAM"]),
         dict(id="B-2", name="Bund 2 — solvent farm", classes=["FLAM"]),
         dict(id="B-3", name="Bund 3 — toxic and oxidiser", classes=["TOX", "OXID"]),
         dict(id="B-4", name="Bund 4 — acids and alkali", classes=["CORR"])]
SEGREGATION = [("OXID", "FLAM"), ("TOX", "FLAM")]     # these hazard classes may not share a bund

TANKER_COVER = 1.15            # deliveries bring this multiple of a tank's net draw: a little more than it loses
LICENCE_SQUEEZE_DAY = 11       # days after the as-of: four flammable tankers land together ahead of a campaign build-up
TANK_OPENING_SHARE = 0.42       # opening level as a share of tank capacity: real headroom under the licence
TANKER_MAX_SHARE = 0.45         # a tanker load may be at most this share of the tank it fills

SOLVENTS = [
    dict(id="TOL", name="Toluene", cls="HYD", haz="FLAM", tank="T-01", bund="B-1", capKL=60.0, openKL=41.0, priceKL=98000, tanker=25.0),
    dict(id="MDC", name="Dichloromethane", cls="HAL", haz="FLAM", tank="T-02", bund="B-1", capKL=40.0, openKL=24.5, priceKL=142000, tanker=22.0),
    dict(id="IPA", name="Isopropyl alcohol", cls="ALC", haz="FLAM", tank="T-03", bund="B-2", capKL=50.0, openKL=33.0, priceKL=118000, tanker=25.0),
    dict(id="MEOH", name="Methanol", cls="ALC", haz="FLAM", tank="T-04", bund="B-2", capKL=45.0, openKL=27.0, priceKL=72000, tanker=25.0),
    dict(id="ACN", name="Acetonitrile", cls="POL", haz="FLAM", tank="T-05", bund="B-2", capKL=30.0, openKL=18.0, priceKL=265000, tanker=20.0),
    dict(id="DMF", name="Dimethylformamide", cls="POL", haz="TOX", tank="T-06", bund="B-3", capKL=25.0, openKL=14.0, priceKL=168000, tanker=20.0),
    dict(id="THF", name="Tetrahydrofuran", cls="POL", haz="FLAM", tank="T-07", bund="B-1", capKL=20.0, openKL=11.0, priceKL=236000, tanker=20.0),
    dict(id="EA", name="Ethyl acetate", cls="EST", haz="FLAM", tank="T-08", bund="B-2", capKL=35.0, openKL=22.0, priceKL=104000, tanker=25.0),
    dict(id="HNO3", name="Nitric acid 68%", cls="AQ", haz="OXID", tank="T-09", bund="B-3", capKL=12.0, openKL=7.4, priceKL=46000, tanker=12.0),
    dict(id="H2SO4", name="Sulphuric acid 98%", cls="AQ", haz="CORR", tank="T-10", bund="B-4", capKL=40.0, openKL=26.0, priceKL=22000, tanker=20.0),
    dict(id="NAOH", name="Caustic lye 48%", cls="AQ", haz="CORR", tank="T-11", bund="B-4", capKL=35.0, openKL=24.0, priceKL=31000, tanker=20.0),
]

# =====================================================================================================================
# PRODUCTS — four families. Every rule the scheduler applies is read off these ATTRIBUTES: nothing maps a product id to a
# unit, a clean grade or a duty. A product added from Excel inherits all of it.
#   family      F1 aryl amines (pale, light effluent) · F2 nitro / azo (deep colour, heavy effluent)
#               F3 regulated APIs (three stages, export, DMF-filed) · F4 high-potency (Block B only)
#   solv        the dominant solvent — drives the cleaning matrix and the tank farm
#   colour      1 pale .. 5 deep: a deep product before a pale one forces a boil-out
#   potency     1 normal · 2 potent · 3 high-potency (segregated)
#   genotox     a genotoxic residue may never precede a regulated API on the same unit
#   route       the operations, in order: (archetype, hours, minLagH, maxLagH, effluent m3/batch, waste category, solvent kL/batch)
#               minLagH / maxLagH are the lag allowed BEFORE this operation, measured from the end of the one before
#               it — the planner's minimum and maximum lag on that link. maxLagH is the HOLD WINDOW of the deck's
#               nuance 3: how long that intermediate may wait. The first operation's pair is unused.
# =====================================================================================================================
FAMILIES = [
    dict(id="F1", name="Aryl amines", kind="aryl amine", note="Pale intermediates, light effluent load"),
    dict(id="F2", name="Nitro and azo", kind="nitro or azo intermediate", note="Deep colour load, heavy effluent"),
    dict(id="F3", name="Regulated APIs", kind="regulated active", note="Three stages, filed route, export"),
    dict(id="F4", name="High-potency APIs", kind="high-potency active", note="Segregated suite, contained pack"),
]

# route rows: (archetype, hours, minLagH, maxLagH, effl_m3, waste_cat, solvent_kL)
PRODUCTS = [
    # ---- F1 aryl amines ------------------------------------------------------------------------------------------
    dict(id="AM-110", name="4-Amino-anisole", family="F1", solv="TOL", colour=2, potency=1, genotox=False, chargeKL=4.0, batchKg=620,
         assay=(98.2, 0.45), impMax=0.35, psd=(140, 40), retestM=36, priceKg=1180, costKg=720, sell=True,
         route=[("RXN_HYD", 16, 2, 24, 7.5, "ETP", 2.6), ("ISO_CFG", 7, 1, 10, 4.0, "ETP", 0.8), ("DRY_VTD", 13, 2, 72, 0.6, "ETP", 0.0)]),
    dict(id="AM-120", name="2-Chloro-aniline", family="F1", solv="MDC", colour=2, potency=1, genotox=False, chargeKL=3.2, batchKg=480,
         assay=(98.6, 0.40), impMax=0.30, psd=(120, 35), retestM=30, priceKg=1420, costKg=880, sell=True,
         route=[("RXN_EXO", 14, 2, 18, 6.0, "ETP", 2.1), ("ISO_ANFD", 8, 1, 12, 3.2, "MEE", 0.7), ("DRY_VTD", 12, 2, 72, 0.5, "ETP", 0.0)]),
    dict(id="AM-130", name="3-Amino-benzotrifluoride", family="F1", solv="IPA", colour=1, potency=1, genotox=False, chargeKL=5.0, batchKg=760,
         assay=(99.0, 0.35), impMax=0.25, psd=(160, 45), retestM=36, priceKg=2240, costKg=1460, sell=True,
         route=[("RXN_HYD", 18, 2, 24, 8.0, "ETP", 3.0), ("ISO_CFG", 8, 1, 12, 4.5, "ETP", 1.0), ("DRY_SFD", 9, 2, 96, 0.4, "ETP", 0.0)]),
    # ---- F2 nitro and azo (deep colour, heavy effluent, co-product) -----------------------------------------------
    dict(id="NT-210", name="2,4-Dinitro-toluene sulphonate", family="F2", solv="H2SO4", colour=5, potency=1, genotox=True, chargeKL=5.5, batchKg=840,
         assay=(97.4, 0.60), impMax=0.60, psd=(210, 60), retestM=24, priceKg=640, costKg=385, sell=True,
         coprod=dict(id="CP-241", ratio=1.85, haz="CORR", disposalKg=14, name="Spent nitration acid"),
         route=[("RXN_EXO", 20, 3, 14, 18.0, "MEE", 3.4), ("ISO_CFG", 9, 1, 12, 9.0, "ETP", 1.2), ("DRY_VTD", 14, 2, 48, 0.8, "ETP", 0.0)]),
    dict(id="NT-220", name="4-Nitro-phenol", family="F2", solv="HNO3", colour=4, potency=1, genotox=True, chargeKL=4.5, batchKg=700,
         assay=(97.8, 0.55), impMax=0.55, psd=(190, 55), retestM=24, priceKg=720, costKg=430, sell=True,
         coprod=dict(id="CP-241", ratio=1.40, haz="CORR", disposalKg=14, name="Spent nitration acid"),
         route=[("RXN_EXO", 18, 3, 12, 15.0, "MEE", 2.8), ("ISO_ANFD", 10, 1, 12, 7.5, "ETP", 1.0), ("DRY_VTD", 13, 2, 48, 0.7, "ETP", 0.0)]),
    dict(id="AZ-230", name="Azo coupling intermediate", family="F2", solv="DMF", colour=5, potency=1, genotox=False, chargeKL=6.0, batchKg=900,
         assay=(96.8, 0.70), impMax=0.80, psd=(240, 70), retestM=24, priceKg=560, costKg=330, sell=True,
         route=[("RXN_HOT", 13, 3, 10, 21.0, "MEE", 3.8), ("ISO_CFG", 10, 1, 6, 11.0, "ETP", 1.4), ("DRY_SFD", 10, 2, 48, 0.9, "ETP", 0.0)]),
    # ---- F3 regulated APIs: three stages, hold windows, export ----------------------------------------------------
    dict(id="RX-310", name="Rexatidine API", family="F3", solv="ACN", colour=2, potency=2, genotox=False, chargeKL=3.6, batchKg=410,
         assay=(99.3, 0.22), impMax=0.15, psd=(95, 22), retestM=36, priceKg=9800, costKg=5900, sell=True, regulated=True,
         route=[("RXN_CRYO", 14, 2, 10, 5.5, "ETP", 2.0), ("ISO_ANFD", 8, 1, 12, 3.0, "ETP", 0.9),
                ("RXN_HOT", 18, 3, 18, 6.5, "ETP", 2.2), ("ISO_CFG", 8, 1, 8, 3.4, "ETP", 0.8), ("DRY_VTD", 15, 2, 96, 0.5, "ETP", 0.0), ("PACK", 5, 1, 240, 0.1, "INC", 0.0)]),
    dict(id="RX-320", name="Vendrozide API", family="F3", solv="THF", colour=1, potency=2, genotox=False, chargeKL=3.0, batchKg=330,
         assay=(99.5, 0.18), impMax=0.10, psd=(80, 18), retestM=36, priceKg=14600, costKg=8800, sell=True, regulated=True,
         route=[("RXN_CRYO", 16, 2, 8, 5.0, "ETP", 1.8), ("ISO_ANFD", 8, 1, 12, 2.8, "ETP", 0.8),
                ("RXN_HOT", 17, 3, 16, 6.0, "ETP", 2.0), ("ISO_CFG", 7, 1, 8, 3.0, "ETP", 0.7), ("DRY_VTD", 16, 2, 96, 0.4, "ETP", 0.0), ("MILL", 6, 1, 120, 0.1, "INC", 0.0), ("PACK", 5, 1, 240, 0.1, "INC", 0.0)]),
    dict(id="RX-330", name="Lamoprazole intermediate", family="F3", solv="EA", colour=2, potency=1, genotox=False, chargeKL=4.4, batchKg=540,
         assay=(99.1, 0.25), impMax=0.20, psd=(110, 28), retestM=30, priceKg=6400, costKg=3900, sell=True, regulated=True,
         coprod=dict(id="CP-331", ratio=0.22, haz="FLAM", disposalKg=0, name="Recovered isomer", priceKg=1100),
         route=[("RXN_HOT", 19, 2, 12, 7.0, "ETP", 2.4), ("ISO_CFG", 9, 1, 12, 4.0, "ETP", 1.0),
                ("RXN_HOT", 15, 3, 24, 5.5, "ETP", 1.9), ("DRY_VTD", 14, 2, 96, 0.5, "ETP", 0.0), ("PACK", 5, 1, 240, 0.1, "INC", 0.0)]),
    # ---- F4 high potency: Block B only, contained pack ------------------------------------------------------------
    dict(id="HP-410", name="Oncology API (HP)", family="F4", solv="ACN", colour=1, potency=3, genotox=True, chargeKL=1.8, batchKg=140,
         assay=(99.6, 0.15), impMax=0.08, psd=(45, 10), retestM=24, priceKg=168000, costKg=96000, sell=True, regulated=True,
         route=[("RXN_CRYO", 18, 2, 8, 2.2, "INC", 1.1), ("ISO_ANFD", 10, 1, 10, 1.4, "INC", 0.6), ("DRY_VTD", 18, 2, 72, 0.3, "INC", 0.0), ("PACK", 6, 1, 240, 0.1, "INC", 0.0)]),
    dict(id="HP-420", name="Hormone API (HP)", family="F4", solv="MEOH", colour=1, potency=3, genotox=False, chargeKL=1.6, batchKg=120,
         assay=(99.4, 0.18), impMax=0.10, psd=(38, 9), retestM=24, priceKg=96000, costKg=56000, sell=True, regulated=True,
         route=[("RXN_HOT", 16, 2, 10, 1.8, "INC", 0.9), ("ISO_ANFD", 9, 1, 10, 1.1, "INC", 0.5), ("DRY_VTD", 16, 2, 72, 0.2, "INC", 0.0), ("PACK", 6, 1, 240, 0.1, "INC", 0.0)]),
    dict(id="HP-430", name="Cytotoxic intermediate (HP)", family="F4", solv="MDC", colour=2, potency=3, genotox=True, chargeKL=2.0, batchKg=165,
         assay=(98.9, 0.28), impMax=0.18, psd=(55, 14), retestM=24, priceKg=74000, costKg=44000, sell=True,
         route=[("RXN_EXO", 17, 2, 9, 2.6, "INC", 1.3), ("ISO_ANFD", 10, 1, 10, 1.6, "INC", 0.7), ("DRY_VTD", 17, 2, 72, 0.3, "INC", 0.0)]),
    # ---- intermediates that are ALSO sold (same equipment, same cleaning class as their family) -------------------
    dict(id="IM-205", name="Amino-sulphonate intermediate", family="F1", solv="TOL", colour=3, potency=1, genotox=False, chargeKL=4.8, batchKg=690,
         assay=(97.9, 0.50), impMax=0.45, psd=(185, 50), retestM=18, priceKg=780, costKg=470, sell=True, intermediate=True,
         route=[("RXN_HOT", 15, 2, 20, 9.0, "ETP", 2.8), ("ISO_CFG", 8, 1, 10, 5.0, "ETP", 1.1)]),
    dict(id="IM-315", name="Protected amine intermediate", family="F3", solv="EA", colour=1, potency=1, genotox=False, chargeKL=3.8, batchKg=470,
         assay=(98.8, 0.30), impMax=0.25, psd=(130, 32), retestM=18, priceKg=3100, costKg=1900, sell=True, intermediate=True, regulated=True,
         route=[("RXN_HOT", 17, 2, 14, 6.0, "ETP", 2.2), ("ISO_ANFD", 9, 1, 12, 3.6, "ETP", 0.9)]),
]

# =====================================================================================================================
# CLEANING MATRIX — THE RULE, derived from attributes, with an override table for the pairs the plant has validated
# differently. The grid on screen is a VIEW of this rule, so a new product gets a sane row and column for free.
# =====================================================================================================================
CLEAN_GRADES = [
    dict(id="NONE", name="No clean", hours=0.0, note="Same product, campaign continues"),
    dict(id="RINSE", name="Solvent rinse", hours=2.0, note="Same family and solvent, colour not falling"),
    dict(id="WASH", name="Solvent wash", hours=6.0, note="Family or solvent class changes"),
    dict(id="BOILOUT", name="Boil-out and swab", hours=16.0, note="Deep colour before pale, or potent before normal; swab test to a limit"),
    dict(id="DEDICATE", name="Validated clean-down", hours=24.0, note="Genotoxic residue before a filed API route: full clean-down, swab to the dedicated limit, QA release of the train"),
    dict(id="FORBIDDEN", name="Not permitted", hours=None, note="Cross-contamination risk the plant does not accept at any clean grade — segregated equipment, never a sequencing choice"),
]
CLEAN_OVERRIDES = [     # (from, to, grade, why) — what the plant's own validation data says, overriding the derived grade
    dict(frm="AZ-230", to="AM-130", grade="FORBIDDEN", why="Azo residue is not removable to the amine limit on this train"),
    dict(frm="NT-210", to="AM-110", grade="BOILOUT", why="Validated boil-out, two swabs"),
    dict(frm="IM-205", to="AM-110", grade="RINSE", why="Shared intermediate, same solvent, validated rinse"),
    dict(frm="RX-330", to="RX-310", grade="WASH", why="Both filed routes; wash validated between them"),
    dict(frm="NT-220", to="NT-210", grade="NONE", why="Campaign pair, no clean between them"),
]
# What the GENERIC rule set assumes instead. These are the deck's own words made numeric: one changeover time per product
# pair, and nameplate yield. The aware rule set reads the matrix and the yield distribution instead.
GENERIC = dict(flatChangeoverH=3.0, yieldAllowance=1.00,
               note="A generic planner books a flat changeover between any two products and plans batches at nameplate yield")
AWARE = dict(yieldAllowance=1.0, yieldConfidenceSd=1.0,
             note="The aware plan sizes a campaign one standard deviation below mean yield, then re-costs it as each batch assays")

CAMPAIGN = dict(minBatches=3, maxBatches=9, forcedBreakAfter=9, pullAheadDays=28, sortAttr="colour", sortDir="asc",
                note="Campaign rule: group a product, run pale to deep inside a family, force a break after nine batches")

# =====================================================================================================================
# DEMAND — fictional customers and orders. 'regulated' customers carry an approved-site + route matrix and a minimum
# remaining shelf life; those two gates are what make allocation more than quantity and date.
# =====================================================================================================================
# sites in the network. This demo plans UNIT-2 in detail; the others exist so sourcing and site approval are real choices.
SITES = [
    dict(id="UNIT-2", name="API Site · Unit 2", kind="own", planned=True, note="The plant this demo schedules"),
    dict(id="UNIT-7", name="Fine Chem Site · Unit 7", kind="own", planned=False, note="Second own site, S&OP level only"),
    dict(id="TOLL-A", name="Toll partner A", kind="toll", planned=False, note="Tolling partner for isolated stages"),
]

CUSTOMER_NAMES = [
    "Aurelia Pharma", "Northwind Lifesciences", "Kesterel Chemie", "Vantage Agro", "Sable & Roth",
    "Meridian Specialty", "Halcyon Pharma", "Torrid Dyes", "Bluecrest Nutra", "Calder Fine Chem",
    "Ostara Labs", "Pemberton Agro", "Veridian Pharma", "Quillon Chemicals", "Ridgeline Polymers",
    "Suvarna Organics", "Trellis Lifesciences", "Umber Pigments", "Vireo Crop Science", "Westmark Pharma",
    "Yarrow Specialty", "Zephyr Intermediates", "Arclight Chemie", "Brightmoor Pharma", "Coralline Labs",
    "Dunmore Agro", "Elmridge Organics", "Fairhaven Pharma", "Glenmere Dyes", "Harrowgate Chem",
    "Inverness Lifesci", "Jessamine Nutra", "Kinloch Pharma", "Larkspur Agro", "Marlowe Specialty",
    "Norwood Intermediates", "Oakmere Pharma", "Pinecrest Chemie", "Quarrystone Agro", "Ravensworth Labs",
]
CUST_REGIONS = ["EU", "US", "JP", "IN", "LATAM", "SEA"]
ORDER_CLASSES = [       # class drives priority, the delay penalty and the release window
    dict(id="EXPORT_REG", name="Regulated export", share=0.30, penaltyPerDay=22000, relWinDays=28, note="Late-delivery penalty is a contractual percentage of order value a day. Filed route, approved site, COA with every lot"),
    dict(id="EXPORT", name="Export", share=0.22, penaltyPerDay=14000, relWinDays=24, note="Contracted export, no site filing"),
    dict(id="DOM_COMMITTED", name="Committed domestic", share=0.30, penaltyPerDay=6000, relWinDays=18, note="Confirmed date"),
    dict(id="DOM_OPEN", name="Open domestic", share=0.18, penaltyPerDay=1200, relWinDays=14, note="Requested date, not committed"),
]
ORDERS_TARGET = 140          # orders in the book: a fine-chemicals book, and enough lines that the release window keeps the plant fed
LINES_PER_ORDER = (1, 2)
LINE_QTY_KG = (100, 6000)
# the smallest order line, as a share of one batch: a line consumes a whole batch however small it is
MIN_LINE_BATCHES = 0.75
DEMAND_LOAD = 0.82           # orders ask for this share of the capacity the plant can REALISE (tension gate 0.85-0.92)
# Nameplate unit-hours are not available hours. Once hold windows have to be honoured and eligibility is as narrow as
# chemistry makes it, a schedule realises only part of the nameplate: a reactor waits because the filter it feeds cannot
# take the slurry in time, and that wait is not recoverable. Measured from the aware plan with tools/calibrate.js.
# Calibrating the order book against nameplate instead is how a plant ends up with a book it was never going to serve.
SCHEDULE_FRICTION = 0.60
REGULATED_SHARE = 0.30       # share of customers with an approved-site matrix
MIN_LIFE_MONTHS = (12, 24)   # a regulated customer's minimum remaining shelf life on receipt
QUAL_LEAD_WEEKS = (12, 36)   # qualifying a second site for a regulated customer

# S&OP: twelve months with a seasonal peak and an annual shutdown
SEASON = dict(peakMonths=[3, 4, 9, 10], peakLift=0.26, troughMonths=[7, 12], troughDrop=0.14,
              shutdownMonthOffset=7, shutdownDays=10, note="Monsoon-season agro peak, plus the annual statutory shutdown")
SOURCING = dict(buyPremium=0.18, tollPremium=0.09, tollLeadDays=21, buyLeadDays=35,
                note="Buying a stage costs more per kg than making it; tolling sits between, and both free bottleneck hours")
RM_BLOCKS = dict(minBlockKL=20.0, priceLagDays=45, note="Solvent and key raw materials come in tanker blocks; contract price resets on a lag")

# =====================================================================================================================
# EXECUTION — what actually happened in the frozen history. Deterministic shares, applied per batch by a seeded draw.
# =====================================================================================================================
EXEC = dict(
    breakdownsPerMonth=7, breakdownHours=(4, 26),
    yieldShortShare=0.22,          # batches whose assay lands low enough to matter
    offSpecShare=0.05,             # batches that fail spec outright and are re-worked
    qcDays=(1.5, 3.0),             # QC release time after drying
    utilityTripShare=0.06,         # history: concurrent duty over the cap trips a batch
    delayReasons=["Utility interruption", "Equipment breakdown", "Awaiting QC release", "Awaiting raw material",
                  "Cleaning overrun", "Effluent plant at capacity", "Operator availability"],
)

# the six generic assumptions the deck names, plus the seventh (allocation) — the Plan Studio's assumption ratchet
GENERIC_ASSUMPTIONS = [
    dict(id="clean", nuance="P1", label="A changeover time per product pair", real="A clean grade set by residue and compatibility"),
    dict(id="yield", nuance="P2", label="A fixed yield per product", real="Yield that moves with assay and conversion"),
    dict(id="hold", nuance="P3", label="Stock with unlimited shelf life", real="Intermediates with hold-time windows"),
    dict(id="util", nuance="P4", label="Reactors as independent resources", real="Shared steam, brine and vacuum"),
    dict(id="waste", nuance="P5", label="A production plan on its own", real="Effluent, solvent recycle and consent limits"),
    dict(id="licence", nuance="P6", label="Tanks sized by volume", real="Licensed quantity ceilings by hazard class"),
    dict(id="alloc", nuance="P7", label="Allocation on quantity and date", real="Allocation on spec, route and approval"),
]

# objective weights — the same five levers for both rule sets, so the comparison is about rules, not about priorities
WEIGHT_PRESETS = [
    dict(id="balanced", label="Balanced", mode="weighted", dates=46, profit=22, clean=16, util=10, waste=6, delayScale=1.0),
    dict(id="otif", label="Delivery first", mode="weighted", dates=66, profit=14, clean=10, util=6, waste=4, delayScale=1.4),
    dict(id="campaign", label="Campaign first", mode="weighted", dates=28, profit=20, clean=36, util=10, waste=6, delayScale=0.8),
    dict(id="margin", label="Margin first", mode="weighted", dates=32, profit=44, clean=12, util=8, waste=4, delayScale=0.9),
]
