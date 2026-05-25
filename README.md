# SmartMall

> **Location-aware multi-vendor marketplace for Nigeria and Africa.**
> Find products in physical shops near you, compare prices, order online, track delivery.

---

## What Is SmartMall?

SmartMall is a platform where customers search for a product and instantly see which physical shops near them have it in stock — with real prices, shop ratings, and distance. They can order online and choose between home delivery or picking it up from the shop.

Think of it as **Google Maps meets Jumia**, built specifically for the Nigerian market and African commerce.

---

## The Problem It Solves

Right now in Nigeria, if someone in Asaba wants to buy a specific phone model, they:
1. Ask on WhatsApp groups
2. Physically walk to the market
3. Check shop by shop manually
4. Negotiate, buy, carry it home

SmartMall replaces that entire process:
1. Open the app
2. Search "Tecno Camon 30"
3. See 12 shops within 3km with prices and ratings
4. Order from the best option, get it delivered or pick it up

---

## Who It's For

**Customers:** Anyone who wants to find and buy products from local shops near them without leaving their house.

**Vendors:** Physical shop owners — market traders, boutiques, supermarkets, electronics shops — who want to reach more customers online without paying Jumia's commissions.

---

## What Makes It Unique

- **Nigeria-first** — Paystack and Flutterwave built natively, Naira prices, Nigerian market context
- **Location-aware** — shows shops near you sorted by distance, not just any shop in the country
- **Physical shop discovery** — connects customers to real shops, not warehouses
- **AI-powered** — customers talk to an AI assistant that searches real shops and recommends products in plain language including Nigerian Pidgin
- **Vendor owned** — vendors control their shop, prices, and stock completely
- **Multi-channel stock** — large businesses (supermarkets, chains) can allocate separate stock for SmartMall without affecting their physical store inventory

---

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Django 5, Django REST Framework |
| Realtime | Django Channels, WebSocket, Redis |
| Database | PostgreSQL |
| Auth | JWT (SimpleJWT) |
| Payments | Paystack, Flutterwave, Stripe |
| AI Assistant | Claude API (Anthropic) |
| ML | scikit-learn, pandas, numpy |
| API Docs | Swagger / ReDoc |
| Containerisation | Docker Compose |
| Deployment | Railway |

---

## Project Phases

| Phase | Description | Status |
|---|---|---|
| Phase 1 | Core marketplace — auth, vendors, products | ✅ Complete |
| Phase 2 | Commerce engine — cart, orders, payments | ✅ Complete |
| Phase 3 | Delivery, realtime, tracking, location, ratings, pickup | ✅ Complete |
| Phase 4 | Monetisation — subscriptions, ads, promotions | ✅ Complete |
| Phase 5 | AI + ML — customer assistant, smart search, demand forecast | ✅ Complete |
| Phase 6 | Frontend — React Native customer + vendor apps | 🔄 Next |

---

## Key Features

### For Customers
- Search products by name — see all nearby shops with prices and ratings
- AI shopping assistant — find products in plain English or Pidgin
- Compare prices across multiple shops
- Cart, checkout, and secure payment (Paystack / Flutterwave / Stripe)
- Home delivery or pick up in store
- Real-time order tracking via WebSocket
- Pickup code system — collect order at shop with a unique code
- Personalised product recommendations

### For Vendors
- Register shop with physical location
- List products with stock, prices, and photos
- Receive and manage orders from one dashboard
- Vendor AI assistant — ask about sales, stock, demand forecasts
- Channel allocation — reserve separate stock for SmartMall vs physical store
- Subscription plans (Free, Starter, Growth, Pro)
- Featured listings and discount promotions
- Delivery management (vendor riders or logistics partners)
- Real-time notifications on every order event

### For the Platform
- Multi-vendor marketplace — thousands of shops in one place
- Vendor verification workflow — businesses reviewed before going live
- Subscription monetisation — vendors pay for premium features
- Promotions engine — vendors pay to feature their products
- Analytics — track impressions, clicks, conversions
- Background tasks — auto-expire pickup orders, auto-renew subscriptions

---

## Architecture

SmartMall follows a strict **service-layer architecture**:

```
Views → Services → Models
```

- Views only handle requests and responses
- All business logic lives in service layer
- Models are pure data — no workflow logic

### Project Structure

