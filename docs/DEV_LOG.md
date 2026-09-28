# Check-O / SmartMall — Development Log

Running record of changes, decisions and things to check. Newest first.

> **Planned sections are in [`FUTURE_FEATURES.md`](FUTURE_FEATURES.md)** — transport,
> real estate, rentals, hotels and restaurants, and GG (fairly used items). Not to be
> built until Petrus says so, but read it before any change that would rule them out.

---

## ⚠️ REMEMBER — Wednesday Paystack test (Week 2)

- **Each payment attempt now gets its own Paystack reference**
  (`SM-<checkout-or-order-id>-<random>`). Before this, if a customer closed the
  payment page and tried again, Paystack rejected the retry as a *duplicate
  reference*. When testing, deliberately **abandon a payment and retry** to
  confirm the retry now works.
- **The database update fills in the shop on existing orders automatically**
  (migration `orders/0004_checkout_groups_one_order_per_shop`). This was checked
  on an older copy of the database. After running `python manage.py migrate` on
  Railway, open a few old orders in admin and confirm the **Business** field is filled.
- Pay through a **checkout** (`checkout_group_id`), not a single order, when the
  cart has items from more than one shop.
- Partial refunds: if one shop in a multi-shop checkout cancels after payment,
  refund **only that shop's order total** in the Paystack dashboard (see
  Admin → Orders → *Refunds to process*), then click *Mark as refunded*.

---

## 2026-09-26 — Docker Compose: the worker starts with everything else

`docker compose up` now brings up four things instead of three: Postgres, Redis,
the web server, and a **worker** running `run_tasks --loop`. One command, no
separate terminal for the scheduler, and it comes back on its own if it dies —
which matters, because a dead worker fails silently. Nothing errors; unpaid orders
simply stop being cancelled until a vendor complains her stock is gone.

To be clear about what Docker does and doesn't do here: it doesn't schedule
anything. It packages and starts processes. What Compose gives us is that the
worker starts *alongside* the server instead of being remembered by hand. Same
split as Railway (web service + scheduled service), rehearsed locally.

Two things fixed while in the file:

- **Local Docker was running production settings.** The Dockerfile sets
  `DJANGO_SETTINGS_MODULE=config.settings.prod` for Railway, and compose never
  overrode it — so `DEBUG: "1"` in the environment did nothing, because `prod.py`
  hard-codes `DEBUG = False`. That matters more than it sounds now that photos
  exist: media files are only served when DEBUG is on, so every product photo
  would have 404'd under Docker while working fine outside it. Compose now sets
  `config.settings.dev` explicitly.
- **The two Django services share one environment block** (a YAML anchor). The
  worker drifting onto a different `DATABASE_URL` than the web server is the
  nastiest version of this bug: everything looks healthy and the worker
  dutifully cancels orders in a database nobody is using. Now they can't diverge.

The worker waits for the web service's healthcheck before starting, which is how
it knows migrations have finished. The image is slim with no curl, so the check
asks Python to fetch `/api/health/`.

Validated with `docker compose config`.

### Petrus: note before you use it
Compose uses **Postgres**, a different database from the `db.sqlite3` you use
outside Docker. Your seeded shops and last night's orders do not follow you in:
```
docker compose run --rm backend python manage.py seed_demo --with-orders
docker compose run --rm backend python manage.py createsuperuser
```
Expo still runs on the host (`npx expo start -c` in `mobile/`), because it needs
your own network to reach your phone. So it's two terminals, not one.

The SQLite workflow is untouched — this sits there unused until you run
`docker compose up`.

---

## 2026-09-26 — The scheduler: unpaid orders now actually get cancelled

The 30-minute payment window was never a timer. The deadline is written on the
order and something has to come along and act on it. Nothing did, so an order
Petrus abandoned at 18:05 was still `pending_payment` nine hours later — and
Mama Nkechi's groundnut oil was reading **sold out to every shopper in Asaba**,
because the three bottles were still held by a payment nobody was going to finish.

That's the real cost of a missing scheduler, and it's why this isn't optional.

**Development — `python manage.py run_tasks --loop`**

Windows has no cron, so looping is the answer: leave it in its own terminal
beside the dev server. `--every` sets the gap (default 300s). It survives a
failing round rather than dying, finishes the round in hand on Ctrl+C or SIGTERM
instead of stopping mid-task, sleeps only the remainder so a slow round doesn't
push the schedule out, and calls `close_old_connections()` each round so a
long-lived loop never sits on a connection the database has dropped.

