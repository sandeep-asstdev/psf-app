# PSF – Post Service Follow-up SaaS Platform

Production-grade, multi-tenant Enterprise SaaS web application engineered for automobile dealerships to manage Post Service Follow-up (PSF), customer complaints, TNPS/NPS surveys, 15/30-day Happiness Calling, and post-resolution reconfirmations.

---

## 1. Tech Stack Overview

- **Frontend**:
  - React 18+ with Vite (JavaScript / JSX only, no TypeScript)
  - Tailwind CSS with persistent **Light AND Dark theme** (class strategy + CSS custom property design tokens)
  - React Router v6, TanStack Query v5, Zustand, React Hook Form + Zod, TanStack Table, Recharts, Lucide Icons, date-fns, react-hot-toast, react-i18next
  - Mobile-first responsive layout (optimized for CREs dialing from smartphones and tablets)
- **Backend**:
  - Python 3.11+, FastAPI (async), Pydantic v2, Uvicorn
  - PostgreSQL 16/18 with Prisma ORM (`schema.prisma` with async Python client)
  - Redis 7 (caching aggregate counters, session store, Celery/ARQ job queue, Pub/Sub live updates)
  - MinIO / S3-compatible storage for customer voice recordings, gate passes, and invoices
  - WebSocket & SSE for real-time dashboard counters and reminders
- **DevOps**:
  - Docker & Docker Compose (`postgres`, `redis`, `minio`, `minio-init`, `api`, `worker`, `web`)
  - Strict tenant isolation (`Tenant` -> `Brand` -> `Branch`) with row-level scoping middleware

---

## 2. Directory Layout

```
PSF/
├── docker-compose.yml          # Full multi-container stack definition
├── .env.example                # Canonical environment template
├── .env                        # Local development variables
├── .gitignore
├── README.md                   # System documentation & setup guide
├── docs/
│   ├── architecture.md         # Full system architecture, multi-tenancy & workflows
│   └── er_diagram.md           # ER Diagram (Mermaid), data dictionary & partitioning plan
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt        # Backend dependencies
│   ├── prisma/
│   │   └── schema.prisma       # Complete PostgreSQL Prisma schema
│   └── app/
│       ├── main.py             # FastAPI entrypoint with CORS, logging & lifecycle
│       ├── api/
│       │   └── v1/
│       │       ├── api.py      # Versioned API router
│       │       └── endpoints/
│       │           └── health.py # Service health & connectivity checks
│       ├── core/
│       │   ├── config.py       # Pydantic v2 settings management
│       │   ├── database.py     # Prisma connection lifecycle
│       │   └── redis.py        # Redis client & caching utilities
│       └── workers/
│           └── runner.py       # Background worker runner
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js      # Light & Dark theme with CSS variable tokens
    ├── postcss.config.js
    ├── index.html
    └── src/
        ├── main.jsx            # React root with QueryClient & Router
        ├── App.jsx             # Route definitions & theme initializer
        ├── index.css           # CSS design tokens for light/dark modes
        ├── i18n/               # Internationalization setup
        ├── store/
        │   └── themeStore.js   # Zustand theme store (persisted + system preference)
        ├── components/
        │   └── layout/
        │       ├── Header.jsx  # Branding, search, theme toggler, user info
        │       ├── Sidebar.jsx # Navigation links & shift attendance
        │       └── AppLayout.jsx # Enterprise responsive layout wrapper
        └── pages/
            ├── HomePage.jsx    # Tile-based workstation matching AppSheet module
            ├── PlaceholderPage.jsx
            └── NotFoundPage.jsx
```

---

## 3. Quick Start (Docker Compose)

To boot the entire distributed infrastructure (Postgres, Redis, MinIO, API, Worker, and Web frontend):

```bash
# 1. Clone repository & verify environment variables
cp .env.example .env

# 2. Launch all services in detached mode
docker-compose up -d

# 3. Check container status
docker-compose ps
```

### Accessible Services:
- **Web Application**: [http://localhost:5173](http://localhost:5173) (or port 80 via Nginx in prod)
- **FastAPI OpenAPI Interactive Docs**: [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
- **FastAPI Healthcheck**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
- **MinIO Storage Console**: [http://localhost:9001](http://localhost:9001) (`minioadmin` / `minioadmin`)
- **PostgreSQL Database**: `localhost:5432` (`psf_admin` / `psf_secure_password_dev` / `psf_db`)
- **Redis**: `localhost:6379`

---

## 4. Local Development Without Docker

### Frontend Setup:
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

### Backend Setup:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
prisma generate --schema=prisma/schema.prisma
uvicorn app.main:app --reload --port 8000
```

---

## 5. Build Roadmap & Next Steps

- [x] **Phase 1: Architecture doc, folder structure, ER diagram, docker-compose, env setup** (Current)
- [ ] **Phase 2: Auth, multi-tenancy, RBAC, user management, login logs**
- [ ] **Phase 3: Masters/settings + questionnaire builder + seed templates**
- [ ] **Phase 4: Data import + allocation**
- [ ] **Phase 5: PSF dashboard + call console + follow-up engine**
- [ ] **Phase 6: Complaints, reconfirmation, TNPS, happiness, advisor modules**
- [ ] **Phase 7: Report dashboard, exports, scheduled reports**
- [ ] **Phase 8: Real-time, notifications, WhatsApp/SMS integrations, PWA**
- [ ] **Phase 9: Testing, hardening, deployment guide, white-label onboarding flow**
