# Check-O — Roadmap to a complete product

Written 2 October 2026. Companion to [`DEV_LOG.md`](DEV_LOG.md) (what has been done)
and [`FUTURE_FEATURES.md`](FUTURE_FEATURES.md) (sections deliberately parked).

Ordered by **milestone**, not by feature, because the order matters more than the
list. Each milestone is something that is true of the business when it is finished,
not a pile of code.

Markers: **[P]** only Petrus can do it · **[C]** Claude can build it ·
**[D]** a decision is needed before code is possible.

---

## M0 — Ready to show a real shop
*Target: one sitting. Almost done.*

- [ ] **[P]** `npx expo install expo-image-picker` in `mobile/`, then uncomment the
      two marked lines in `src/app/vendor-product/[id].tsx`. Photos are built and
      tested; they are only switched off because the package was never installed.
- [ ] **[P]** Test a **declined** payment on Paystack's simulator. The order must
      stay unpaid with stock still held, and the app must offer a retry. A bug of
      exactly this family was already found and fixed once in `gateway.py`.
- [ ] **[P]** Test a **two-shop** payment against real Paystack. Wednesday's was one
      shop, collection only — so per-shop delivery fees and one payment splitting
      into two orders are still only proven in tests.
- [ ] **[C]** Fix the shop page address: it shows `Business.address`, which most
      vendors leave empty, while distance uses the *location* address. One of the
      two, consistently.

---

## M1 — One real shop trading for a week
*Target: 2 weeks. The milestone that decides whether any of the rest is worth building.*

Nothing here needs hosting. Your laptop and a hotspot are enough — that is how
the first payment was proved.

- [ ] **[P]** Find one shop. Ideally a trader you already buy from.
- [ ] **[P]** Sit with the owner. Let **her** choose the items, photograph them with
      your phone, and type the real prices. Watch where her hands hesitate.
- [ ] **[P]** Have a friend order and pay for one thing, on their own phone.
- [ ] **[P]** Pay her by bank transfer yourself, by hand. Settlement is not built
      and does not need to be for one shop.
- [ ] **[P]** Write down what you learn in `DEV_LOG.md`, including anything she
      found confusing or refused to do.

**The questions to come away with.** These are worth more than any feature:
will a trader type prices into a phone at all? Is ₦1,500 for delivery normal or
insulting in her area? Does the pickup code make sense to her? What does she do
when an order arrives while she is serving a walk-in customer? And the one that
matters most — **would she rather just keep using WhatsApp?** If yes, that is the
most valuable thing you could learn, and far better learned now.

---

## M2 — Several shops, without you in the middle
*Target: 1–2 months after M1 succeeds. Do not start before M1.*

This is the real engineering milestone. Everything in it exists because a
marketplace with ten shops cannot route every action through you.

### 2a. Settlement — how vendors get their money
**The single biggest gap in the project. Zero lines exist today.**

- [ ] **[D] Decide: manual payouts, or Paystack split payments?**
      *Manual* — money lands with you, you transfer weekly, you take your cut off
      the top. No code, but needs discipline and bookkeeping, and a vendor who is
      unsure when her money is coming stops listing.
      *Split* — each shop gets a Paystack subaccount and Paystack divides the
      payment at the moment it is made, sending each shop its share directly. Real
      work to build, needs bank details verified per vendor, then runs itself and
      no vendor has to trust you to remember.
- [ ] **[D] Decide the commission.** A percentage? Flat per order? Nothing at
      first to attract shops? This number has to exist before any code.
- [ ] **[C]** Whichever route: a **ledger**. Per order — gross, commission, what
      the vendor is owed, whether it has been paid, when, and by what reference.
      Even manual payouts need this or you will lose track by the tenth shop.
- [ ] **[C]** A vendor-facing **earnings screen**: what you've sold, what you're
      owed, what's been paid. The thing that makes a vendor trust the platform.
- [ ] **[C]** Handle refunds against settlement — a shop that cancels after payment
      must not be paid out for that order.

### 2b. Vendor self-registration
- [ ] **[C]** A sign-up flow in the app: shop name, phone, address, category, and
      whether they deliver, with a delivery fee. The API already accepts this; the
      screen doesn't exist.
- [ ] **[C]** A location picker so the vendor pins their own shop on a map rather
      than trusting GPS, which is often wrong in Asaba.
- [ ] **[C]** Vendors set and change their own delivery fee — admin-only today.
- [ ] **[D] Decide the approval rule.** Shops have a `status` already. Do you
      approve each one by hand? Require an RC number? Let them trade immediately
      and remove bad ones? This decides how fast you can grow and how much risk
      you carry.
- [ ] **[C]** An admin queue for approving shops, if that's the answer.

