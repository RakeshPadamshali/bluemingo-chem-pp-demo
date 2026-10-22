/* The ONE registry of the sixteen chemical-planning nuances this demo has to show.

   The deck (Bluemingo Specialty Chemicals, 42 slides) argues sixteen nuances in words — seven on the plant floor, nine in
   S&OP. This file is their machine-readable form: each one carries the deck's own claim verbatim, what a generic planner
   assumes instead, the page that owns it, the scenario that demonstrates it, and the Configure / Extend route from slide 39.

   Everything reads from here — the sidebar, the dashboard's deck map, each page's header chip, the scenario launcher and
   tools/verify.py. The verifier asserts a bijection: all sixteen owned, none twice, none orphaned. If a nuance has no page,
   the build fails rather than the demo quietly dropping a third of the deck. */
window.CHM_NUANCES = [
  // ------------------------------------------------------------------ plant floor (deck slides 6-19)
  { id: 'P1', no: 1, grp: 'plant', icon: 'fa-soap', name: 'Cleaning-matrix sequencing',
    claim: 'Sequence is set by the cleaning matrix, not by setup time',
    generic: 'A changeover time per product pair', real: 'A clean grade set by residue and compatibility',
    question: 'Which product follows which, and for how long',
    page: 'cleaning', scen: 'C1', route: 'Configure', module: 'Production Planning and Scheduling',
    rule: 'Changeover matrix by attribute (family, solvent class, colour load, potency), with an override table and a forbidden flag' },

  { id: 'P2', no: 2, grp: 'plant', icon: 'fa-flask-vial', name: 'Yield and assay',
    claim: 'The batch count is an estimate, because every batch yields differently',
    generic: 'A fixed yield per product', real: 'Yield that moves with assay and conversion',
    question: 'How many batches, and with what confidence',
    page: 'batches', scen: 'C2', route: 'Extend', module: 'Scheduling with Plant Analytics',
    rule: 'Yield distribution per product; the campaign is re-costed after each batch assay' },

  { id: 'P3', no: 3, grp: 'plant', icon: 'fa-hourglass-half', name: 'Intermediates and hold times',
    claim: 'Intermediates turn stock into a timing decision',
    generic: 'Stock with unlimited shelf life', real: 'Intermediates with hold-time windows',
    question: 'When stage two must start after stage one',
    page: 'stages', scen: 'C3', route: 'Configure', module: 'Multi-stage Production Scheduling',
    rule: 'Links with a minimum and a maximum lag between stage operations' },

  { id: 'P4', no: 4, grp: 'plant', icon: 'fa-temperature-arrow-down', name: 'Utilities and thermal duty',
    claim: 'Reactors cannot all run at once, because utilities set the limit',
    generic: 'Reactors as independent resources', real: 'Shared steam, brine and vacuum',
    question: 'Which batches can run together',
    page: 'utilities', scen: 'C4', route: 'Extend', module: 'Scheduling with shared-resource rules',
    rule: 'Secondary resources with an hourly capacity and a three-segment duty profile per stage' },

  { id: 'P5', no: 5, grp: 'plant', icon: 'fa-recycle', name: 'Effluent, solvents, recycle',
    claim: 'Effluent and solvent recovery are capacity, not afterthoughts',
    generic: 'A production plan on its own', real: 'Effluent, solvent recycle and consent limits',
    question: 'What the treatment plant can absorb',
    page: 'effluent', scen: 'C5', route: 'Extend', module: 'Scheduling with Supply Planning',
    rule: 'Daily limit per waste category, with recovered solvent credited back to a later batch' },

  { id: 'P6', no: 6, grp: 'plant', icon: 'fa-triangle-exclamation', name: 'Hazard and storage limits',
    claim: 'Safety and licence limits are hard constraints on the plan',
    generic: 'Tanks sized by volume', real: 'Licensed quantity ceilings by hazard class',
    question: 'What may be held on site at once',
    page: 'tanks', scen: 'C6', route: 'Extend', module: 'Supply Planning, Inventory Optimization',
    rule: 'Licensed ceiling per hazard class and per bund, checked across time, not at a point' },

  { id: 'P7', no: 7, grp: 'plant', icon: 'fa-flask', name: 'Spec-driven lot blending',
    claim: 'Orders match on specification, route and approval, not only quantity',
    generic: 'Allocation on quantity and date', real: 'Allocation on spec, route and approval',
    question: 'Which batch serves which customer lot',
    page: 'lots', scen: 'C7', route: 'Extend', module: 'Material Allocator',
    rule: 'Blend to spec: mass-weighted on active, inside the customer spec, approved route and minimum remaining life' },

  // ------------------------------------------------------------------ S&OP (deck slides 20-37)
  { id: 'S1', no: 1, grp: 'sop', icon: 'fa-chart-pie', name: 'Capacity and product mix',
    claim: 'Capacity moves with the product mix, so one tonnage number misleads',
    generic: 'One nameplate tonnage', real: 'A finite view by product mix',
    question: 'What this plant can make of THIS mix',
    page: 'capacity', scen: 'C8', route: 'Configure', module: 'S&OP, Network Optimization',
    rule: 'Capacity envelope recomputed per mix, with cleaning hours inside the envelope' },

  { id: 'S2', no: 2, grp: 'sop', icon: 'fa-ranking-star', name: 'Margin per bottleneck hour',
    claim: 'Rank products by margin per bottleneck hour, not per tonne',
    generic: 'Margin per tonne', real: 'Margin per hour of the constraint',
    question: 'Which product to favour when the plant is full',
    page: 'capacity', scen: 'C9', route: 'Configure', module: 'S&OP, Network Optimization',
    rule: 'Contribution divided by hours on the binding resource, per product' },

  { id: 'S3', no: 3, grp: 'sop', icon: 'fa-handshake', name: 'Make, buy or toll',
    claim: 'Make, buy or toll is a recurring call, not a one-time decision',
    generic: 'A fixed sourcing choice', real: 'A monthly call valued at the bottleneck',
    question: 'Make it, buy it, or have it tolled',
    page: 'sourcing', scen: 'C2b', route: 'Configure', module: 'S&OP, Network Optimization',
    rule: 'Three sourcing options per intermediate, each costed against the bottleneck hour' },

  { id: 'S4', no: 4, grp: 'sop', icon: 'fa-arrows-split-up-and-left', name: 'Co-products',
    claim: 'A co-product can cap the main product',
    generic: 'One output per process', real: 'A main product and a coupled co-product',
    question: 'What the co-product does to the main plan',
    page: 'capacity', scen: 'C10', route: 'Extend', module: 'Supply Planning, Inventory and Network Optimization',
    rule: 'Fixed co-product ratio with its own storage and disposal ceiling' },

  { id: 'S5', no: 5, grp: 'sop', icon: 'fa-truck-ramp-box', name: 'Supply blocks and price lag',
    claim: 'Raw materials arrive in blocks, and their price moves before yours does',
    generic: 'Material available when needed', real: 'Minimum order blocks and a price lag',
    question: 'When to buy, and at what exposure',
    page: 'sourcing', scen: 'C13b', route: 'Configure', module: 'Supply, Demand, Inventory Optimization',
    rule: 'Minimum buy block per raw material, with a price-effective date' },

  { id: 'S6', no: 6, grp: 'sop', icon: 'fa-clock-rotate-left', name: 'Shelf life',
    claim: 'Inventory has an expiry, so stock is not all equal',
    generic: 'Stock with unlimited shelf life', real: 'Lots with a retest date and a customer minimum',
    question: 'Which lot can still serve which customer',
    page: 'stock', scen: 'C11', route: 'Extend', module: 'Supply Planning, Inventory and Network Optimization',
    rule: 'Retest date per lot against each customer minimum remaining life' },

  { id: 'S7', no: 7, grp: 'sop', icon: 'fa-building-shield', name: 'Approved sites',
    claim: 'Which site can supply which customer is a planning constraint',
    generic: 'Any site can serve any customer', real: 'A customer-by-site approval matrix',
    question: 'Which site may ship this order',
    page: 'sourcing', scen: 'C12', route: 'Extend', module: 'Supply Planning, Inventory and Network Optimization',
    rule: 'Approval matrix by customer, site and route, with a qualification lead time' },

  { id: 'S8', no: 8, grp: 'sop', icon: 'fa-calendar-xmark', name: 'Season and shutdown',
    claim: 'Seasonal peaks and annual shutdowns are met with stock built early',
    generic: 'Level demand and a plant always running', real: 'A seasonal peak and an annual shutdown',
    question: 'How much to build before the plant stops',
    page: 'stock', scen: 'C13', route: 'Configure', module: 'Supply, Demand, Inventory Optimization',
    rule: 'Pre-build against a shutdown window, bounded by shelf life and storage' },

  { id: 'S9', no: 9, grp: 'sop', icon: 'fa-boxes-packing', name: 'Pack and postponement',
    claim: 'Hold bulk, and decide pack and label late',
    generic: 'Finished goods in their final pack', real: 'Bulk held, packed to order',
    question: 'How late the pack decision can be made',
    page: 'stock', scen: 'C13c', route: 'Configure', module: 'Supply, Demand, Inventory Optimization',
    rule: 'Pack as a postponed operation on a shared bulk lot' }
];
window.CHM_NU = {};
window.CHM_NUANCES.forEach(function (x) { window.CHM_NU[x.id] = x; });
window.CHM_NU_LABEL = function (id) { var x = window.CHM_NU[id]; return x ? (x.grp === 'plant' ? 'Plant ' : 'S&OP ') + x.no + ' · ' + x.name : id; };
