// UN1C0RN^2 SpacetimeDB module.
//
// Replaces the former Supabase schema (supabase/migrations + seed.sql).
//
// Conventions shared with the Python backend (backend/app/db/repositories.py):
//   * Timestamps are i64 microseconds since the Unix epoch; 0 means "not set".
//   * Optional strings use "" for "not set".
//   * JSON documents (parameters, metadata, ...) are stored as JSON text.
//   * Every table is private. Writes go through reducers and backend reads go
//     through the `read_rows` procedure; both accept only an authorized writer:
//       - the dedicated backend identity named by the SENTINEL_BACKEND_IDENTITY
//         environment value (settable only by the database owner when publishing), or
//       - the identity recorded in `owner` by `init` (only set when the database
//         was created from this module).
import { schema, table, t, SenderError, Range } from 'spacetimedb/server';

const SEVERITIES = ['INFO', 'WARNING', 'CRITICAL'];
const DEVICE_STATUSES = ['CONNECTED', 'DISCONNECTED'];
const INCIDENT_STATUSES = ['OPEN', 'RESPONDING', 'RESOLVED', 'UNRESOLVED'];
const COMMAND_TYPES = [
  'FAN_ON', 'FAN_OFF', 'VENT_OPEN', 'VENT_CLOSE', 'BUZZER_ON', 'BUZZER_OFF', 'SET_LED_STATUS',
];
const COMMAND_STATUSES = ['PENDING', 'DELIVERED', 'EXECUTED', 'FAILED', 'EXPIRED'];

const owner = table(
  {},
  {
    id: t.u8().primaryKey(),
    identity: t.identity(),
  }
);

const facilities = table(
  {},
  {
    id: t.string().primaryKey(),
    name: t.string().unique(),
    city: t.string(),
    latitude: t.f64(),
    longitude: t.f64(),
    facility_type: t.string(),
    is_simulated: t.bool(),
    created_at: t.i64(),
  }
);

const devices = table(
  {},
  {
    device_id: t.string().primaryKey(),
    facility_id: t.string().index('btree'),
    device_type: t.string(),
    status: t.string(),
    last_seen: t.i64(),
    created_at: t.i64(),
  }
);

const sensor_readings = table(
  {},
  {
    id: t.string().primaryKey(),
    device_id: t.string().index('btree'),
    facility_id: t.string().index('btree'),
    temperature_c: t.f64(),
    humidity_percent: t.f64(),
    vibration_score: t.f64(),
    water_detected: t.bool(),
    timestamp_ms: t.i64(),
    boot_id: t.string(),
    is_simulated: t.bool(),
    recorded_at: t.i64().index('btree'),
  }
);

const incidents = table(
  {},
  {
    id: t.string().primaryKey(),
    facility_id: t.string().index('btree'),
    incident_type: t.string(),
    severity: t.string(),
    status: t.string(),
    description: t.string(),
    detected_readings: t.string(),
    verification_data: t.string(),
    detected_at: t.i64().index('btree'),
    resolved_at: t.i64(),
  }
);

const ai_decisions = table(
  {},
  {
    id: t.string().primaryKey(),
    incident_id: t.string().index('btree'),
    model_name: t.string(),
    has_anomaly_score: t.bool(),
    anomaly_score: t.f64(),
    anomaly_detected: t.bool(),
    severity: t.string(),
    reasoning: t.string(),
    tool_calls: t.string(),
    recommended_action: t.string(),
    decision_source: t.string(),
    created_at: t.i64().index('btree'),
  }
);

const hardware_commands = table(
  {},
  {
    id: t.string().primaryKey(),
    device_id: t.string().index('btree'),
    incident_id: t.string(),
    command_type: t.string(),
    parameters: t.string(),
    status: t.string(),
    reported_state: t.string(),
    failure_reason: t.string(),
    created_at: t.i64().index('btree'),
    acknowledged_at: t.i64(),
    executed_at: t.i64(),
  }
);