**Production — `railway.cron.toml`**

A second Railway service off the same repo, start command
`python manage.py run_tasks --scheduled`, `cronSchedule = "*/5 * * * *"`. It has
to be a second service: Railway runs a service's *own* start command on its
schedule, so a schedule on the web service would restart the web server every
five minutes. Setup steps are in the file's header — including the one that's
easy to miss, giving it the same `DATABASE_URL`, or it runs happily against
nothing. Railway's minimum interval is 5 minutes, which is the cadence these
tasks were written for, and it skips a run if the previous one is still going.
`restartPolicyType = "never"`: the next run is five minutes away, so retrying a
failed one buys nothing.

If a cron service isn't wanted, the file's header also gives the always-on worker
alternative (`--loop` as the start command). Same command either way.

**A bug found while doing it.** `--scheduled` decides the hourly and daily tiers
from a window — "is it the first 5 minutes of the hour" — which is correct for a
5-minute cron and wrong for anything else. At 60-second ticks it would have run
every hourly task **five times an hour**. So `--loop` doesn't use the window; it
remembers when each tier last ran. (In-memory, so a restart can re-run an hourly
tier once. These tasks only expire what is already due, so that is harmless.)

**Verified.** 304 tests (9 new in `core/tests/test_run_tasks_command.py`),
covering the frequent tier never being skipped, hourly/daily firing once and not
once per tick, the loop surviving a thrown error mid-round, and — with no mocks —
a real expired order being cancelled and its stock returned.

Then against a **copy of Petrus's own database**: both stale orders went to
`cancelled` / `payment_timeout` / `system`, and the stock went back to the right
buckets — 3 bottles of oil to the shop's own stock, 2 blood pressure monitors to
the Check-O allocation, each to where it came from.

### Petrus: how to use it
Third terminal, in `backend/`, alongside the server and Expo:
```
python manage.py run_tasks --loop
```
Leave it open. Without it, unpaid orders never expire and stock stays locked.
Your two stale orders will clear on the first round.

### Note for deployment
The cron service is **not optional**. Without it one abandoned payment holds a
vendor's stock until another shopper happens to touch the same product, and the
vendor sees her goods as sold out with no idea why.

---

## 2026-09-26 — Product photos, and three silent bugs

Petrus noticed products had no pictures. They didn't, and it turned out to be
four separate things stacked on top of each other — three of which failed
*silently*, which is why nothing had ever complained.

**The backend already had the hard part.** A `ProductImage` model and a working
`POST /api/product-images/` with ownership checks existed since Batch 1. Nothing
needed building there. But nothing could have worked either:

1. **`MEDIA_URL` had no leading slash.** `"media/"` makes a photo's `.url` a
   *relative* path, so `build_absolute_uri()` resolved it against whatever
   endpoint asked — producing `/api/products/<id>/media/products/rice.jpg`. Now
   `"/media/"`.
2. **Nothing served the media folder.** Django doesn't serve uploaded files by
   itself and `config/urls.py` never mapped it. Upload would succeed, every photo
   would 404. Added `static(MEDIA_URL, document_root=MEDIA_ROOT)`, which is
   development-only by design — `static()` returns nothing when DEBUG is off.
3. **The one that cost real time.** A photo must be sent as multipart, because it
   carries a file. DRF treats multipart as HTML form input, and for a
   `BooleanField` that means *an omitted field becomes `False`* rather than the
   model default (`BooleanField.default_empty_html`, DRF 3.18). The app doesn't
   send `is_active` — it shouldn't have to — so every photo was saved with
   `is_active = False`: HTTP 201, file on disk, never displayed, nothing logged.
   Fixed with a `FormBoolean` field in the serializer that honours its declared
   default. Worth remembering: **any boolean on a multipart endpoint has this
   trap.**

**Also in the serializer:** the first photo on a product becomes the cover
automatically, and marking a new cover demotes the old one, so a product is never
coverless and never has two covers.

**In the app:** `expo-image-picker` (in Expo Go, so no development build needed).
`PhotoPicker` sits near the top of the vendor's product screen — take a photo or
choose from the gallery, see the strip, star one as the cover, delete one.
Photos upload the moment they're chosen rather than waiting for "Save changes",
so backing out without saving doesn't lose them.

Photos are taken at `quality: 0.55`, cropped square. Square is the right shape for
the product grid anyway, and crop plus compression keeps a phone photo to a few
hundred KB — which matters when a vendor is listing twenty items on metered data.
If real Asaba photos still come out heavy, `expo-image-manipulator` is the next
step; it's in Expo Go too.

