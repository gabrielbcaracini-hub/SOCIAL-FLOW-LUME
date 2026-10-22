PRAGMA foreign_keys = ON;

CREATE TABLE organizations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE users (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id),
    name TEXT NOT NULL,
    email TEXT NOT NULL COLLATE NOCASE UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'vendedor')),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX idx_users_org ON users(organization_id);

CREATE TABLE business_settings (
    organization_id TEXT PRIMARY KEY REFERENCES organizations(id),
    trade_name TEXT NOT NULL,
    description TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT NOT NULL,
    address_public TEXT NOT NULL,
    hours_json TEXT NOT NULL,
    services_json TEXT NOT NULL,
    assistant_json TEXT NOT NULL,
    theme_json TEXT NOT NULL,
    privacy_note TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE vehicles (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id),
    brand TEXT NOT NULL,
    model TEXT NOT NULL,
    version TEXT NOT NULL,
    year_manufacture INTEGER NOT NULL CHECK (year_manufacture BETWEEN 1980 AND 2100),
    year_model INTEGER NOT NULL CHECK (year_model BETWEEN 1980 AND 2100),
    km INTEGER NOT NULL CHECK (km >= 0),
    transmission TEXT NOT NULL CHECK (transmission IN ('manual', 'automatico', 'cvt', 'automatizado')),
    fuel TEXT NOT NULL CHECK (fuel IN ('flex', 'gasolina', 'etanol', 'diesel', 'hibrido', 'eletrico')),
    body_type TEXT NOT NULL CHECK (body_type IN ('hatch', 'sedan', 'suv', 'pickup', 'minivan', 'esportivo')),
    price_cents INTEGER NOT NULL CHECK (price_cents >= 100),
    status TEXT NOT NULL CHECK (status IN ('disponivel', 'reservado', 'vendido', 'indisponivel')),
    color TEXT NOT NULL,
    description TEXT NOT NULL,
    stock_code TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (organization_id, stock_code)
);
CREATE INDEX idx_vehicles_org_status ON vehicles(organization_id, status);
CREATE INDEX idx_vehicles_org_brand ON vehicles(organization_id, brand);

CREATE TABLE vehicle_images (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id),
    vehicle_id TEXT NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('placeholder', 'upload')),
    label TEXT NOT NULL,
    path TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE INDEX idx_images_vehicle ON vehicle_images(vehicle_id, sort_order);

CREATE TABLE leads (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id),
    vehicle_id TEXT REFERENCES vehicles(id) ON DELETE SET NULL,
    origin TEXT NOT NULL CHECK (origin IN ('vitrine', 'detalhe', 'assistente', 'visita')),
    contact_name TEXT NOT NULL,
    contact_phone TEXT NOT NULL DEFAULT '',
    contact_email TEXT NOT NULL DEFAULT '',
    consent INTEGER NOT NULL CHECK (consent = 1),
    preferences_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL CHECK (status IN ('novo', 'contatado', 'negociacao', 'ganho', 'perdido')),
    notes TEXT NOT NULL DEFAULT '',
    assignee_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    summary TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX idx_leads_org_status ON leads(organization_id, status);

CREATE TABLE appointments (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id),
    lead_id TEXT REFERENCES leads(id) ON DELETE SET NULL,
    vehicle_id TEXT NOT NULL REFERENCES vehicles(id) ON DELETE RESTRICT,
    kind TEXT NOT NULL CHECK (kind IN ('visita', 'test_drive')),
    status TEXT NOT NULL CHECK (status IN ('solicitado', 'confirmado', 'reagendado', 'cancelado', 'realizado')),
    starts_at TEXT NOT NULL,
    ends_at TEXT NOT NULL,
    contact_name TEXT NOT NULL,
    contact_phone TEXT NOT NULL DEFAULT '',
    contact_email TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX idx_appointments_vehicle ON appointments(organization_id, vehicle_id, status);

CREATE TABLE chat_sessions (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id),
    preference_json TEXT NOT NULL DEFAULT '{}',
    handoff INTEGER NOT NULL DEFAULT 0 CHECK (handoff IN (0, 1)),
    lead_id TEXT REFERENCES leads(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE chat_messages (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id),
    session_id TEXT NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role = 'registro'),
    content TEXT NOT NULL CHECK (content IN ('recomendacao', 'sem_correspondencia', 'foco', 'incompleta')),
    structured_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE INDEX idx_chat_session ON chat_messages(session_id);

CREATE TABLE auth_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX idx_auth_user ON auth_sessions(user_id);

CREATE TABLE client_contexts (
    id TEXT PRIMARY KEY,
    csrf_token TEXT NOT NULL,
    session_id TEXT REFERENCES auth_sessions(id) ON DELETE SET NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE audit_log (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    user_id TEXT,
    action TEXT NOT NULL,
    entity TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX idx_audit_org ON audit_log(organization_id, created_at);
