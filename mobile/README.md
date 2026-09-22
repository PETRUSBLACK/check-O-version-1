# Check-O mobile app

Expo (SDK 57) + Expo Router + TypeScript. Opens in the **Expo Go** app on your phone.

## Run it on your phone

1. Install **Expo Go** from the Play Store.
2. Start the backend so your phone can reach it (from `backend/`):
   ```
   python manage.py runserver 0.0.0.0:8000
   ```
3. Find your laptop's Wi-Fi IP (Windows: `ipconfig` → "IPv4 Address", e.g. `192.168.1.23`).
4. In this `mobile/` folder, copy `.env.example` to `.env` and set:
   ```
   EXPO_PUBLIC_API_URL=http://192.168.1.23:8000/api
   ```
5. Install and start:
   ```
   npm install
   npx expo start
   ```
6. Scan the QR code with Expo Go. Phone and laptop must be on the same Wi-Fi.

If the phone can't connect, allow Python through Windows Firewall (private networks),
or run `npx expo start --tunnel`.

## Structure

```
src/
  app/               screens (Expo Router — every file is a route)
    _layout.tsx      fonts, providers, signed-in / signed-out routing
    sign-in.tsx  register.tsx  forgot-password.tsx
    (tabs)/          Home, Orders, Cart, Account
    shop/[id].tsx    shop page
    search.tsx       product search
  components/        shared UI (buttons, fields, shop card, categories)
  config/api.ts      API client (JWT, token refresh, error messages)
  services/          one file per backend area
  store/auth.ts      signed-in user (zustand)
  hooks/             location, status bar
  theme.ts           colours and fonts from the Check-O style guide
```

## Checks

```
npx tsc --noEmit
```