Adding a product now lands on that product instead of back on the list, because
that's the first moment a photo can be attached. And the vendor's product list
shows a thumbnail, with a dashed "No photo" tile where one is missing — which
turns an invisible gap into a visible job.

The shopper screens needed nothing: product cards, the product page and the cart
already read `cover_image`.

**Verified:** 295 tests (11 new in `apps/products/tests/test_photos.py`), and
separately against a *real running server*, uploading over HTTP with exactly the
payload the app sends — no `is_active` — then fetching the photo back at the URL
the API handed out and comparing the bytes. That live check matters because
Django forces `DEBUG=False` in tests, so `static()` serves nothing and a unit test
*cannot* prove the URL works. The test suite checks the file landed on disk at the
right path; the live run proved it is reachable.

TypeScript clean, Android bundle exports.

### Petrus: one thing to do
In `mobile/`, run `npx expo install expo-image-picker`, then `npx expo start -c`.

### Still open on photos
- **Storage.** Files go to `backend/media/`. A Railway container's disk is wiped
  on every deploy, so on deployment every photo vanishes. Needs Cloudinary or S3 —
  a settings change, not a rewrite, but it must happen before real vendors upload.
- The 29 demo products still have no photos; there's nothing real to seed them
  with. Photograph a few by hand to see how the grid looks full.

---

## 2026-09-25 — Stage 7: paying with Paystack

The app could place an order but not pay for one. Now it can, end to end, without
Petrus's key being needed to build it.

**How the money moves.** The app asks the backend to start a payment; the backend
asks Paystack for a payment page and gets back a link; the app opens that link in a
browser window inside the app; the customer pays; Paystack sends them back to
`checko://payment/callback`, which closes the window and hands control to the app;
the app then asks the backend *"did that go through?"* and the backend asks Paystack.

**Why the app asks instead of waiting.** Paystack normally confirms a payment by
calling a webhook — its server calling ours. It cannot call a laptop, which has no
public address, so on the current setup a webhook would never arrive at all. Even on
Railway later, a webhook can land after the customer is already staring at the screen.
So the app asks directly. The webhook still works when there is one; both routes end
in the same function, and checking twice is harmless.

- New: `POST /api/payments/{id}/verify/` (`apps/payments/views/verify_view.py`).
  Only the person who owns the checkout may ask. Gateway errors come back in plain
  words ("That payment didn't go through. You can try again."), not stack traces.
- `confirm_payment_via_webhook` restructured. Two real bugs fixed:
  a failed payment used to be *recorded* inside a transaction that then raised, which
  rolled the record back — so a failure left no trace; and the call to Paystack sat
  inside a database transaction holding a locked row across a network call. Now the
  network call happens first, outside; only the short write is in a transaction.
- **Underpayment is refused.** If Paystack reports less than the order total, the
  payment is marked failed and the orders stay unpaid.
- `PAYMENT_CALLBACK_URL` setting (default `checko://payment/callback`). The old code
  sent customers to `FRONTEND_ORIGIN/payment/callback`, a web address that does not
  exist — they would have been stranded on a dead page after paying.
- `PAYSTACK_BASE_URL` setting: lets the whole flow be tested against a stand-in
  gateway. Unset, it points at the real Paystack. That is how this was proved without
  a key: a fake Paystack was run locally, a real payment walked through it, the orders
  went to **paid**, a second check returned the same answer, and a stranger asking
  about someone else's payment got refused.
- A vendor may now pay for their own shopping. Ownership is already enforced by the
  queryset, so the old "customers only" check just locked people out.

**App side:** `src/app/pay.tsx` (the paying screen), `src/services/payments.ts`,
"Pay for this order" on an unpaid order, and the order-placed screen now says
*Payment received* when it has been.

If the customer closes the payment window, the app still checks — they may have paid
and then closed it.

Tests: 284 passing. TypeScript clean, Android bundle exports.

### Petrus: two things to do
1. In `mobile/`, run `npm install` — a new package (`expo-web-browser`) was added.
2. When you have the Paystack test key, create `backend/.env` with the line
   `PAYSTACK_SECRET_KEY=sk_test_...` — **type it into that file, never into the chat**.
   `.env` is already ignored by git, so it never leaves your laptop.

---

## 2026-09-24 — Stage 6b: a shop manages its own products

Until now every price change in Asaba went through Petrus typing into Django admin.
That breaks at about shop number three. A shop can now do it from its own phone.

