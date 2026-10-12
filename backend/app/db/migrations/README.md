# Database Migrations

SurgeGuard is configured for PostgreSQL / Supabase persistence.

### Local Development / Phase 0
Database setup is completely non-blocking. In local development or prototype mode, `USE_LOCAL_DEMO_DB=True` allows the application to operate in demo mode without requiring an active external database connection.

### Connecting PostgreSQL / Supabase
When connecting a hosted or local database:
1. Provide `DATABASE_URL=postgresql://user:password@host:5432/surgeguard` in `.env`.
2. Tables and indices will be created adhering to the schema specified in `app/db/models.py` and PRD Section 11.