const system_events = table(
  {},
  {
    id: t.string().primaryKey(),
    event_type: t.string(),
    device_id: t.string(),
    description: t.string(),
    metadata: t.string(),
    created_at: t.i64().index('btree'),
  }
);

const spacetimedb = schema(
  {
    owner,
    facilities,
    devices,
    sensor_readings,
    incidents,
    ai_decisions,
    hardware_commands,
    system_events,
  },
  {
    env: {
      // Hex identity of the FastAPI backend. Public information, not a secret.
      SENTINEL_BACKEND_IDENTITY: t.string().optional(),
    },
  }
);
export default spacetimedb;

type IdentityLike = { toHexString(): string };

function normalizeHex(value: string): string {
  return value.trim().toLowerCase().replace(/^0x/, '');
}

function isAuthorizedWriter(
  ownerRow: { identity: IdentityLike } | null | undefined,
  sender: IdentityLike,
  backendIdentity: string | undefined
): boolean {
  const senderHex = normalizeHex(sender.toHexString());
  if (backendIdentity && normalizeHex(backendIdentity) === senderHex) {
    return true;
  }
  return !!ownerRow && normalizeHex(ownerRow.identity.toHexString()) === senderHex;
}

function requireWriter(
  ownerRow: { identity: IdentityLike } | null | undefined,
  sender: IdentityLike,
  backendIdentity: string | undefined
): void {
  if (!isAuthorizedWriter(ownerRow, sender, backendIdentity)) {
    throw new SenderError('Only the UN1C0RN^2 backend identity may access this database');
  }
}

function requireOneOf(field: string, value: string, allowed: string[]): void {
  if (!allowed.includes(value)) {
    throw new SenderError(`${field} must be one of ${allowed.join(', ')}; got ${value}`);
  }
}

function requireRange(field: string, value: number, min: number, max: number): void {
  if (!Number.isFinite(value) || value < min || value > max) {
    throw new SenderError(`${field} must be between ${min} and ${max}; got ${value}`);
  }
}

function requireJson(field: string, value: string): void {
  try {
    JSON.parse(value);
  } catch {
    throw new SenderError(`${field} must be valid JSON text`);
  }
}

// Seed data (formerly supabase/seed.sql).
const SEED_FACILITIES = [
  ['facility-main', 'UN1C0RN^2 Lab', 'Austin', 30.2672, -97.7431, 'DEMO', false],
  ['facility-sim-west', 'UN1C0RN^2 Sim West', 'San Francisco', 37.7749, -122.4194, 'SIMULATED', true],
  ['facility-sim-central', 'UN1C0RN^2 Sim Central', 'Chicago', 41.8781, -87.6298, 'SIMULATED', true],
  ['facility-sim-east', 'UN1C0RN^2 Sim East', 'New York', 40.7128, -74.006, 'SIMULATED', true],
] as const;

const SEED_DEVICES = [
  ['sentinel-esp32', 'facility-main', 'ESP32_SENSOR'],
  ['sentinel-pico', 'facility-main', 'PICO_CONTROLLER'],
  ['facility-sim-west-sensor', 'facility-sim-west', 'SIMULATED_SENSOR'],
  ['facility-sim-west-controller', 'facility-sim-west', 'SIMULATED_CONTROLLER'],
  ['facility-sim-central-sensor', 'facility-sim-central', 'SIMULATED_SENSOR'],
  ['facility-sim-central-controller', 'facility-sim-central', 'SIMULATED_CONTROLLER'],
  ['facility-sim-east-sensor', 'facility-sim-east', 'SIMULATED_SENSOR'],
  ['facility-sim-east-controller', 'facility-sim-east', 'SIMULATED_CONTROLLER'],
] as const;

type SeedDb = {
  facilities: {
    id: { find(id: string): unknown };
    insert(row: {
      id: string; name: string; city: string; latitude: number; longitude: number;
      facility_type: string; is_simulated: boolean; created_at: bigint;
    }): unknown;
  };
  devices: {
    device_id: { find(id: string): unknown };
    insert(row: {
      device_id: string; facility_id: string; device_type: string; status: string;
      last_seen: bigint; created_at: bigint;
    }): unknown;
  };
};