- New **Products** tab on the seller side: every product with its price, what's
  available, and how much is set aside for Check-O. Sorted by what needs attention —
  sold out first, then running low. A banner counts anything sold out, because a
  sold-out product is invisible to customers and the shop may not realise.
- **Edit** a product: name, price, how many are in the shop, the Check-O split,
  description, and whether it shows on Check-O at all. Hiding never deletes.
- **Add** a product, including setting the Check-O split while adding rather than
  saving and editing again.
- The allocation is asked as **"How many can Check-O sell?"** with *All of them* or
  *Only some*, and it does the arithmetic out loud: "6 on Check-O · 12 for your shop".
  Nobody has to understand the words "channel allocation".

### Backend
- `ProductSerializer.validate` refuses an allocation larger than stock. The dedicated
  allocation endpoint already did; a plain PATCH did not, so the two ways in disagreed.
  **This also catches lowering stock below an existing allocation**, which would
  otherwise have the shop quietly promising Check-O more than it has.
- `POST /api/products/` now accepts `smartmall_allocation` and `category` when adding.
- Tests: 275 passing (13 new).

Checked in a browser against live data: set aside 20 of 40 bags of rice, was refused
at 999, and added a new product from scratch with its split.

## 2026-09-24 — Stage 6a: the seller side (incoming orders)

**One app, two sides.** Signing in as a seller now lands on the seller's own screens — dark green,
so a shop owner can tell at a glance which side of Check-O they're looking at — instead of the
shopping tabs. Customers are unaffected.

- **Orders**: "3 orders to sort out", what they're worth, and a To do / All toggle. Each card
  shows the reference, what to pack, delivery or collection, the total, and the one next step.
  The tab carries a badge, because a shop must know something is waiting without looking.
- **Order detail**: what to pack, where it goes, and a single button for the next step —
  Start preparing → Packed and ready → Sent out → Delivered, or for collection
  Start preparing → Ready to collect → Customer collected it.
- **Collection needs the customer's code.** The shop types the code from the customer's phone
  before handing anything over; a wrong code is refused. The shop is never shown the code.
- **"I can't fulfil this order"** makes the shop pick a reason (out of stock / damaged / other,
  with a note). The customer is told why, the stock goes back, and a paid order is flagged for
  refund. Verified: stock returned to 25 and the reason reached the customer's screen.
- **My shop** shows the shop, its category, address, and whether it delivers and for how much —
  including "Waiting for approval" when it isn't live yet. `GET /api/businesses/mine/` is new.

### Two bugs found while building this
- **Security: the pickup endpoints never checked who owned the order.** Any vendor could mark
  another shop's order ready for collection, or confirm collection on it. Both now check the
  shop, and there are tests that fail without the check.
- **A collection order couldn't be marked ready** after being prepared: the transition table only
  allowed `processing → packaging`, forcing a shop putting an order behind the counter through a
  delivery step. `processing → ready_for_pickup` is now allowed.
- Vendor order list now filters on the order's shop rather than joining through line items, which
  could list the same order twice.

Tests: 262 passing. Whole seller flow driven in a browser against live data: delivery order
advanced through every stage, collection order taken to ready and the wrong code refused, and an
order cancelled with a reason.

## 2026-09-24 — Stage 5: My Orders, and demo data
- **Orders tab** is real: every order newest first, with the shop, what's in it, the total, how
  it's coming, and a status in the customer's words ("Being prepared", "Ready to collect") rather
  than the database's. A collection code shows on the row once the shop marks it ready.
- **Order detail**: full breakdown, delivery address or a large collection code with its deadline,
  and **Cancel this order** while the shop hasn't started. Confirmation is asked *in the page*, not
  through an OS dialog — `Alert.alert` doesn't exist on web, so the button silently did nothing
  there, and an OS dialog looks nothing like the rest of the app.
- A cancelled order explains itself: who cancelled, and why when the shop gave a reason.
- Checked end to end in a browser: order placed → appears in Orders → opened → cancelled →
  stock returned to the shop and the reservation released.

### Demo data
`python manage.py seed_demo` fills the database with six Asaba shops and 29 products; `--wipe`
removes them again, including any test orders placed against them. Sign in as
`shopper@demo.check-o.ng` / `checko12345`. Deliberately awkward cases included: one sold-out item,
two low-stock items, and rice with 40 in the shop but only 12 released to Check-O.

