# What using Check-O actually feels like

Findings from real use, newest first. Not a wish list — every item here was hit
by someone trying to do a normal thing, and it stopped them or made them pause.

A feature that is written, tested and deployed can still be unusable. This file
is the record of the difference.

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

3, 4 and 5 are one disease: **the app does not hold on to what it has been
told**, and asks for commitment before giving anything. They share the same code
and should be one piece of work.

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