/** Inserts any missing seed facilities/devices. Never modifies existing rows. */
function seedReferenceData(db: SeedDb, now: bigint): number {
  let inserted = 0;
  for (const [id, name, city, latitude, longitude, facility_type, is_simulated] of SEED_FACILITIES) {
    if (!db.facilities.id.find(id)) {
      db.facilities.insert({
        id, name, city, latitude, longitude, facility_type, is_simulated, created_at: now,
      });
      inserted++;
    }
  }
  for (const [device_id, facility_id, device_type] of SEED_DEVICES) {
    if (!db.devices.device_id.find(device_id)) {
      db.devices.insert({
        device_id, facility_id, device_type, status: 'DISCONNECTED', last_seen: 0n, created_at: now,
      });
      inserted++;
    }
  }
  return inserted;
}

// Runs only when a database is first created from this module (or after --delete-data).
export const init = spacetimedb.init(ctx => {
  ctx.db.owner.insert({ id: 0, identity: ctx.sender });
  seedReferenceData(ctx.db, ctx.timestamp.microsSinceUnixEpoch);
});

// Idempotent repair for databases where `init` never ran (module published as an update).
export const ensure_seed_data = spacetimedb.reducer(ctx => {
  requireWriter(ctx.db.owner.id.find(0), ctx.sender, ctx.env.SENTINEL_BACKEND_IDENTITY);
  seedReferenceData(ctx.db, ctx.timestamp.microsSinceUnixEpoch);
});

export const upsert_device = spacetimedb.reducer(
  { row: devices.rowType },
  (ctx, { row }) => {
    requireWriter(ctx.db.owner.id.find(0), ctx.sender, ctx.env.SENTINEL_BACKEND_IDENTITY);
    requireOneOf('status', row.status, DEVICE_STATUSES);
    if (!ctx.db.facilities.id.find(row.facility_id)) {
      throw new SenderError(`Unknown facility ${row.facility_id}`);
    }
    const existing = ctx.db.devices.device_id.find(row.device_id);
    if (existing) {
      ctx.db.devices.device_id.update({ ...row, created_at: existing.created_at });
    } else {
      ctx.db.devices.insert(row);
    }
  }
);

export const insert_sensor_readings = spacetimedb.reducer(
  { rows: t.array(sensor_readings.rowType) },
  (ctx, { rows }) => {
    requireWriter(ctx.db.owner.id.find(0), ctx.sender, ctx.env.SENTINEL_BACKEND_IDENTITY);
    for (const row of rows) {
      requireRange('temperature_c', row.temperature_c, -20, 100);
      requireRange('humidity_percent', row.humidity_percent, 0, 100);
      requireRange('vibration_score', row.vibration_score, 0, Number.MAX_VALUE);
      if (row.timestamp_ms < 0n) {
        throw new SenderError('timestamp_ms must be non-negative');
      }
      // Re-sent batches after a failed flush must not abort the whole transaction.
      if (!ctx.db.sensor_readings.id.find(row.id)) {
        ctx.db.sensor_readings.insert(row);
      }
    }
  }
);

export const upsert_incident = spacetimedb.reducer(
  { row: incidents.rowType },
  (ctx, { row }) => {
    requireWriter(ctx.db.owner.id.find(0), ctx.sender, ctx.env.SENTINEL_BACKEND_IDENTITY);
    requireOneOf('severity', row.severity, SEVERITIES);
    requireOneOf('status', row.status, INCIDENT_STATUSES);
    requireJson('detected_readings', row.detected_readings);
    requireJson('verification_data', row.verification_data);
    if (ctx.db.incidents.id.find(row.id)) {
      ctx.db.incidents.id.update(row);
    } else {
      ctx.db.incidents.insert(row);
    }
  }
);

