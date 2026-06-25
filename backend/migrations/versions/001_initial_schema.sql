-- ============================================================
-- SCHEMA INICIAL — Piping CMS
-- Fontes: TYS-TUB-1 (MTO), SGS-SGM (spools), Valvulas,
--         MAPA_JUNTA (juntas), Databook Paradox (JUNTAS/TUB/
--         SOLD/LOTERX/INCONF/RASTMAT/RESUMO)
-- ============================================================

-- ------------------------------------------------------------
-- ENUMS
-- ------------------------------------------------------------
CREATE TYPE joint_type     AS ENUM ('RO','SU','TP','AN','BL','LO');
CREATE TYPE material_code  AS ENUM ('AC','AL','AI','ST');
CREATE TYPE insp_level     AS ENUM ('0','1','2','3');
CREATE TYPE ndt_result     AS ENUM ('A','R','N','M');
CREATE TYPE spool_scope    AS ENUM ('SHOP','FIELD','VENDOR');
CREATE TYPE user_role      AS ENUM ('ADMIN','FIELD_ENGINEER','QC_INSPECTOR','VIEWER');

-- status de junta (campo sger do ControlTub)
CREATE TYPE joint_status AS ENUM (
  '01_NAO_INICIADA',
  '03_AGUARD_ACOPLAMENTO',
  '04_AGUARD_SOLDAGEM',
  '09_AGUARD_VS',
  '12_AGUARD_LP_PM',
  '14_AGUARD_LIB_LOTE',
  '15_AGUARD_RX_US',
  '18_AGUARD_RX_REPARO',
  '23_AGUARD_TT',
  '30_LIBERADA'
);

-- status de spool
CREATE TYPE spool_status AS ENUM (
  'NAO_INICIADO',
  'EM_FABRICACAO',
  'FABRICADO',
  'EM_CAMPO',
  'MONTADO',
  'TESTADO'
);

