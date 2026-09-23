# Check-O / SmartMall — Development Log

Running record of changes, decisions and things to check. Newest first.

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

## Open items
- Location on Home is GPS + Google's name for the spot, which is often wrong in Asaba. Needs a
  tappable picker (choose your area / confirm GPS) — doing it with the checkout work, where the
  delivery address actually matters.
- Old `mobile/src/services/cart.ts`, `orders.ts`, `ai.ts` send the wrong fields — replaced in stages 3–5.
- Batch 3: move `ai/` and `ml/` inside `backend/` so AI works on Railway; set `ANTHROPIC_API_KEY`.
- Cleanup: old `api.py` files, `config/settings.py`, `backend/management/`, unused `realtime/`,
  numpy/pandas/scikit-learn in requirements, `STATICFILES_STORAGE` → `STORAGES` in prod.py.
- Vendor "confirm before payment" feature (before real vendors).
- Railway cron job for `run_tasks --scheduled`.
- Mobile app: stage 4 (cart → checkout → payment), 5 (my orders), 6 (vendor side).
- Shop page shows `Business.address`, which most vendors leave empty; the *location* address
  (used for distance) is a different field. Decide which one the shop page should show.
- Product photos: nothing in the app uploads them yet, so every product shows a placeholder
  icon. Vendor product management (stage 6) is where that goes.
