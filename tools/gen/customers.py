"""Fictional customers, their site/route approvals and their shelf-life minimums.

A regulated customer is what turns allocation from "quantity and date" into "spec, route and approval": it names the sites
it has qualified, the filed route it buys against, and the remaining shelf life it insists on at receipt.
"""
from . import config as CFG
from .common import R, pick, rint, between


def build_customers(products):
    prods = [p for p in products if p["sell"]] if products and "sell" in products[0] else products
    reg_products = [p["id"] for p in prods if p.get("regulated")]
    gen_products = [p["id"] for p in prods if not p.get("regulated")]
    out = []
    n_reg = int(round(len(CFG.CUSTOMER_NAMES) * CFG.REGULATED_SHARE))
    # Every product must have real demand, or the nuance it carries has no story on screen. Hand each pool out
    # round-robin first — so no product is left with two order lines — then add random extras on top.
    def anchors_for(pool, j):
        if not pool:
            return []
        L = len(pool)
        return [pool[j % L], pool[(j + max(1, L // 3)) % L]]
    for i, name in enumerate(CFG.CUSTOMER_NAMES):
        cid = "C%03d" % (i + 1)
        regulated = i < n_reg
        region = pick(CFG.CUST_REGIONS) if regulated else pick(["IN", "IN", "SEA", "LATAM", "EU"])
        # what this customer buys: regulated ones buy filed products, the rest buy intermediates and dyestuff feeds
        pool = reg_products if regulated else gen_products
        anch = anchors_for(pool, i if regulated else i - n_reg)
        k = min(len(pool), rint(1, 3 if regulated else 4))
        buys = sorted(set(anch + R.sample(pool, k)))
        # approved sites. Every regulated customer has qualified this plant; only some have qualified a second site.
        if regulated:
            sites = ["UNIT-2"]
            if R.random() < 0.45:
                sites.append("UNIT-7")
            if R.random() < 0.2:
                sites.append("TOLL-A")
        else:
            sites = ["UNIT-2", "UNIT-7", "TOLL-A"]
        out.append(dict(id=cid, name=name, region=region, regulated=regulated, sites=sites, buys=buys,
                        minLifeMonths=rint(*CFG.MIN_LIFE_MONTHS) if regulated else 0,
                        qualWeeks=rint(*CFG.QUAL_LEAD_WEEKS) if regulated else 0,
                        filedRoute=regulated, coaRequired=regulated,
                        note="Approved sites: " + ", ".join(sites)))
    return out


def approval_rows(customers):
    """The approved-site matrix as master rows: one row per customer x site, with its qualification lead time."""
    rows = []
    for c in customers:
        for s in CFG.SITES:
            ok = s["id"] in c["sites"]
            rows.append(dict(id="%s|%s" % (c["id"], s["id"]), customerId=c["id"], siteId=s["id"],
                             approved=ok, qualWeeks=0 if ok else (c["qualWeeks"] or rint(*CFG.QUAL_LEAD_WEEKS)),
                             why="Qualified" if ok else ("Not qualified — %d weeks to file and validate" % (c["qualWeeks"] or 24))))
    return rows


def customers_for(customers, product_id):
    return [c for c in customers if product_id in c["buys"]]
