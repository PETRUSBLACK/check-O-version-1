# Check-O — planned sections (not built yet)

Petrus's plans for the app, recorded 24 September 2026. **None of this is to be
built until he says so.** It is here so it isn't lost and so that decisions made
now don't quietly rule any of it out.

Today Check-O is one thing: shops in Asaba selling goods. Every section below
adds a *different kind of listing* with its own provider, its own idea of
"available", and in most cases its own ratings. That shape is worth keeping in
mind whenever the current code is changed.

---

## Decision — 24 September 2026

Petrus narrowed the roadmap to **transport (drivers)** and **restaurants**.

| Section | Decision |
|---|---|
| Transport — drivers | **Keep.** The strongest fit: it feeds the core, because every shop currently arranges its own dispatch. |
| Restaurants | **Keep.** Same behaviour as shopping — something nearby, today. Some of it may already exist in the unused `dining` app. |
| Hotels | Parked. Grouped with restaurants originally, but booking a room is a different transaction — dates, one at a time, no cart. |
| GG — fairly used items | Parked. Shaped like shopping but the trust model is inverted: the seller is a stranger, and a bad experience lands on Check-O's name. |
| Real estate — land | **Out of this app.** A once-a-decade purchase doesn't belong beside weekly groceries. Its own product, sharing accounts if wanted. |
| Rentals — landlords | **Out of this app.** Same reason. |

**Neither kept section starts until the core is finished and proven:** payment,
vendors managing their own products and stock, deployment off Petrus's laptop,
and one real Asaba shop trading on Check-O for a week. The trigger for starting
either is users asking for it — not a free afternoon.

The parked and removed sections are kept below in full. Nothing is lost, and
Petrus can change his mind.

---

## 1. Transport — drivers for hire

Drivers register in the app and their **availability** is visible. When a
business owner needs a ride, they open a list of drivers who are free and pick one.

- Drivers must be **authenticated and verified** before they appear.
- Drivers are **rated by business owners and buyers**.

*Needs deciding later:* what "verified" means in practice (licence, vehicle
papers, who checks them); whether availability is a switch the driver flips or
comes from their actual jobs; whether Check-O takes a cut or only introduces
the two parties; whether this also carries Check-O's own deliveries, which today
each shop arranges itself.

## 2. Real estate — land, sold by portion

Real estate companies get their own section where they register **land** and the
**portions** it is divided into, and can see at a glance whether each portion is
**sold or still available**.

*Needs deciding later:* who may register as a real estate company and how that's
checked; whether a portion is reserved as well as sold, and for how long; whether
money moves through Check-O or the platform only lists; how portions are shown —
a plot map, or a list.

## 3. Rentals — landlords and vacant buildings

Landlords register **vacant buildings** for prospective tenants to browse, with
the **price**, and it must be **clearly stated when an apartment has been taken**.

*Needs deciding later:* who marks a place as taken and how it's kept honest —
a stale "available" listing is the thing that kills rental sites; whether tenants
enquire in the app or just get a phone number; yearly vs monthly rent, which
matters for how price is shown.

## 4. Hotels and restaurants

**Hotels:** a user searches the app for **available rooms across all hotels**,
with prices.

**Restaurants:** a user searches for **a particular meal** and sees which
restaurants have it and at what price.

Both are **rated by users**.

*Needs deciding later:* whether rooms can be booked and paid for in the app or
only found; how a hotel keeps room availability current; how meals are named so
search works — "jollof rice" written six ways won't match — which probably means
a shared list of dishes rather than free text.

Note: the codebase already has a `dining` app with menus, menu sections and
reservations, and `RESTAURANT` and `HOTEL` are already business categories. Some
of this may be a matter of surfacing what exists rather than building new.

## 5. GG — fairly used items, sold person to person

A section for people selling their **fairly used items** through the platform.
Petrus described this as the most complex of the five.

**What "GG" means:** Petrus says GG is an existing Nigerian platform for selling
fairly used goods, and this section should do the same thing. The exact platform
hasn't been pinned down yet — searching didn't turn up a clear match, so get the
name or web address from him before treating it as a model to copy, and before
using "GG" as the section's name in the app. Naming a section after another
company's platform is a trademark risk; the internal name can stay GG while the
customer-facing one is our own.

*Needs deciding later:* how an individual seller differs from a registered shop
(no RC number, no business, no approval process); how a buyer is protected when
the seller is a stranger rather than a vetted shop; whether money is held until
the item changes hands; how disputes are handled; how a used item's condition is
described honestly. This one carries the most risk of the five and deserves the
most thought before any code.

---

## Things all five share

Worth building once rather than five times, when the time comes:

- **Verification of a provider** — driver, estate company, landlord, hotel,
  private seller. Check-O already verifies shops; that is the same problem.
- **Ratings** — asked for explicitly in sections 1 and 4, and wanted everywhere.
  There is already a `BusinessRating` model.
- **"Is it still available?"** — a sold portion, a taken apartment, a booked
  room, an item already sold. Every section has this, and in every one a stale
  listing is what loses users' trust.
- **Search across a category**, not within one provider — rooms across all
  hotels, a meal across all restaurants.
