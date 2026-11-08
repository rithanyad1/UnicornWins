# SENTINEL SpacetimeDB module

This TypeScript module defines the persistent schema for the SENTINEL backend. It replaces the former Supabase migrations and seed data.

## Tables

All tables are private. Only the identity that first published the database can call write reducers or read rows over SQL. That identity is recorded in `owner` by `init`.

| Table | Primary key | Written by |
|---|---|---|
| `owner` | `id` (always 0) | `init` |
| `facilities` | `id` | `init` (seed only) |
| `devices` | `device_id` | `init`, `upsert_device` |
| `sensor_readings` | `id` | `insert_sensor_readings` (batch) |
| `incidents` | `id` | `upsert_incident` |
| `ai_decisions` | `id` | `upsert_ai_decision` |
| `hardware_commands` | `id` | `upsert_hardware_command` |
| `system_events` | `id` | `insert_system_event` |

Column conventions, shared with `backend/app/db/repositories.py`:

- Timestamps are `i64` microseconds since the Unix epoch. `0` means "not set".
- Optional strings use `""` for "not set".
- JSON documents (`parameters`, `metadata`, `tool_calls`, and so on) are stored as JSON text.
- `ai_decisions.anomaly_score` is paired with `has_anomaly_score`.

Reducers enforce the same rules as the old SQL `CHECK` constraints: allowed enum values, sensor value ranges, and valid JSON.

## Publish

```bash
npm install
npm run typecheck
spacetime login
spacetime publish sentinel                      # Maincloud
spacetime publish --server local sentinel       # local `spacetime start`
spacetime login show --token                    # token for backend/.env SPACETIMEDB_TOKEN
```

Changing the type of a column, or removing one, needs `spacetime publish --delete-data sentinel`. That wipes all rows and re-runs `init`.

## Inspect

```bash
spacetime sql sentinel "SELECT * FROM incidents WHERE status = 'OPEN'"
spacetime logs sentinel
```
