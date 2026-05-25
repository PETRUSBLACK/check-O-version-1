# SmartMall Project Context

Last updated: 2026-05-06 (Phase 2 identity & access — completed)

## Project Goal
Build a scalable smart commerce ecosystem combining:
- Multi-vendor marketplace
- Payments
- Delivery/logistics
- Realtime updates
- AI assistant layer
- ML recommendation/forecasting layer

## Architecture Direction
- Backend: Django + DRF + Channels (domain-driven app separation)
- Business logic: service modules, not views
- Mobile: React Native with feature-based structure
- Integrations: adapter-based payment/logistics/notification providers
- AI: calls backend tools/services (no duplicated domain logic)
- ML: training + serving API layer

## Phase status
- **Phase 1 (Foundation & architecture):** complete
- **Phase 2 (Identity & access):** complete for current scope:
  - Email-only users with **`UserManager`** (`create_user` / `create_superuser` by email)
  - JWT + optional refresh token blacklist (logout)
  - Password change, password reset (uid/token), throttled register/login/reset
  - Object-level checks on products, promotions, subscriptions, shipments
  - Vendors see orders that include their products; shipment `set_status` uses `get_object()`
- **Phase 3+:** catalog scaling, integrations, mobile app, ML/AI, hard CI

## Auth API (`/api/auth/…`)
| Method | Path | Notes |
|--------|------|--------|
| POST | `/api/auth/register/` | Throttled; optional `vendor_business` for vendors |
| POST | `/api/auth/token/` | Throttled JWT obtain |
| POST | `/api/auth/token/refresh/` | Throttled |
| GET | `/api/auth/me/` | Current user |
| POST | `/api/auth/password/change/` | `old_password`, `new_password` |
| POST | `/api/auth/password/reset/` | Request email; same response always |
| POST | `/api/auth/password/reset/confirm/` | `uid`, `token`, `new_password` |
| POST | `/api/auth/logout/` | Body `refresh` → blacklist |

## Vendor verification (businesses)
- Draft → submit-for-review → pending → approve/reject → products allowed when **approved**
- See earlier business endpoints in `apps.businesses`

## Environment (email / reset link)
- `EMAIL_BACKEND`, `DEFAULT_FROM_EMAIL`
- `FRONTEND_ORIGIN`, `PASSWORD_RESET_FRONTEND_PATH` (reset email link)

## Tests
- `python manage.py test apps.users.tests`

## Verification
- `python manage.py check`
- Apply migrations (includes `token_blacklist`)

## Resume prompt
1. Read this file
2. Run `python manage.py check` in `backend/`
3. Continue Phase 3 or integration work from product roadmap
