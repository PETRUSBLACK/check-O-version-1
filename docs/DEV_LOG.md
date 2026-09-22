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
- **Backend (do before stage 3):** `ProductSerializer` exposes `cost_price` to everyone — hide it from
  customers. Its `available_stock` also disagrees with the model (should be min(stock, allocation)).
- Old `mobile/src/services/cart.ts`, `orders.ts`, `ai.ts` send the wrong fields — replaced in stages 3–5.
- Batch 3: move `ai/` and `ml/` inside `backend/` so AI works on Railway; set `ANTHROPIC_API_KEY`.
- Cleanup: old `api.py` files, `config/settings.py`, `backend/management/`, unused `realtime/`,
  numpy/pandas/scikit-learn in requirements, `STATICFILES_STORAGE` → `STORAGES` in prod.py.
- Vendor "confirm before payment" feature (before real vendors).
- Railway cron job for `run_tasks --scheduled`.
- Mobile app: stages 1–6 (setup/login → home → shop/product → cart/checkout → my orders → vendor side).