### Fixes
- `BusinessLocation` was **not registered in admin at all**, so a shop's coordinates couldn't be
  set. Now edited on the shop's own page, with a **Coordinates** box that takes a pasted Google
  Maps link or "6.2003, 6.7331". A shop can't be saved without a location, because such a shop
  would silently never appear in the app.
- The app now works out the laptop's address from Expo instead of `.env`, so a hotspot change no
  longer breaks the phone. `.env` still wins if set — use it only to point at Railway.
- The "can't reach" error now names the address it tried, in development.
- Removed the notification bell from Home: it was a button wired to nothing.
- Selected category tile now fills solid green; the old 2px outline was too quiet to notice.

## 2026-09-23 — Stage 4a: checkout with per-shop delivery

**Decision: Check-O runs no riders.** Each shop says whether it delivers and sets its own flat
fee; the customer picks delivery or pickup **per shop** at checkout. Shops already know their own
dispatch people, so this needs nothing from you before launch.

- `Business.delivers` + `Business.delivery_fee`. **Editable straight from the list** in
  Admin → Businesses, because you'll be changing it constantly while signing shops up.
- `Order` gains `delivery_fee`, `recipient_name`, `delivery_phone` (it already had
  `fulfilment_type`, `delivery_address`, `pickup_code`).
- The shop's fee is **copied onto the order** at checkout, so a shop raising its fee later never
  changes an order the customer already agreed to.
- `Order.total` now includes the delivery fee, so payments and refunds needed no change at all.
  `order.items_total` is the goods on their own.
- A pickup order gets a **collection code** and a 48-hour deadline, and carries no address —
  choosing pickup for one shop never leaks the delivery address onto that shop's order.
- `POST /api/cart/checkout/` takes `{fulfilment: {shop_id: "delivery"|"pickup"}, delivery:
  {recipient_name, phone, address}}`. Asking a shop that doesn't deliver to deliver is refused;
  so is delivery without a name, phone and address — and the cart is kept intact when it is.
- `GET /api/cart/` now returns a `shops` block (name, delivers, fee) so the checkout screen needs
  one call, not one per shop.
- **Mobile:** checkout screen (per-shop delivery/pickup, address form, cost breakdown) and an
  order-placed screen showing each shop's total, collection codes and delivery address. The Cart
  button now goes to checkout, and is blocked if a line is over what the shop has left.
- Fixed two pre-existing crashes outside `backend/`: `ai/tools/smartmall_tools.py` and
  `ml/ranking/ranker.py` imported `BusinessStatus` from the wrong module, so **AI product search
  and ML search ranking failed silently every time**. They import from `apps.businesses.choices` now.
- Tests: 236 passing (14 new for delivery). Whole flow driven in a browser against a live backend:
  two shops in one cart, one delivering and one collect-only, validation, and placing the order.

**Not done yet (stage 4b):** payment. The order-placed screen says so plainly, and the orders
cancel themselves after 30 minutes as designed.

## 2026-09-23 — Mobile stage 3: shop page, product page, cart
- **Shop page**: cover, rating, address, and the shop's products in a 2-column grid.
  A search box appears once a shop has more than 6 products. Sold-out items are dimmed.
- **Product page**: photo, price, "In stock" / "Only 3 left" / "Sold out", description,
  quantity stepper capped at what's actually available, and **Add to cart**.
- **Cart tab**: real cart grouped by shop, per-shop subtotals, quantity + / − / remove,
  grand total, and a count badge on the tab. Checkout button is there but disabled — stage 4.
- Product search results now show the shop name and open the product page.
- **Vendors can shop.** The old rule let a vendor see only their own shop and products, so a
  vendor account saw an empty app and got 403 on the cart. Now any signed-in user can browse and
  buy — except from their **own** shop, which is refused with a clear message.
- Stock messages rewritten for shoppers: "Mama Nkechi Stores has 12 of this on Check-O, and you
  already have 2 in your cart" instead of "Only 12 unit(s) available for SmartMall orders".
- Products now carry `business_name` and `cover_image` (the vendor's cover photo, or the first
  one), prefetched so a grid is still one query. Shop detail now includes rating.
- Checked: TypeScript clean, Android bundle builds, and the whole flow — sign in, home, shop,
  product, add to cart, cart — driven in a browser against a live local backend.

## 2026-09-23 — Product privacy + correct stock number
- `cost_price`, `stock`, `smartmall_allocation` and `low_stock_threshold` are now **hidden from
  customers** — only the shop owner and admins see them. Before this, any customer viewing a product
  could read the shop's buying price, i.e. its profit margin.
