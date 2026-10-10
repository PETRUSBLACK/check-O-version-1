# What using Check-O actually feels like

Findings from real use, newest first. Not a wish list — every item here was hit
by someone trying to do a normal thing, and it stopped them or made them pause.

A feature that is written, tested and deployed can still be unusable. This file
is the record of the difference.

---

## 2026-10-10, later — what the inbox revealed

### 8. Nobody ever tells the shop — **fixed 2026-10-10**

Found while debugging #7, which is the point of building an inbox: once
messages can be seen, the missing ones become visible.

Every notification helper in Check-O was addressed to `order.customer`. Order
placed, payment confirmed, status changed, shipment moved, pickup due, pickup
expired, refund due — seven of them, all to the shopper. **Not one reached the
person who has to pack the bag.**

A trader whose phone stays silent when money arrives has to keep opening
Check-O to check whether anything has happened, which is precisely the
behaviour an order notification exists to make unnecessary. Check-O would have
been quieter than a missed call.

Petrus's reply when I raised it was the whole argument in six words: *"why
should a shop owner not receive notifications?"* There is no reason. It was
never a decision, it was an omission — the shop side of Check-O was built
outwards from the shopper side, and until that morning nothing in the app could
display a notification at all, so there was nothing to notice missing.

**Fixed:** the shop is now told when an order is **paid**, and when somebody
else cancels one.

Two judgements worth keeping:

- **Paid, not placed.** An unpaid order is a thirty-minute hold that may simply
  lapse. Sending a trader to pack something that might evaporate teaches her to
  ignore Check-O, which costs more than the message is worth. Payment is the
  first moment the work is real.
- **Not her own cancellations.** A vendor who cancels an order does not need a
  message announcing what she just did.

Nine tests, in the shape of the gap: for every message, who gets it — including
that the shopper did not lose anything, that one payment does not announce
itself twice, and that an order with no shop attached still gets paid for.

### 9. Three fixes for a bug that was in the data — **the morning's real lesson**

Tapping a notification did nothing. I shipped three fixes without once asking
the device what was happening: a plain push, then a dismiss-then-navigate, then
a replace. All three were wrong, and Petrus tested every one of them on his own
phone, reloading Expo each time.

The fourth attempt was not a fix. It was four lines that made the screen say
what the tap had just done. The answer came back in one tap: **no destination.**

His two notifications were written at 4:38 and 4:42 that morning. The columns
that say what a notification is about were added by a migration at 5:03. Those
rows got the defaults — an empty event type, an empty payload — so the app
correctly refused to invent somewhere to go. The navigation code had been right
the whole time, on data a quarter of an hour too old.

**The lesson is the same one as #6, which was two days ago.** There, 382 tests
passed because every one of them went through the ORM and none through the
view. Here, three fixes failed because I reasoned about the code from a sandbox
while the only evidence was on a phone in Asaba. Both are the same mistake:
*believing a model of the system instead of asking the system.*

Instrument first, then fix. It costs one round trip and saves four.

Petrus took Shop O all the way: signed up, set the shop up, added a product with
a photo, submitted it, approved it in the admin. **Shop O is the first shop ever
to go live on Check-O.** Two things broke on the way, and both were mine.

### 6. A new shop could never add a product — **fixed 2026-10-10**

He reported it in four words: *"the add product is not working"*. The cause was a
deadlock with no way out:

- `missing_before_review()` refuses to let a shop be submitted until it has at
  least one product
- a shop cannot be approved until it has been submitted
- and `ProductViewSet.create()` refused any shop that was not already **approved**

So every vendor who ever signed up was stuck permanently. The app told her she
needed a product; the server told her she needed approval. There was no order in
which those three could be satisfied.

Mine, added on 2 October, shipped to production on the 6th, found by a human on
the 10th. The service layer's own docstring says the opposite in plain English —
*"The waiting is never dead time. A draft shop can add products, photos and set
prices — all of it"* — and the view contradicted it for eight days.

**Fixed:** product creation now refuses only `SUSPENDED`. Draft, pending and
rejected shops can all stock their shelves.

**Why no test caught it, which is the part worth keeping:** every existing
product test built its products with `Product.objects.create(...)`, straight
through the ORM. The ORM never runs a view's permission check. 382 passing tests
and not one of them had ever asked the server to create a product the way the app
does. `backend/apps/products/tests/test_new_shop_can_list.py` now does, nine
times over. **When a rule lives in a view, only a request can prove it.**