```
smartmall/
├── backend/
│   ├── apps/
│   │   ├── users/          — auth, JWT, roles
│   │   ├── businesses/     — vendor registration, location, ratings
│   │   ├── products/       — catalog, channel allocation
│   │   ├── cart/           — cart and checkout
│   │   ├── orders/         — order lifecycle, pickup flow
│   │   ├── payments/       — Paystack, Flutterwave, Stripe + webhooks
│   │   ├── delivery/       — shipments, tracking, providers
│   │   ├── notifications/  — realtime + DB notifications
│   │   ├── subscriptions/  — vendor subscription plans
│   │   ├── ads/            — promotions, featured listings
│   │   ├── analytics/      — event tracking
│   │   └── ai_assistant/   — AI chat, smart search, demand forecast
│   ├── core/
│   │   ├── base_models.py
│   │   ├── constants/
│   │   ├── exceptions/
│   │   ├── middleware/
│   │   ├── permissions/
│   │   ├── utils/
│   │   └── validators/
│   ├── realtime/
│   │   ├── consumers/      — WebSocket consumers
│   │   ├── events/         — event type constants
│   │   └── websocket_utils.py
│   └── config/
│       ├── settings/
│       │   ├── base.py
│       │   ├── dev.py
│       │   └── prod.py
│       ├── urls.py
│       ├── asgi.py
│       └── wsgi.py
├── ai/
│   ├── assistant/          — customer + vendor AI assistants
│   └── tools/              — database query tools for AI
├── ml/
│   ├── demand/             — demand prediction model
│   └── ranking/            — smart search ranking
├── mobile/                 — React Native app (Phase 6)
└── docs/
```

---

## API Endpoints (Summary)

| Category | Endpoints |
|---|---|
| Auth | Register, login, token refresh, logout, password reset |
| Businesses | CRUD, verify, location, nearby search, ratings |
| Products | CRUD, channel allocation |
| Cart | Add, update, remove, checkout |
| Orders | List, detail, status transitions, pickup flow |
| Payments | Initiate, webhooks (Paystack, Flutterwave, Stripe) |
| Delivery | Shipments, tracking, provider management |
| Subscriptions | Plans, subscribe, cancel, renew |
| Ads | Promotions, featured products, discounts |
| AI | Customer chat, vendor chat, smart search, demand forecast |
| Notifications | List, mark read |
| Analytics | Event tracking |

Full interactive documentation at: `/api/docs/` (Swagger UI)

---

## AI + ML Features

### Customer AI Shopping Assistant
Conversational AI powered by Claude (Anthropic). Customers chat naturally:

> *"I wan buy phone under 50k near me"*
> → AI searches real database, finds nearby shops, returns accurate prices and ratings

Understands Nigerian English and Pidgin. Never makes up products — only returns real data.

### Vendor AI Business Assistant
Helps vendors manage their shop through conversation:
- Sales summary and revenue breakdown
- Low stock alerts
- Pending order management
- Demand forecasts with restock recommendations

### Smart Search (ML-Ranked)
Multi-signal search ranking combining:
- Text relevance
- Distance from customer
- Shop rating
- Stock availability
- Promotion boost weight

### Demand Forecast
Analyses 90 days of order history. Accounts for Nigerian seasonal patterns — Sallah, Christmas, back-to-school, rainy season. Predicts days until stockout per product.

---

## Channel Allocation (Multi-Channel Stock)

Designed for supermarkets and large businesses that sell across multiple channels:

```
Ebeano Supermarket — Total stock: 100 bags of rice
    Physical store allocation: 80 bags
    SmartMall allocation:      20 bags  ← set in SmartMall dashboard

When a SmartMall customer orders 5 bags:
    SmartMall allocation: 15 bags  ← reduced
    Physical store stock: 80 bags  ← untouched
```

Physical store sales never affect SmartMall availability. No overselling. No conflict between channels.

---

## Payment Gateways

| Provider | Use Case | Webhook |
|---|---|---|
| Paystack | Nigerian cards, bank transfer, USSD | ✅ Implemented |
| Flutterwave | West Africa, mobile money | ✅ Implemented |
| Stripe | International cards | ✅ Implemented |

All webhooks verify cryptographic signatures before processing — no fake payment confirmations possible.

---

## WebSocket Events

Real-time notifications delivered via WebSocket:

| Event | Triggered When |
|---|---|
| `order.placed` | Customer places order |
| `payment.confirmed` | Payment webhook received |
| `order.status_changed` | Order moves to new status |
| `shipment.updated` | Shipment status changes |
| `order.pickup_reminder` | 24hr / 6hr / 1hr before pickup deadline |
| `order.pickup_expired` | 48hr pickup window expires |
| `subscription.activated` | Vendor subscription goes live |

---

## Quick Start

```bash
# Clone and configure
git clone https://github.com/your-username/smartmall.git
cd smartmall
cp .env.example .env   # fill in your values

# Run with Docker
docker compose up --build

# Run migrations
docker compose exec backend python manage.py migrate

# Create admin account
docker compose exec backend python manage.py createsuperuser

# Access
API:     http://localhost:8000/api/
Swagger: http://localhost:8000/api/docs/
Admin:   http://localhost:8000/admin/
```

---

## Environment Variables