-- ------------------------------------------------------------
-- PROJETOS / UNIDADES
-- ------------------------------------------------------------
CREATE TABLE projects (
  id          SERIAL PRIMARY KEY,
  code        VARCHAR(20)  NOT NULL UNIQUE,
  name        VARCHAR(255) NOT NULL,
  created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE units (
  id          SERIAL PRIMARY KEY,
  project_id  INTEGER NOT NULL REFERENCES projects(id),
  code        VARCHAR(10)  NOT NULL,  -- ex: U4710, U4730
  sub_unit    VARCHAR(10),            -- ex: 1A, 2B
  description VARCHAR(255),
  UNIQUE(project_id, code, sub_unit)
);

-- ------------------------------------------------------------
-- LINHAS
-- ------------------------------------------------------------
CREATE TABLE pipe_lines (
  id              SERIAL PRIMARY KEY,
  project_id      INTEGER      NOT NULL REFERENCES projects(id),
  unit_id         INTEGER      NOT NULL REFERENCES units(id),
  line_tag        VARCHAR(100) NOT NULL,
  fluid           VARCHAR(50),
  line_type       VARCHAR(50),
  material        material_code,
  spec            VARCHAR(100),
  diameter_mm     NUMERIC(8,2),
  revision        VARCHAR(10),
  UNIQUE(project_id, line_tag)
);

-- ------------------------------------------------------------
-- SPOOLS
-- Fonte principal: SGS-SGM Excel (File 2) + TUB.csv (Databook)
-- ------------------------------------------------------------
CREATE TABLE spools (
  id                  SERIAL PRIMARY KEY,
  project_id          INTEGER      NOT NULL REFERENCES projects(id),
  pipe_line_id        INTEGER      REFERENCES pipe_lines(id),
  unit_id             INTEGER      REFERENCES units(id),
  isometrico          VARCHAR(30)  NOT NULL,
  spool               VARCHAR(10)  NOT NULL,
  spool_key           VARCHAR(50)  GENERATED ALWAYS AS (isometrico || '-' || spool) STORED,
  revision            VARCHAR(5),
  manufacturer        VARCHAR(100),
  scope               spool_scope,
  diameter_mm         NUMERIC(8,2),
  thickness_mm        NUMERIC(8,3),
  length_m            NUMERIC(12,4),
  weight_kg           NUMERIC(12,4),
  area_m2             NUMERIC(12,4),
  material            material_code,
  spec                VARCHAR(100),
  hold                BOOLEAN      NOT NULL DEFAULT FALSE,
  hold_reason         TEXT,
  status              spool_status NOT NULL DEFAULT 'NAO_INICIADO',
  -- contagem de juntas
  joints_total        INTEGER      DEFAULT 0,
  joints_welded       INTEGER      DEFAULT 0,
  joints_released     INTEGER      DEFAULT 0,
  joints_tt           INTEGER      DEFAULT 0,  -- requerem TT
  joints_rt           INTEGER      DEFAULT 0,  -- requerem RT
  joints_ut           INTEGER      DEFAULT 0,
  joints_lp           INTEGER      DEFAULT 0,
  -- datas fabricação
  dt_lib_fab          DATE,
  dt_prog_fab         DATE,
  dt_corte            DATE,
  dt_acoplamento      DATE,
  dt_soldagem         DATE,
  dt_vs               DATE,
  dt_lib_end          DATE,
  dt_tt               DATE,
  dt_pintura          DATE,
  dt_dimensional      DATE,
  dt_embarque         DATE,
  -- datas montagem
  dt_lib_mon          DATE,
  dt_prog_mon         DATE,
  dt_pre_mon          DATE,
  dt_montagem         DATE,
  dt_sth              DATE,
  dt_lavagem          DATE,
  -- progresso %
  pct_fab             NUMERIC(5,2) DEFAULT 0,
  pct_mon             NUMERIC(5,2) DEFAULT 0,
  -- metadados
  sger                VARCHAR(100),
  obs                 TEXT,
  source              VARCHAR(20)  NOT NULL DEFAULT 'SGS', -- SGS | DATABOOK
  created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  UNIQUE(project_id, isometrico, spool)
);

CREATE INDEX idx_spools_project  ON spools(project_id);
CREATE INDEX idx_spools_unit     ON spools(unit_id);
CREATE INDEX idx_spools_status   ON spools(status);
CREATE INDEX idx_spools_hold     ON spools(hold) WHERE hold = TRUE;
CREATE INDEX idx_spools_key      ON spools(spool_key);

-- ------------------------------------------------------------
-- MTO — itens do modelo 3D
-- Fonte: TYS-TUB-1 Excel (File 1) ~168k linhas
-- ------------------------------------------------------------
CREATE TABLE mto_items (
  id                BIGSERIAL PRIMARY KEY,
  project_id        INTEGER      NOT NULL REFERENCES projects(id),
  spool_id          INTEGER      REFERENCES spools(id),
  pipe_line_id      INTEGER      REFERENCES pipe_lines(id),
  unit_id           INTEGER      REFERENCES units(id),
  isometrico        VARCHAR(30),
  spool_number_raw  VARCHAR(50),
  item_3d_name      VARCHAR(200),
  item_3d_type      VARCHAR(100),
  description       TEXT,
  material_spec     VARCHAR(100),
  material_code_std VARCHAR(150),
  material_code_alt VARCHAR(150),
  diameter_nom_mm   NUMERIC(8,2),
  diameter_sec_mm   NUMERIC(8,2),
  pipe_length_m     NUMERIC(12,4),
  elevation_m       NUMERIC(10,3),
  weight_kg         NUMERIC(12,4),
  surface_area_m2   NUMERIC(12,4),
  position          VARCHAR(100),
  scope             VARCHAR(50),
  zone              VARCHAR(100),
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_mto_spool       ON mto_items(spool_id);
CREATE INDEX idx_mto_mat_std     ON mto_items(material_code_std);
CREATE INDEX idx_mto_iso         ON mto_items(isometrico);
CREATE INDEX idx_mto_type        ON mto_items(item_3d_type);

-- ------------------------------------------------------------
-- JUNTAS (soldas individuais)
-- Fonte: MAPA_JUNTA xlsb (File 4) ~93k + JUNTAS.csv Databook
-- ------------------------------------------------------------
CREATE TABLE joints (
  id                BIGSERIAL PRIMARY KEY,
  project_id        INTEGER      NOT NULL REFERENCES projects(id),
  spool_id          INTEGER      REFERENCES spools(id),
  isometrico        VARCHAR(30)  NOT NULL,
  spool             VARCHAR(10)  NOT NULL,
  junta             VARCHAR(10)  NOT NULL,
  joint_key         VARCHAR(70)  GENERATED ALWAYS AS (isometrico || '-' || spool || '-' || junta) STORED,
  joint_type        joint_type,
  diameter_in       VARCHAR(10),  -- ex: "1 1/2""
  diameter_mm       INTEGER,
  thickness_mm      NUMERIC(8,3),
  material          material_code,
  insp_level        insp_level,
  pressure_class    VARCHAR(5),   -- C ou P
  requires_tt       BOOLEAN      DEFAULT FALSE,
  requires_ut       BOOLEAN      DEFAULT FALSE,
  is_repair         BOOLEAN      DEFAULT FALSE, -- junta R001...
  sth               VARCHAR(50),
  ieis              VARCHAR(20),
  status            joint_status NOT NULL DEFAULT '01_NAO_INICIADA',
  -- soldadores
  welder_root_id    INTEGER      REFERENCES welders(id),
  welder_fill_id    INTEGER      REFERENCES welders(id),
  -- consumíveis / rastreabilidade
  heat_number_1     VARCHAR(20),
  heat_number_2     VARCHAR(20),
  corrida_1         VARCHAR(20),
  corrida_2         VARCHAR(20),
  corrida_3         VARCHAR(20),
  corrida_4         VARCHAR(20),
  -- datas
  dt_corte          DATE,
  dt_acoplamento    DATE,
  dt_soldagem       DATE,
  dt_vs             DATE,
  dt_lp             DATE,
  dt_rx             DATE,
  dt_tt             DATE,
  dt_lib_end        DATE,
  dt_embarque       DATE,
  dt_prog_mon       DATE,
  dt_montagem       DATE,
  -- resultados NDT (resumo por junta)
  result_vs         ndt_result,
  result_lp         ndt_result,
  result_rx         ndt_result,
  result_us         ndt_result,
  result_tt         ndt_result,
  -- metadados
  sger              joint_status,
  prog_fab          DATE,
  source            VARCHAR(20) NOT NULL DEFAULT 'EXCEL', -- EXCEL | DATABOOK
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(project_id, isometrico, spool, junta)
);

CREATE INDEX idx_joints_spool    ON joints(spool_id);
CREATE INDEX idx_joints_status   ON joints(status);
CREATE INDEX idx_joints_key      ON joints(joint_key);
CREATE INDEX idx_joints_mat      ON joints(material);
CREATE INDEX idx_joints_repair   ON joints(is_repair) WHERE is_repair = TRUE;

-- ------------------------------------------------------------
-- SOLDADORES
-- Fonte: SOLD.csv (Databook)
-- ------------------------------------------------------------
CREATE TABLE welders (
  id              SERIAL PRIMARY KEY,
  project_id      INTEGER      NOT NULL REFERENCES projects(id),
  sin             VARCHAR(20)  NOT NULL,  -- matrícula/crachá
  name            VARCHAR(100),
  company         VARCHAR(50),
  process         VARCHAR(10),            -- GTAW, SMAW, FCAW...
  p_number        SMALLINT,
  f_number        SMALLINT,
  diam_min_mm     SMALLINT,
  thickness_max_mm SMALLINT,
  positions_qual  VARCHAR(10),
  dt_qualification DATE,
  dt_requalification DATE,
  disqualified    BOOLEAN     DEFAULT FALSE,
  rt_repair_index NUMERIC(5,2),           -- índice de reparo acumulado
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(project_id, sin)
);

-- ------------------------------------------------------------
-- LOTES RX (radiografia)
-- Fonte: LOTERX.csv (Databook)
-- ------------------------------------------------------------
CREATE TABLE rt_lots (
  id          SERIAL PRIMARY KEY,
  project_id  INTEGER     NOT NULL REFERENCES projects(id),
  joint_id    BIGINT      REFERENCES joints(id),
  lot_number  VARCHAR(30) NOT NULL,
  isometrico  VARCHAR(30),
  spool       VARCHAR(10),
  junta       VARCHAR(10),
  diameter_mm SMALLINT,
  thickness_mm NUMERIC(8,3),
  result      ndt_result,
  film_lot    VARCHAR(10),
  technician  VARCHAR(20),
  company     VARCHAR(20),
  dt_exam     DATE,
  status_code VARCHAR(5),
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_rtlots_joint ON rt_lots(joint_id);

-- ------------------------------------------------------------
-- NÃO-CONFORMIDADES
-- Fonte: INCONF.csv (Databook)
-- ------------------------------------------------------------
CREATE TABLE nonconformances (
  id              SERIAL PRIMARY KEY,
  project_id      INTEGER     NOT NULL REFERENCES projects(id),
  joint_id        BIGINT      REFERENCES joints(id),
  spool_id        INTEGER     REFERENCES spools(id),
  rnc_number      VARCHAR(20),
  system_code     SMALLINT,
  operation_code  SMALLINT,
  description     TEXT,
  dt_generated    DATE,
  released        BOOLEAN     DEFAULT FALSE,
  dt_released     DATE,
  released_by     VARCHAR(100),
  badge_released  VARCHAR(20),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------
-- RASTREABILIDADE DE MATERIAL
-- Fonte: RASTMAT.csv (Databook)
-- ------------------------------------------------------------
CREATE TABLE material_traceability (
  id              SERIAL PRIMARY KEY,
  project_id      INTEGER     NOT NULL REFERENCES projects(id),
  heat_number     VARCHAR(20) NOT NULL,
  nrir            VARCHAR(30),
  nrir_year       SMALLINT,
  supplier        VARCHAR(100),
  contract        VARCHAR(60),
  fiscal_note     VARCHAR(60),
  purchase_order  VARCHAR(60),
  project_code    VARCHAR(60),
  description     TEXT,
  diam_min_mm     SMALLINT,
  diam_max_mm     SMALLINT,
  certificate_num VARCHAR(30),
  inspection_result CHAR(1),  -- A=aprovado, R=reprovado
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(project_id, heat_number)
);

-- ------------------------------------------------------------
-- VÁLVULAS
-- Fonte: SGS-SGM_VALVULAS Excel (File 3)
-- ------------------------------------------------------------
CREATE TABLE valves (
  id                SERIAL PRIMARY KEY,
  project_id        INTEGER     NOT NULL REFERENCES projects(id),
  valve_id_raw      VARCHAR(100),
  description       TEXT,
  dn_mm             NUMERIC(8,2),
  unit_weight_kg    NUMERIC(10,4),
  qty_planned       NUMERIC(10,2) DEFAULT 0,
  qty_received      NUMERIC(10,2) DEFAULT 0,
  qty_reserved      NUMERIC(10,2) DEFAULT 0,
  qty_issued        NUMERIC(10,2) DEFAULT 0,
  weight_planned_kg NUMERIC(14,4) DEFAULT 0,
  weight_received_kg NUMERIC(14,4) DEFAULT 0,
  availability      VARCHAR(20),  -- AVAILABLE | PARTIAL | MISSING
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------
-- RESUMO HISTÓRICO (KPI por data/unidade)
-- Fonte: RESUMO.csv (Databook) — substituído por views em prod
-- Mantido para histórico e curva S
-- ------------------------------------------------------------
CREATE TABLE progress_snapshots (
  id          BIGSERIAL PRIMARY KEY,
  project_id  INTEGER     NOT NULL REFERENCES projects(id),
  snapshot_dt DATE        NOT NULL,
  unit_code   VARCHAR(10),
  area_code   VARCHAR(10),
  sop_code    VARCHAR(25),
  material    material_code,
  -- totais
  n_total     INTEGER DEFAULT 0,
  p_total     NUMERIC(14,2) DEFAULT 0,  -- peso total (kg)
  n_welded    INTEGER DEFAULT 0,
  n_released  INTEGER DEFAULT 0,
  n_hold      INTEGER DEFAULT 0,
  n_pending_mat INTEGER DEFAULT 0,
  n_cut       INTEGER DEFAULT 0,
  n_fitup     INTEGER DEFAULT 0,
  n_painted   INTEGER DEFAULT 0,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(project_id, snapshot_dt, unit_code, area_code, material)
);

CREATE INDEX idx_snapshot_date ON progress_snapshots(snapshot_dt);
CREATE INDEX idx_snapshot_unit ON progress_snapshots(unit_code);

-- ------------------------------------------------------------
-- UPLOAD BATCHES (controle de importações)
-- ------------------------------------------------------------
CREATE TABLE upload_batches (
  id            SERIAL PRIMARY KEY,
  project_id    INTEGER     NOT NULL REFERENCES projects(id),
  file_type     VARCHAR(20) NOT NULL, -- MTO|SGS|VALVULAS|JUNTAS|DATABOOK_*
  original_name VARCHAR(255) NOT NULL,
  rows_parsed   INTEGER,
  rows_inserted INTEGER,
  rows_updated  INTEGER,
  rows_errored  INTEGER,
  status        VARCHAR(20) NOT NULL DEFAULT 'PENDING',
  error_log     TEXT,
  started_at    TIMESTAMPTZ,
  completed_at  TIMESTAMPTZ,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------
-- USUÁRIOS
-- ------------------------------------------------------------
CREATE TABLE users (
  id            SERIAL PRIMARY KEY,
  project_id    INTEGER     REFERENCES projects(id),
  email         VARCHAR(255) NOT NULL UNIQUE,
  full_name     VARCHAR(255) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role          user_role   NOT NULL DEFAULT 'VIEWER',
  is_active     BOOLEAN     NOT NULL DEFAULT TRUE,
  last_login_at TIMESTAMPTZ,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------
-- AUDIT LOG
-- ------------------------------------------------------------
CREATE TABLE audit_log (
  id          BIGSERIAL PRIMARY KEY,
  user_id     INTEGER     REFERENCES users(id),
  table_name  VARCHAR(50) NOT NULL,
  record_id   BIGINT      NOT NULL,
  action      VARCHAR(10) NOT NULL CHECK (action IN ('INSERT','UPDATE','DELETE')),
  old_data    JSONB,
  new_data    JSONB,
  changed_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_table  ON audit_log(table_name, record_id);
CREATE INDEX idx_audit_when   ON audit_log(changed_at);

-- ------------------------------------------------------------
-- VIEWS — progresso consolidado por spool
-- ------------------------------------------------------------
CREATE MATERIALIZED VIEW mv_spool_progress AS
SELECT
  s.id,
  s.project_id,
  s.unit_id,
  s.spool_key,
  s.status,
  s.weight_kg,
  s.length_m,
  s.joints_total,
  s.joints_welded,
  s.joints_released,
  ROUND(
    CASE WHEN s.joints_total = 0 THEN 0
    ELSE s.joints_welded::NUMERIC / s.joints_total * 100
    END, 2
  ) AS pct_welded,
  ROUND(
    CASE WHEN s.joints_total = 0 THEN 0
    ELSE s.joints_released::NUMERIC / s.joints_total * 100
    END, 2
  ) AS pct_released,
  COUNT(j.id) AS joint_count_live,
  SUM(CASE WHEN j.status = '30_LIBERADA' THEN 1 ELSE 0 END) AS joints_lib_live
FROM spools s
LEFT JOIN joints j ON j.spool_id = s.id
GROUP BY s.id;

CREATE UNIQUE INDEX ON mv_spool_progress(id);

-- Atualizar após cada ETL:
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_spool_progress;