### 7. The app has no inbox — **built 2026-10-10, nobody has used it yet**

He approved Shop O and said: *"I did not receive a notification saying the shop
is open, but my shop now say open on check O."*

He was right, and it is worse than a missing screen. Grep the whole mobile
codebase for `notification` and it returns nothing. No service file, no bell, no
badge, no screen. There are ten service files in `mobile/src/services/` and none
of them is for notifications.

The backend is working perfectly, which is how this stayed hidden. His admin page
shows both rows sitting in Neon:

| Notification | To | When | Read at |
|---|---|---|---|
| Shop O is open on Check-O | onukwupetrusoge@gmail.com | 10 Oct, 4:42 a.m. | — |
| A shop is waiting for review | admin@gmail.com | 10 Oct, 4:38 a.m. | — |

Both unread, because nothing in the world can read them. Every notification
Check-O has created since September — order placed, order accepted, payment
confirmed, stock running low, shop approved, shop rejected — has been written to
the database and seen by nobody.

On 2 October I built the low-stock warning and wrote twelve tests for how
restrained it was: that it fires once and not on every sale, that it respects the
threshold, that it does not nag. Twelve tests about the manners of a message that
had nowhere to arrive.

**What it should do:** a bell on the header with an unread count, a screen listing
them newest first, tapping one marks it read and goes to the thing it is about
(the order, the shop, the product). Nothing clever. The hard part is already
built — there is a `Notification` model, it is being written to correctly, and it
has an `is_read` field waiting to be used.

**Not push notifications.** That is a separate, bigger job needing Expo's push
service and device tokens. An inbox you have to open is most of the value and a
fraction of the work.

**Built the same day.** A bell on the Home header of both sides of the app with
an unread count, and `/notifications` — newest first, unread ones marked, pull to
refresh, *mark all as read*, and tapping one marks it read and opens the order or
shop it is about.

That last part needed a change to the model. `notify()` has always taken an
`event_type` and a `payload` of ids, and always threw both away: they went out
over the WebSocket and the database row kept only the words. So every message
ever stored was unactionable by design. Both are now columns
(`notifications/0003`), which made all eleven existing call sites useful at once
without touching one of them.

Sixteen new tests, through the API. Two of them are the ones that matter — that
one person's inbox never shows, and never accepts a mark on, another person's
messages.

Also deleted `apps/notifications/api.py`: a second copy of the viewset that
nothing had imported since the app was split into a `views/` package. A dead
duplicate of a file you are about to edit is exactly how finding #6 stayed
hidden for eight days.

**Per the rule at the bottom of this file, this is not done.** The code is
written, 398 tests pass, and no human being has opened the screen. It goes live
on the next push. Petrus has two unread notifications waiting in Neon — "Shop O
is open on Check-O" and "A shop is waiting for review" — and they are the first
thing it will have to render.

---

## 2026-10-09 — Petrus's first run through the live app

The backend went live on 6 October. On the 9th Petrus set a shop up on his own
phone against the live server, the way a trader in Asaba would. These came out of
that half hour. He found all of them; none were visible from reading the code.

### 1. The sign-up screen forgets why you came — **open**

Tapping **"Sell on Check-O — open your shop"** on the sign-in page lands on a
screen headed **"Create your account"**, offering a choice between *I want to
buy* and *I want to sell*.

You just said you wanted to sell. The next screen offers you the opposite, and
its heading says nothing about shops. The intent is carried in the code (the link
passes `role=vendor`, so *I want to sell* starts selected) but nothing on screen
acknowledges it.

**What it should do:** arriving from that link, the heading reads *"Open your
shop on Check-O"*, and the buy option shrinks to a quiet line underneath —
*"Actually, I just want to buy"*. Same screen, but it remembers why you are there.

Small, and it only affects people who have already decided to sell. Lowest
priority of everything here.

### 2. The shop's address is asked for twice — **fixed 2026-10-09**

Shop setup asked for a typed address *and* a GPS pin, and only the pin counted
toward approval. So a vendor typed where her shop was, saved, and was told the
app still did not know where her shop was.

