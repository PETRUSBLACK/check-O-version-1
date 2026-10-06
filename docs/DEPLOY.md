# Putting Check-O online, for free

**Why bother:** right now Check-O only works on your wifi, with your laptop
running. No vendor in Asaba can trade on that. This gets the backend onto the
internet so a shop owner can use Check-O from her own phone, on her own data,
whether or not your laptop is open.

**What it costs:** nothing. Three free accounts, no card.

**How long:** about 45 minutes the first time, most of it waiting for builds.

---

## The shape of it

```
  Shop owner's phone                    Free cron service
   (Expo Go / APK)                   every 5 minutes, GET
          │                                    │
          │  https                             │  https + X-Task-Token
          ▼                                    ▼
   ┌──────────────────────────────────────────────────┐
   │  Render — free web service (Docker, Daphne)       │
   │  checko-api.onrender.com                          │
   └───────────┬──────────────────────┬───────────────┘
               │                      │
     DATABASE_URL              CLOUDINARY_URL
               ▼                      ▼
     ┌──────────────────┐   ┌────────────────────┐
     │ Neon  Postgres   │   │ Cloudinary         │
     │ 1 GB, free       │   │ product photos     │
     └──────────────────┘   └────────────────────┘
```

Three decisions worth understanding before you click anything, because each one
is a trap you would otherwise walk into:

**Why not Render's own free Postgres?** It **expires 30 days after creation**.
Your data would disappear in a month. Neon's free plan does not expire.

**Why Cloudinary rather than `backend/media/`?** Render rebuilds the container on
every deploy and throws the old filesystem away. Product photos stored on disk
would vanish the next time you pushed a change — silently, with the database
still holding paths to files that no longer exist.

**Why a cron service instead of a second background worker?** Render's free tier
gives you 750 instance hours a month. A month is about 730 hours, so **one**
service can run continuously inside the allowance — but not two. And a free
service falls asleep after 15 minutes of no traffic and takes about a minute to
wake up, which means the first customer of the morning stares at a loading
screen. A free cron hitting `/api/internal/run-tasks/` every 5 minutes solves
both: the background tasks run, *and* the service never gets quiet long enough to
fall asleep.

---

## Step 1 — The database (Neon)

1. Go to **neon.com**, sign up with GitHub or email.
2. Create a project. Name it `checko`. Region: **Frankfurt (eu-central-1)** — the
   closest to Nigeria of what they offer.
3. On the project dashboard, find **Connection string** and copy it. It looks like:

   ```
   postgresql://neondb_owner:SOMEPASSWORD@ep-cool-name-123456.eu-central-1.aws.neon.tech/neondb?sslmode=require
   ```

4. Keep it somewhere for the next step. **Do not paste it into a chat, a commit,
   or a screenshot** — it is a username and password for your database.

Free plan: 1 GB of storage, which is tens of thousands of orders. The compute
sleeps after 5 minutes of quiet and wakes in under a second.

---

## Step 2 — Photo storage (Cloudinary)

1. Go to **cloudinary.com**, sign up for the free plan.
2. On the dashboard, find **API Environment variable**. It looks like:

   ```
   CLOUDINARY_URL=cloudinary://123456789012345:aBcDeFgHiJkLmNoPqRsTuVwXyZ@your-cloud-name
   ```

3. Copy the value **after** `CLOUDINARY_URL=`. Same warning: it contains a secret.

---

## Step 3 — Push the code to GitHub

Render deploys from a Git repository, so what is on your laptop has to be on
GitHub. If `smartmall` already has a GitHub remote, just push. If not, create an
empty **private** repository on GitHub and follow the instructions it gives you.

Check first that nothing secret is about to go up:

```bash
cd backend
git status
git check-ignore -v .env        # must print a line — that means .env is ignored
```

If `git check-ignore` prints nothing, **stop** and tell me — your Paystack secret
key is about to be committed.

---

## Step 4 — The backend (Render)

There is a `render.yaml` at the root of the repository, so Render can set most of
this up itself.

1. Go to **render.com**, sign up with GitHub.
2. **New → Blueprint**, pick the `smartmall` repository, Apply.
3. Render reads `render.yaml`, creates a service called `checko-api`, and asks you
   for the four values it will not invent:

   | Asks for | Paste |
   |---|---|
   | `DATABASE_URL` | the Neon connection string from step 1 |
   | `CLOUDINARY_URL` | the `cloudinary://...` value from step 2 |
   | `PAYSTACK_SECRET_KEY` | your `sk_test_...` key |
   | `PAYSTACK_PUBLIC_KEY` | your `pk_test_...` key |

   It generates `SECRET_KEY` and `TASK_RUNNER_TOKEN` itself.

4. Wait for the build. The first one takes 5–10 minutes — it is installing
   Python packages inside a Docker image. Watch the log.

The start command already runs `migrate` and `collectstatic` before Daphne, so
your tables are created on the first deploy with nothing to do by hand.

**About `dockerfilePath`** — settled by running it, on 2026-10-06. Render's docs
say the path is relative to the repo root. Its build host disagrees: with
`rootDir: backend`, the path is resolved **relative to rootDir**. Setting it to
`./backend/Dockerfile` makes the build look for `backend/backend/Dockerfile` and
die with:

```
error: invalid local: resolve : lstat /opt/render/project/src/backend/backend: no such file or directory
```

`render.yaml` now says `./Dockerfile`, which is correct. If you ever see that
error again, this is why.

### If you would rather click than use the Blueprint

**New → Web Service** → pick the repo → Language **Docker** → Root Directory
`backend` → Instance Type **Free** → Region **Frankfurt** → then add every
environment variable from `render.yaml` by hand, generating your own long random
strings for `SECRET_KEY` and `TASK_RUNNER_TOKEN`.

### Check it worked

Open `https://checko-api.onrender.com/api/health/` in a browser. You want:

```json
{"status": "ok", "service": "smartmall-backend"}
```

Then make yourself an admin account. Render's **Shell** tab (free tier includes
it):

```bash
python manage.py createsuperuser
```

and log in at `https://checko-api.onrender.com/admin/`.

---

## Step 5 — The scheduler (a free cron)

This is the step people skip, and the symptom is subtle: everything looks fine,
but an abandoned payment holds a vendor's stock forever, nobody is reminded about
anything, and no shop is told its stock is low.

1. In Render, open `checko-api` → **Environment** → copy the generated value of
   **`TASK_RUNNER_TOKEN`**.
2. Go to **cron-job.org** (free, no card) and sign up.
3. Create a cron job:

   | Field | Value |
   |---|---|
   | Title | `Check-O tasks` |
   | URL | `https://checko-api.onrender.com/api/internal/run-tasks/` |
   | Schedule | **Every 5 minutes** |

4. Open **Advanced / Headers** and add one header:

   ```
   X-Task-Token: <the TASK_RUNNER_TOKEN value>
   ```

5. Save, then use **Test run**. You want `200` and a body like:

   ```json
   {"status": "ok", "ran": ["frequent"], "failed": {}}
   ```

   A **401** means the header is wrong or missing. A **503** means
   `TASK_RUNNER_TOKEN` is not set on Render.

This one cron job is doing two jobs. Every 5 minutes it runs the background tasks
**and** it is traffic, which is what stops Render putting the service to sleep.

---

## Step 6 — Point the app at it

In `mobile/.env`:

```
EXPO_PUBLIC_API_URL=https://checko-api.onrender.com/api
```

Then restart Expo so the new value is picked up — these are baked into the bundle
at build time, not read at runtime:

```bash
cd mobile
npx expo start --clear
```

**Remember this trap:** `EXPO_PUBLIC_API_URL` always wins. While that line is in
`mobile/.env`, the app talks to Render even when your laptop's backend is running
and you are editing it. Comment it out when you go back to working locally.

Now sign up as a vendor, set the shop up, add a product with a photo, and buy it
from another phone. The photo should come back from a `res.cloudinary.com` URL,
not from your laptop.

---

## What you have to watch

| Thing | Free limit | What happens when you hit it |
|---|---|---|
| Render instance hours | 750/month | The service stops until next month. One service, pinged, fits. Do **not** add a second. |
| Neon storage | 1 GB | Writes start failing. Tens of thousands of orders before this matters. |
| Neon compute | 100 CU-hours/month | Compute suspends until next month. Sleeping costs nothing, so this is hard to hit. |
| Cloudinary | ~25 GB bandwidth/month | Images stop loading. Hundreds of product photos is fine. |

One honest warning about the free tier: it is good enough to put Check-O in a real
shop owner's hands, which is the whole point. It is not good enough to launch to
the public. When you have a shop that depends on it, Render's cheapest paid plan
removes the sleeping and the hour limit, and that is the first money worth
spending on this project.

---

## When something is wrong

| Symptom | Almost always |
|---|---|
| `400 Bad Request` on every page | `ALLOWED_HOSTS`. It picks up `RENDER_EXTERNAL_HOSTNAME` automatically, so this means you are reaching it on a different domain. |
| Admin login takes the password then refuses the form | `CSRF_TRUSTED_ORIGINS`. Same cause as above. |
| `server closed the connection unexpectedly`, now and then | Neon's compute went to sleep. `conn_health_checks=True` in `base.py` is the fix and is already set — if you see this, check it is still there. |
| Photos upload, then 404 later | `CLOUDINARY_URL` is not set, so they went to the container's disk and the next deploy wiped them. The startup log says so in as many words. |
| Unpaid orders never cancel | Step 5. Check cron-job.org's history for 200s. |
| First request of the day takes a minute | The service slept. Your cron is not running. Step 5 again. |
| Build fails on `collectstatic` | A static file referencing something that does not exist. The log names the file. |
| `invalid local: resolve : lstat .../backend/backend` | `dockerfilePath` — see the note in step 4. It is relative to `rootDir`, not the repo root. |

---

## Sources

The free-tier details here were checked on 2026-10-02 rather than remembered:

- [Is Render Free? Free Tier Limits, Sleep, and the 30-Day DB](https://justinmckelvey.com/blog/is-render-free)
- [Neon free-plan limits](https://neon.com/faqs/managed-postgres-databases-free-tier)
- [Render Blueprint YAML reference](https://render.com/docs/blueprint-spec)

Free tiers change. If a number above does not match what the dashboard tells you,
believe the dashboard.
