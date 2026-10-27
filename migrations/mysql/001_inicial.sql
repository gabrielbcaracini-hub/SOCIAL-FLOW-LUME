CREATE TABLE organizations (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(160) NOT NULL,
    slug VARCHAR(80) NOT NULL UNIQUE,
    created_at VARCHAR(40) NOT NULL,
    updated_at VARCHAR(40) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL,
    name VARCHAR(160) NOT NULL,
    email VARCHAR(120) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL,
    active TINYINT NOT NULL DEFAULT 1,
    created_at VARCHAR(40) NOT NULL,
    updated_at VARCHAR(40) NOT NULL,
    UNIQUE KEY uq_users_email (email),
    CONSTRAINT fk_users_org FOREIGN KEY (organization_id) REFERENCES organizations(id),
    CONSTRAINT ck_users_role CHECK (role IN ('admin', 'vendedor')),
    CONSTRAINT ck_users_active CHECK (active IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX idx_users_org ON users(organization_id);

CREATE TABLE business_settings (
    organization_id VARCHAR(36) PRIMARY KEY,
    trade_name VARCHAR(160) NOT NULL,
    description TEXT NOT NULL,
    phone VARCHAR(40) NOT NULL,
    email VARCHAR(120) NOT NULL,
    address_public TEXT NOT NULL,
    hours_json TEXT NOT NULL,
    services_json TEXT NOT NULL,
    assistant_json TEXT NOT NULL,
    theme_json TEXT NOT NULL,
    privacy_note TEXT NOT NULL,
    updated_at VARCHAR(40) NOT NULL,
    CONSTRAINT fk_settings_org FOREIGN KEY (organization_id) REFERENCES organizations(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE vehicles (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL,
    brand VARCHAR(80) NOT NULL,
    model VARCHAR(80) NOT NULL,
    version VARCHAR(120) NOT NULL,
    year_manufacture INT NOT NULL,
    year_model INT NOT NULL,
    km INT NOT NULL,
    transmission VARCHAR(20) NOT NULL,
    fuel VARCHAR(20) NOT NULL,
    body_type VARCHAR(20) NOT NULL,
    price_cents INT NOT NULL,
    status VARCHAR(20) NOT NULL,
    color VARCHAR(40) NOT NULL,
    description TEXT NOT NULL,
    stock_code VARCHAR(40) NOT NULL,
    created_at VARCHAR(40) NOT NULL,
    updated_at VARCHAR(40) NOT NULL,
    UNIQUE KEY uq_vehicles_stock (organization_id, stock_code),
    CONSTRAINT fk_vehicles_org FOREIGN KEY (organization_id) REFERENCES organizations(id),
    CONSTRAINT ck_vehicles_year_fab CHECK (year_manufacture BETWEEN 1980 AND 2100),
    CONSTRAINT ck_vehicles_year_mod CHECK (year_model BETWEEN 1980 AND 2100),
    CONSTRAINT ck_vehicles_km CHECK (km >= 0),
    CONSTRAINT ck_vehicles_price CHECK (price_cents >= 100),
    CONSTRAINT ck_vehicles_cambio CHECK (transmission IN ('manual', 'automatico', 'cvt', 'automatizado')),
    CONSTRAINT ck_vehicles_fuel CHECK (fuel IN ('flex', 'gasolina', 'etanol', 'diesel', 'hibrido', 'eletrico')),
    CONSTRAINT ck_vehicles_tipo CHECK (body_type IN ('hatch', 'sedan', 'suv', 'pickup', 'minivan', 'esportivo')),
    CONSTRAINT ck_vehicles_status CHECK (status IN ('disponivel', 'reservado', 'vendido', 'indisponivel'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX idx_vehicles_org_status ON vehicles(organization_id, status);
CREATE INDEX idx_vehicles_org_brand ON vehicles(organization_id, brand);

CREATE TABLE vehicle_images (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL,
    vehicle_id VARCHAR(36) NOT NULL,
    kind VARCHAR(20) NOT NULL,
    label VARCHAR(80) NOT NULL,
    path VARCHAR(500) NOT NULL,
    sort_order INT NOT NULL DEFAULT 0,
    created_at VARCHAR(40) NOT NULL,
    CONSTRAINT fk_images_org FOREIGN KEY (organization_id) REFERENCES organizations(id),
    CONSTRAINT fk_images_vehicle FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE,
    CONSTRAINT ck_images_kind CHECK (kind IN ('placeholder', 'upload'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX idx_images_vehicle ON vehicle_images(vehicle_id, sort_order);

CREATE TABLE leads (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL,
    vehicle_id VARCHAR(36) NULL,
    origin VARCHAR(20) NOT NULL,
    contact_name VARCHAR(160) NOT NULL,
    contact_phone VARCHAR(40) NOT NULL DEFAULT '',
    contact_email VARCHAR(120) NOT NULL DEFAULT '',
    consent TINYINT NOT NULL,
    preferences_json TEXT NOT NULL,
    status VARCHAR(20) NOT NULL,
    notes TEXT NOT NULL,
    assignee_id VARCHAR(36) NULL,
    summary TEXT NOT NULL,
    created_at VARCHAR(40) NOT NULL,
    updated_at VARCHAR(40) NOT NULL,
    CONSTRAINT fk_leads_org FOREIGN KEY (organization_id) REFERENCES organizations(id),
    CONSTRAINT fk_leads_vehicle FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE SET NULL,
    CONSTRAINT fk_leads_assignee FOREIGN KEY (assignee_id) REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT ck_leads_origin CHECK (origin IN ('vitrine', 'detalhe', 'assistente', 'visita', 'contato')),
    CONSTRAINT ck_leads_consent CHECK (consent = 1),
    CONSTRAINT ck_leads_status CHECK (status IN ('novo', 'contatado', 'negociacao', 'ganho', 'perdido'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX idx_leads_org_status ON leads(organization_id, status);

CREATE TABLE appointments (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL,
    lead_id VARCHAR(36) NULL,
    vehicle_id VARCHAR(36) NOT NULL,
    kind VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    starts_at VARCHAR(40) NOT NULL,
    ends_at VARCHAR(40) NOT NULL,
    contact_name VARCHAR(160) NOT NULL,
    contact_phone VARCHAR(40) NOT NULL DEFAULT '',
    contact_email VARCHAR(120) NOT NULL DEFAULT '',
    notes TEXT NOT NULL,
    created_at VARCHAR(40) NOT NULL,
    updated_at VARCHAR(40) NOT NULL,
    CONSTRAINT fk_appt_org FOREIGN KEY (organization_id) REFERENCES organizations(id),
    CONSTRAINT fk_appt_lead FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE SET NULL,
    CONSTRAINT fk_appt_vehicle FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE RESTRICT,
    CONSTRAINT ck_appt_kind CHECK (kind IN ('visita', 'test_drive')),
    CONSTRAINT ck_appt_status CHECK (status IN ('solicitado', 'confirmado', 'reagendado', 'cancelado', 'realizado'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX idx_appointments_vehicle ON appointments(organization_id, vehicle_id, status);

CREATE TABLE chat_sessions (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL,
    preference_json TEXT NOT NULL,
    handoff TINYINT NOT NULL DEFAULT 0,
    lead_id VARCHAR(36) NULL,
    created_at VARCHAR(40) NOT NULL,
    updated_at VARCHAR(40) NOT NULL,
    CONSTRAINT fk_chat_org FOREIGN KEY (organization_id) REFERENCES organizations(id),
    CONSTRAINT fk_chat_lead FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE SET NULL,
    CONSTRAINT ck_chat_handoff CHECK (handoff IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE chat_messages (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL,
    session_id VARCHAR(36) NOT NULL,
    role VARCHAR(20) NOT NULL,
    content VARCHAR(40) NOT NULL,
    structured_json TEXT NOT NULL,
    created_at VARCHAR(40) NOT NULL,
    CONSTRAINT fk_msg_org FOREIGN KEY (organization_id) REFERENCES organizations(id),
    CONSTRAINT fk_msg_session FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
    CONSTRAINT ck_msg_role CHECK (role = 'registro'),
    CONSTRAINT ck_msg_content CHECK (content IN ('recomendacao', 'sem_correspondencia', 'foco', 'incompleta'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX idx_chat_session ON chat_messages(session_id);

CREATE TABLE auth_sessions (
    id VARCHAR(80) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    expires_at VARCHAR(40) NOT NULL,
    created_at VARCHAR(40) NOT NULL,
    CONSTRAINT fk_auth_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX idx_auth_user ON auth_sessions(user_id);

CREATE TABLE client_contexts (
    id VARCHAR(80) PRIMARY KEY,
    csrf_token VARCHAR(128) NOT NULL,
    session_id VARCHAR(80) NULL,
    expires_at VARCHAR(40) NOT NULL,
    created_at VARCHAR(40) NOT NULL,
    CONSTRAINT fk_ctx_session FOREIGN KEY (session_id) REFERENCES auth_sessions(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE audit_log (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NULL,
    action VARCHAR(80) NOT NULL,
    entity VARCHAR(80) NOT NULL,
    entity_id VARCHAR(36) NOT NULL,
    created_at VARCHAR(40) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX idx_audit_org ON audit_log(organization_id, created_at);