Worse, the only way to give the pin was a button reading *"I'm standing in my
shop — use my location"*. A trader is far more likely to do this at home in the
evening than behind her counter at midday — and tapping it at home pins her shop
to her house, silently, with nobody finding out until a customer knocks on the
wrong door.

**Fixed:** two buttons now answer the same question. **Find my address** geocodes
what she typed; **Use my location** reads the phone's position. Either satisfies
the requirement, and the screen then shows which place it chose so a wrong guess
is visible. The form also refuses to save without a pin, so she learns on that
screen instead of two screens later.

The requirement itself stays — without coordinates a shop can never appear in
"shops near you", so approving one would mean approving a shop nobody can find.

**Still to watch:** `Location.geocodeAsync` uses the phone's own geocoder, which
is good on named roads and unreliable on unnamed ones. If it does badly on real
Asaba addresses, this needs rethinking — possibly a map the vendor drags a pin on.

### 3. A shopper must register before seeing anything — **open, biggest**

The shopper tabs sit behind a sign-in guard. Open Check-O for the first time and
the only thing on offer is sign in or register.

Someone hears about Check-O from a friend, opens it to see whether anyone nearby
sells a phone charger, and is asked to create an account before seeing a single
shop. Most will close it and not come back. Nothing has been offered yet, so
there is no reason to pay the price.

**What it should do:** browse and search freely. Sign-in moves to **Add to cart**
— by then she has seen the value and asking is reasonable.

**Cheaper than it looks:** the API already permits this. Both
`BusinessViewSet` and the products viewset return `AllowAny` for list and
retrieve. The only thing blocking anonymous browsing is the guard in the app.

### 4. The shopper's location is unreadable and unchangeable — **open**

Home shows:

> Delivering to **5PP7+JQQ, Asaba**

That is a Google plus code. It means nothing to a human. It is also not tappable,
so if GPS is wrong — common in Asaba — or she is shopping for her mother across
town, she has no way to correct it. And it is recalculated from scratch every
time the app opens.

**What it should do:** a place name in words (*"Shops near: Okpanam Road"*),
tappable to pick another area, remembered for the session.

### 5. The delivery address is forgotten between orders — **open**

Checkout prefills the customer's *name* from her account and nothing else. Phone
and address start blank on every single order. Buy rice on Monday and again on
Thursday, and type your full address twice.

This is worst exactly where it hurts most: the moment someone is closest to
paying is the moment the app asks them to do the most typing.

**What it should do:** prefill from the last order — every order already stores
`recipient_name`, `phone` and `address`, so there is no new table and no
migration. Keep it editable, and add a **"Deliver to where I am now"** button.

**Note on a question Petrus raised:** remembering must never mean locking in.
Check-O has two different locations — *where am I now* (which shops to show) and
*where should this go* (delivery). They are often different: browsing at the
market, delivering home; buying for a relative across town. The first follows the
phone, the second is remembered but always one tap from being changed.

Named addresses (*Home*, *Shop*, *Mum's*) are the obvious next step, but that is a
guess about behaviour nobody has shown yet. Not until a real shopper asks.

---

## What to build next

**Done first, on the day it was found: 7**, because Check-O now has a real shop
on it. A vendor who is not told an order arrived is worse than a shopper who has
to register — the shopper is a person Check-O has not got yet, the vendor is one
it already has.

Next: 3, 4 and 5, which are one disease: **the app does not hold on to what it
has been told**, and asks for commitment before giving anything. They share the
same code and should be one piece of work.

That bundle is the difference between an app you must commit to and one you can
simply look at. For a shopper who heard about Check-O from a friend, it is
everything.

Then 1, which only affects people already determined to sell.

Deliberately **not** next: the AI assistant, named addresses, and anything else
that is a guess about behaviour no real user has demonstrated. The Anthropic API
bills per message, and Check-O currently costs ₦0 a month to run. That is worth
protecting until there is evidence shoppers cannot find things without it.

---

## How to read the ticks elsewhere

A tick in `ROADMAP.md` means *the code is written and tested*. It does not mean
anyone has used it. Vendor sign-up was ticked complete on 2 October; the first
human to open that screen was Petrus on the 9th, and he found two problems in ten
minutes.

Every feature in Check-O is a guess about what a trader in Asaba needs. Until a
real shop has traded for a week, they are all still guesses — well-built ones.