```env
SECRET_KEY=your-secret-key
DATABASE_URL=postgres://user:pass@localhost:5432/smartmall
REDIS_URL=redis://localhost:6379/0
FRONTEND_ORIGIN=http://localhost:3000

# Payment Gateways
PAYSTACK_SECRET_KEY=sk_test_xxx
FLUTTERWAVE_SECRET_KEY=FLWSECK_TEST-xxx
FLUTTERWAVE_WEBHOOK_SECRET=your-webhook-secret
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx

# AI Assistant
ANTHROPIC_API_KEY=sk-ant-xxx
```

---

## Running Tests

```bash
cd backend
python manage.py test
```

Test coverage includes all 5 phases — auth, businesses, products, cart, orders, payments, delivery, location, ratings, pickup flow, subscriptions, promotions, AI assistant, smart search, demand forecast, and channel allocation.

---

## Deployment (Railway)

The project is configured for Railway deployment:

```bash
# Push to GitHub — Railway auto-deploys
git push origin main

# Live URL
https://smartmall-production.up.railway.app/api/health/
```

---

## Background Tasks

Run scheduled tasks via management command:

```bash
# Run all hourly tasks (pickup expiry, reminders, promotion cleanup)
python manage.py run_tasks --hourly

# Run all daily tasks (subscription renewal, cleanup)
python manage.py run_tasks --daily
```

---

## 🚀 Go-To-Market — Asaba, Delta State

### The Vision
SmartMall starts in Asaba — the commercial capital of Delta State, sitting on the
Asaba/Onitsha axis, one of the busiest trade corridors in Nigeria.

### Target Markets in Asaba

| Market | Products | Priority |
|---|---|---|
| Ogbeogonogo Market | Everything | 🔴 First |
| Cable Point Market | Phones, electronics | 🔴 First |
| Nnebisi Road | Fashion, boutiques | 🟡 Second |
| Asaba Main Market | General goods | 🟡 Second |

**Next city after Asaba:** Onitsha (20 minutes away)

### Zero Budget Launch Plan

| Week | Goal |
|---|---|
| Week 1 | Deploy free on Railway, create social media pages |
| Week 2 | First 5 vendors (personal contacts) |
| Week 3 | First 20 test customers (WhatsApp groups) |
| Week 4 | Fix issues, validate, prepare for live payments |

### The Vendor Pitch

> *"SmartMall helps customers in Asaba find your shop online. When someone searches
> for what you sell, your shop appears with your price. They can order and pick up
> or get it delivered. I want to list your shop for free — it takes 20 minutes."*

### Funding Opportunities

| Programme | Amount | When |
|---|---|---|
| Tony Elumelu Foundation | $5,000 USD | Apply every January |
| NIRSAL MFB (CBN) | ₦500,000–₦3M | Rolling |
| YouWIN Connect | Up to ₦10M | Check youwin.gov.ng |
| Google for Startups Africa | Cloud credits + mentorship | Rolling |
| Delta State Innovation Hub | Mentorship + support | Asaba — contact directly |

### Legal Steps (In Order, As Funds Allow)

| Step | When | Cost |
|---|---|---|
| Paystack individual account | Before first transaction | Free |
| Domain name | First revenue | ₦5,000 |
| CAC registration | First paying customer | ₦50,000–100,000 |
| TIN (FIRS) | After CAC | Free |
| Corporate bank account | After CAC | Free |
| Vendor agreement (lawyer) | Before 20 vendors | ₦50,000–150,000 |
| NDPC data protection | Before 100 users | Varies |
| Trademark | At ₦500,000 revenue | ₦25,000–50,000 |

### Realistic Timeline

| Month | Goal |
|---|---|
| 1 | 5 vendors, 20 test users, backend live |
| 2 | 15 vendors, first real transactions |
| 3 | 30 vendors, ₦50,000–100,000 GMV |
| 4 | Apply Tony Elumelu Foundation |
| 5 | Register CAC, go fully professional |
| 6 | Expand to Onitsha |
| 12 | Go national |

---

## What's Next

1. ✅ Backend — complete
2. 🔄 Deploy to Railway — in progress
3. ⬜ React Native customer app
4. ⬜ React Native vendor app
5. ⬜ Launch in Asaba
6. ⬜ Expand to Onitsha and beyond

---

## Important Links

| Resource | URL |
|---|---|
| CAC Registration | cac.gov.ng |
| FIRS (TIN) | firs.gov.ng |
| NDPC (Data Protection) | ndpc.gov.ng |
| Paystack | paystack.com/ng |
| Flutterwave | flutterwave.com |
| Anthropic (AI) | console.anthropic.com |
| Tony Elumelu Foundation | tonyelumelufoundation.org |
| Google for Startups Africa | startup.google.com/intl/africa |