- `available_stock` in the API now matches the model: **min(stock, allocation)**. Before, a shop that
  allocated 20 units to Check-O but then sold down to 5 in the shop still advertised 20 online.
- Schema now types `available_stock` as a number and `uses_channel_allocation` as true/false.
- Tests: 220 passing.

## 2026-09-22 — Mobile app: stages 1–2 (setup, sign in, Home)
- New Expo app in `mobile/` on **SDK 57** (the version the current Expo Go supports). SDK 51 from the
  old `package.json` would no longer open in Expo Go.
- Sign in, create account (buy / sell), forgot password, auto sign-in on reopen, sign out.
- Home: location (falls back to central Asaba), search, category tiles filter nearby shops,
  "Shops near you" from `/api/shops/nearby/`. Product search screen.
- Orders, Cart and Shop screens are placeholders until stages 3–5.
- Checked: TypeScript clean, Android bundle builds, flows tested in a browser against the local backend.

## 2026-09-22 — Multi-shop checkout
- One cart → **one order per shop** → **one payment** (`CheckoutGroup`).
- `POST /api/cart/checkout/` now returns the checkout (total, amount due, orders).
- `POST /api/payments/initiate/` takes `checkout_group_id` + `provider`; amount is
  calculated by the server.
- New: `GET /api/checkouts/{id}/`. Orders now include `business` / `business_name`.
- Unique Paystack/Flutterwave reference per payment attempt.
- Tests: 210 passing.

## 2026-09-21 — Stock holds, cancel rules, refunds, background tasks
- Unpaid orders hold stock for **30 minutes**, then cancel and return stock.
- Stock always returns to the bucket it came from (Check-O allocation vs main stock).
- Cancel rules: customer until the shop starts processing; vendor until shipping
  (reason required: out_of_stock / item_damaged / other + note).
- Paid + cancelled orders → **Refunds to process** (manual refund in Paystack).
- Per-shop *Vendor cancellations* count in admin.
- Vendor reminder after 2 hours on a paid, untouched order (no auto-cancel).
- `python manage.py run_tasks --scheduled` (cron every 5 min on Railway later).

## 2026-09-21 — Batch 2: order/shipment sync + test suite
- Order status follows shipment status (processing → packaging → shipped → delivered).
- Test suite fixed (was ~55/155 passing).

## 2026-09-21 — Batch 1: core fixes
- Fixed Swagger schema crash (`full_address` field) and nearby-shops 500.
- Restored cart URLs (`cart/add|update|remove|checkout`) + missing import.
- Routed channel allocation endpoints; fixed product images endpoint.

---

## Before testing checkout
1. Run `python manage.py migrate` (two new migrations).
2. In Admin → Businesses, tick **Delivers** for the shops that do and set a **Delivery fee**.
   A shop left unticked is collect-only, which is the safe default.

## Open items
- Location on Home is GPS + Google's name for the spot, which is often wrong in Asaba. Needs a
  tappable picker (choose your area / confirm GPS) — doing it with the checkout work, where the
  delivery address actually matters.
- Old `mobile/src/services/cart.ts`, `orders.ts`, `ai.ts` send the wrong fields — replaced in stages 3–5.
- Batch 3: move `ai/` and `ml/` inside `backend/` so AI works on Railway; set `ANTHROPIC_API_KEY`.
- Cleanup: old `api.py` files, `config/settings.py`, `backend/management/`, unused `realtime/`,
  numpy/pandas/scikit-learn in requirements, `STATICFILES_STORAGE` → `STORAGES` in prod.py.
- Vendor "confirm before payment" feature (before real vendors).
- Railway cron job: **config written 2026-09-26** (`backend/railway.cron.toml`).
  Still has to be created as a second service in the Railway dashboard at deploy time.
- **Paystack live test** — the flow is built and proved against a stand-in gateway
  (2026-09-25). Still needs Petrus's `sk_test_` key in `backend/.env` and one real
  card run, including deliberately abandoning a payment and retrying.
- Product photos: **done 2026-09-26.** Remaining piece is production storage —
  `backend/media/` is wiped on every Railway deploy, so this needs Cloudinary or S3
  before real vendors upload anything.
- Vendor: shop **self-registration**, deliberately last.
- "See my orders" on the order-placed screen lands on the Orders placeholder until stage 5.
- Vendors can't set their own delivery fee from the app yet — admin only (stage 6).
- Shop page shows `Business.address`, which most vendors leave empty; the *location* address
  (used for distance) is a different field. Decide which one the shop page should show.
- Product photos: done 2026-09-26 (see that entry).