### 2c. Notifications that arrive when the app is closed
- [ ] **[D] Decide: push, or one SMS, or both?** Push is free and unlimited but
      needs a development build and a Firebase project, and budget Android phones
      kill background apps, so it is not a guarantee. SMS always arrives and costs
      you about ₦3–4 per message — **nothing is charged to the vendor; receiving is
      free in Nigeria.** My advice: push for everything, plus one SMS for the single
      message where silence costs money — *"you have a paid order"*.
- [ ] **[P]** Firebase project and FCM credentials (an afternoon, mostly clicking).
- [ ] **[P]** If SMS: a Termii or Africa's Talking account, and start the sender-ID
      registration early — it takes days and needs business documents.
- [ ] **[C]** Token registration, the backend sender, and wiring it into the
      existing `notify()` so everything already fired also pushes.
- [ ] **[C]** Tell the customer when their order expires unpaid. Right now it
      silently becomes cancelled.

### 2d. Hosting
- [ ] **[D] Decide where.** Render's free tier would carry a pilot (no card, but it
      sleeps and takes ~60s to wake). Railway is better and costs a few dollars a
      month. **Not AWS** — no spending cap by default, and your Channels code would
      need rewriting for Lambda.
- [ ] **[C]** Photo storage that survives a deploy — Cloudinary (free tier is
      enough) or S3. **Required before any real vendor uploads**, because the
      container disk is wiped on every deploy.
- [ ] **[P]** Commit and push everything to GitHub. A week of changes are sitting
      uncommitted.
- [ ] **[C]** Check production settings, `ALLOWED_HOSTS`, CORS for the real domain.
- [ ] **[P]** Create the scheduled-task service. Config is already written in
      `backend/railway.cron.toml`. **Not optional** — without it an abandoned
      payment holds a vendor's stock until another shopper happens along.
- [ ] **[C]** Point the app at the deployed backend, and add the Paystack webhook
      now that there is a public address.

---

## M3 — Open to the public
*Target: after M2 and a handful of shops trading happily.*

- [ ] **[C]** Move `ai/` and `ml/` inside `backend/` so the AI features work when
      deployed; set `ANTHROPIC_API_KEY`.
- [ ] **[D] [P]** Terms of service and a privacy policy. Required by the Play Store
      and you are handling people's money and addresses. Not optional, not mine to
      write.
- [ ] **[P]** Google Play developer account (one-off fee) and a production build.
- [ ] **[C]** Vendor "confirm before payment" — you wanted this before real vendors:
      a shop confirms it has the goods before the customer is charged.
- [ ] **[C]** A dispute path. Today a refund is you clicking in the Paystack
      dashboard. Needs to be a recorded process with a reason.
- [ ] **[P]** A support route a customer can actually use — a phone number is fine
      to begin with, but it must exist.
- [ ] **[C]** Ratings surfaced in the app. `BusinessRating` already exists.

---

## M4 — Growth
Only once M3 is steady.

- [ ] **[C]** Product variants (colour, size) — written up in
      `FUTURE_FEATURES.md`. Trigger: your first fashion shop.
- [ ] **[C]** Search and browse worth using at a hundred shops: categories that
      work, filters, sorting by distance.
- [ ] **[C]** Make the category icons on Home do something. They are decorative
      today, and Petrus noticed that on day one.
- [ ] Transport/drivers, then restaurants — see `FUTURE_FEATURES.md`. Hotels and
      GG remain parked; land and rentals are out of this app.

---

## Housekeeping — whenever there's a dull hour
*None of this is visible to a user. All of it makes the next change easier.*

- [ ] **[C]** Delete dead code: old `api.py` files, `backend/management/`, the
      unused `realtime/` app, `config/settings.py`.
- [ ] **[C]** Remove numpy, pandas and scikit-learn from `requirements.txt` — they
      do nothing and slow every single build.
- [ ] **[C]** `STATICFILES_STORAGE` → `STORAGES` in `prod.py`.
- [ ] **[C]** Delete the old mobile service files that send wrong fields.
- [ ] **[C]** Clean up abandoned `pending` payment records — nothing ever does, so
      "pending payments" is not a list you can trust.

---

## The three decisions that block the most work

If you only answer three questions, answer these — each one unblocks a whole
milestone, and none of them is a coding question.

1. **How do vendors get paid, and what is your cut?** (blocks M2a)
2. **Who is allowed to open a shop, and who approves it?** (blocks M2b)
3. **Will you spend a few dollars a month on hosting, or accept a 60-second cold
   start on a free tier?** (blocks M2d)

---

## One honest note on order

The temptation is to build M2 now, because it is the interesting work and it is
all code. Resist it. M1 costs nothing, takes an afternoon, and can invalidate
large parts of M2 — if the first shop says she would rather use WhatsApp, the
answer is not to build a settlement ledger.

The software is roughly 80% of a shopping marketplace. The business is closer to
10%. The gap closes in a shop in Asaba, not in this editor.
