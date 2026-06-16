# Umbrella Core — Phase 1 Foundation

Central backend for UmbrellaMC. All clients (Discord bot, Minecraft plugin, dashboard) talk to this.

## What's in Phase 1

- **Settings registry** — all configuration stored in DB, editable via API
- **Audit log** — append-only record of every action
- **Roles & permissions** — 4 default roles (Owner, Admin, Moderator, Helper) with 14 permission keys
- **REST API** — `/health`, `/api/v1/settings`, `/api/v1/roles`, `/api/v1/audit`
- **Database** — PostgreSQL via async SQLAlchemy, Alembic migrations
- **Redis** — configured, not yet used (reserved for Phase 3 caching)

## Quick Start

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env — set SECRET_KEY and INITIAL_ADMIN_DISCORD_ID at minimum
```

### 2. Start with Docker (recommended)

```bash
docker compose up -d
```

Core will be available at `http://localhost:8765`.

### 3. Or run locally

```bash
# Start Postgres and Redis separately, then:
pip install -r requirements.txt

# Run Alembic migrations (first time only)
alembic upgrade head

# Start the server
python main.py
```

## API Quick Reference

All admin endpoints require the header: `X-Admin-Key: <your SECRET_KEY>`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check (no auth) |
| GET | `/api/v1/settings` | List all settings |
| GET | `/api/v1/settings/{key}` | Get one setting |
| PATCH | `/api/v1/settings/{key}` | Update a setting |
| GET | `/api/v1/roles` | List all roles |
| GET | `/api/v1/roles/permissions` | List all permissions |
| GET | `/api/v1/audit` | Paginated audit log |

Enable interactive docs by setting `DEBUG=true` in `.env`, then visit `http://localhost:8765/docs`.

## Plugin Integration (Phase 1)

The Minecraft plugin should send `X-Plugin-Key: <SECRET_KEY>` on every request to Core.
For now, plugin key and admin key use the same `SECRET_KEY` value.
Separate plugin-specific keys come in Phase 6.

## Alembic Migrations

```bash
# Apply all migrations
alembic upgrade head

# Generate new migration after model changes
alembic revision --autogenerate -m "describe your change"

# Roll back one step
alembic downgrade -1
```

## Project Structure

```
umbrella-core/
├── main.py                    # App entry point, lifespan, router registration
├── config/
│   └── settings.py            # Pydantic settings (loads from .env)
├── database/
│   └── engine.py              # Async SQLAlchemy engine + session factory
├── models/
│   ├── setting.py             # Settings table ORM
│   ├── audit_log.py           # Audit log table ORM
│   └── permissions.py         # Roles + permissions ORM
├── services/
│   ├── settings_service.py    # Business logic for settings
│   └── roles_service.py       # Business logic for roles
├── api/
│   ├── middleware/
│   │   └── auth.py            # API key authentication
│   └── routers/
│       ├── health.py          # GET /health
│       ├── settings.py        # /api/v1/settings
│       ├── roles.py           # /api/v1/roles
│       └── audit.py           # /api/v1/audit
├── alembic/
│   ├── env.py                 # Alembic async configuration
│   └── versions/
│       └── 001_initial.py     # Initial schema migration
├── requirements.txt
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
└── .env.example
```

## What Comes Next

- **Phase 2**: Settings API used by bot/plugin to load config dynamically
- **Phase 3**: Discord OAuth login, session tokens, dashboard login page
- **Phase 4**: Dashboard skeleton built against this API
- **Phase 5**: Audit + undo system
- **Phase 6**: Moderation system + plugin CoreClient replacement
