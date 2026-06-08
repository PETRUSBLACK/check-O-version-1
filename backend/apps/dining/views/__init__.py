apps/dining/
├── __init__.py          ← empty
├── apps.py
├── models.py
├── serializers.py
├── admin.py
├── services/
│   ├── __init__.py      ← empty
│   ├── menu.py
│   └── reservation.py
├── views/
│   ├── __init__.py      ← has the imports (this file)
│   ├── menu_views.py
│   └── reservation_views.py
└── migrations/
    ├── __init__.py      ← empty
    └── 0001_initial.py