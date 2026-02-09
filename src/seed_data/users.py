"""
Seed data for users.
14 users across all organizations.  Password for all: "portiq123".
"""

PASSWORD_HASH = "$2b$12$LJ3m4ys3Lk0TSwHiWbOJNeDwvCHmPmVMq.qlwPgTyDz7RuBy3.4xq"

USERS = [
    # ── Platform ────────────────────────────────────────────────────────────
    {
        "email": "admin@portiq.in",
        "first_name": "Platform",
        "last_name": "Admin",
        "org_slug": "portiq",
        "role": "OWNER",
        "phone": "+919820000001",
    },
    {
        "email": "ops@portiq.in",
        "first_name": "Platform",
        "last_name": "Ops",
        "org_slug": "portiq",
        "role": "ADMIN",
        "phone": "+919820000002",
    },
    # ── Great Eastern Shipping (Buyer) ──────────────────────────────────────
    {
        "email": "rajesh@greateastern.com",
        "first_name": "Rajesh",
        "last_name": "Sharma",
        "org_slug": "great-eastern",
        "role": "OWNER",
        "phone": "+919820100001",
    },
    {
        "email": "priya@greateastern.com",
        "first_name": "Priya",
        "last_name": "Nair",
        "org_slug": "great-eastern",
        "role": "MEMBER",
        "phone": "+919820100002",
    },
    {
        "email": "amit@greateastern.com",
        "first_name": "Amit",
        "last_name": "Patel",
        "org_slug": "great-eastern",
        "role": "MEMBER",
        "phone": "+919820100003",
    },
    # ── Shipping Corporation of India (Buyer) ───────────────────────────────
    {
        "email": "vikram@sci.co.in",
        "first_name": "Vikram",
        "last_name": "Singh",
        "org_slug": "sci",
        "role": "OWNER",
        "phone": "+919820200001",
    },
    {
        "email": "deepa@sci.co.in",
        "first_name": "Deepa",
        "last_name": "Menon",
        "org_slug": "sci",
        "role": "MEMBER",
        "phone": "+919820200002",
    },
    # ── Ocean Ship Stores (Supplier) ────────────────────────────────────────
    {
        "email": "mohammed@oceanshipstores.com",
        "first_name": "Mohammed",
        "last_name": "Khan",
        "org_slug": "ocean-ship-stores",
        "role": "OWNER",
        "phone": "+919820300001",
    },
    {
        "email": "suresh@oceanshipstores.com",
        "first_name": "Suresh",
        "last_name": "Reddy",
        "org_slug": "ocean-ship-stores",
        "role": "MEMBER",
        "phone": "+919820300002",
    },
    # ── Marine Supplies International (Supplier) ────────────────────────────
    {
        "email": "chen@marinesupplies.sg",
        "first_name": "Chen",
        "last_name": "Wei",
        "org_slug": "marine-supplies-intl",
        "role": "OWNER",
        "phone": "+6591234567",
    },
    # ── Navkar Ship Chandlers (Supplier) ────────────────────────────────────
    {
        "email": "kishore@navkarchandlers.com",
        "first_name": "Kishore",
        "last_name": "Jain",
        "org_slug": "navkar-chandlers",
        "role": "OWNER",
        "phone": "+919820400001",
    },
    # ── Seahawk Marine Supplies (Supplier) ──────────────────────────────────
    {
        "email": "lakshmi@seahawkmarine.com",
        "first_name": "Lakshmi",
        "last_name": "Iyer",
        "org_slug": "seahawk-marine",
        "role": "OWNER",
        "phone": "+919820500001",
    },
    # ── Bharat Ship Stores (Supplier) ───────────────────────────────────────
    {
        "email": "ravi@bharatshipstores.com",
        "first_name": "Ravi",
        "last_name": "Kumar",
        "org_slug": "bharat-ship-stores",
        "role": "OWNER",
        "phone": "+919820600001",
    },
    {
        "email": "anita@bharatshipstores.com",
        "first_name": "Anita",
        "last_name": "Das",
        "org_slug": "bharat-ship-stores",
        "role": "MEMBER",
        "phone": "+919820600002",
    },
]