export const upsert_ai_decision = spacetimedb.reducer(
  { row: ai_decisions.rowType },
  (ctx, { row }) => {
    requireWriter(ctx.db.owner.id.find(0), ctx.sender, ctx.env.SENTINEL_BACKEND_IDENTITY);
    requireOneOf('severity', row.severity, SEVERITIES);
    requireJson('tool_calls', row.tool_calls);
    if (ctx.db.ai_decisions.id.find(row.id)) {
      ctx.db.ai_decisions.id.update(row);
    } else {
      ctx.db.ai_decisions.insert(row);
    }
  }
);

export const upsert_hardware_command = spacetimedb.reducer(
  { row: hardware_commands.rowType },
  (ctx, { row }) => {
    requireWriter(ctx.db.owner.id.find(0), ctx.sender, ctx.env.SENTINEL_BACKEND_IDENTITY);
    requireOneOf('command_type', row.command_type, COMMAND_TYPES);
    requireOneOf('status', row.status, COMMAND_STATUSES);
    requireJson('parameters', row.parameters);
    requireJson('reported_state', row.reported_state);
    if (ctx.db.hardware_commands.id.find(row.id)) {
      ctx.db.hardware_commands.id.update(row);
    } else {
      ctx.db.hardware_commands.insert(row);
    }
  }
);

export const insert_system_event = spacetimedb.reducer(
  { row: system_events.rowType },
  (ctx, { row }) => {
    requireWriter(ctx.db.owner.id.find(0), ctx.sender, ctx.env.SENTINEL_BACKEND_IDENTITY);
    requireJson('metadata', row.metadata);
    ctx.db.system_events.insert(row);
  }
);

// ---------------------------------------------------------------------------
// Authorized reads for the backend identity (private tables are not readable
// over SQL by non-owner identities). Returns a JSON array of rows, newest first.
// ---------------------------------------------------------------------------
const MAX_READ_ROWS = 5000;

function jsonSafe(row: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(row)) {
    out[key] = typeof value === 'bigint' ? Number(value) : value;
  }
  return out;
}

function newestFirst<R extends Record<string, unknown>>(rows: R[], column: string, limit: number): R[] {
  rows.sort((a, b) => {
    const left = a[column] as bigint;
    const right = b[column] as bigint;
    return left === right ? 0 : left > right ? -1 : 1;
  });
  return rows.slice(0, limit);
}

export const read_rows = spacetimedb.procedure(
  { table: t.string(), since: t.i64(), limit: t.u32() },
  t.string(),
  (ctx, { table, since, limit }) => {
    const cap = Math.max(1, Math.min(limit, MAX_READ_ROWS));
    const after = new Range<bigint>({ tag: 'included', value: since }, { tag: 'unbounded' });
    return ctx.withTx(tx => {
      requireWriter(tx.db.owner.id.find(0), tx.sender, tx.env.SENTINEL_BACKEND_IDENTITY);
      let rows: Record<string, unknown>[];
      switch (table) {
        case 'facilities':
          rows = newestFirst([...tx.db.facilities.iter()], 'created_at', cap);
          break;
        case 'devices':
          rows = newestFirst([...tx.db.devices.iter()], 'created_at', cap);
          break;
        case 'sensor_readings':
          rows = newestFirst([...tx.db.sensor_readings.recorded_at.filter(after)], 'recorded_at', cap);
          break;
        case 'incidents':
          rows = newestFirst([...tx.db.incidents.detected_at.filter(after)], 'detected_at', cap);
          break;
        case 'ai_decisions':
          rows = newestFirst([...tx.db.ai_decisions.created_at.filter(after)], 'created_at', cap);
          break;
        case 'hardware_commands':
          rows = newestFirst([...tx.db.hardware_commands.created_at.filter(after)], 'created_at', cap);
          break;
        case 'system_events':
          rows = newestFirst([...tx.db.system_events.created_at.filter(after)], 'created_at', cap);
          break;
        default:
          throw new SenderError(`Table ${table} is not readable`);
      }
      return JSON.stringify(rows.map(jsonSafe));
    });
  }
);
