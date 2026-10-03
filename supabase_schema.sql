-- ════════════════════════════════════════════════════════════
-- XAZURA SHOP — ПОЛНАЯ БАЗА С НУЛЯ (Supabase)
-- Supabase → SQL Editor → New query → вставь ВСЁ → Run.
-- Безопасно запускать повторно: существующие данные не удаляются.
-- В .env бота нужен ключ service_role (НЕ anon!).
-- ════════════════════════════════════════════════════════════

-- 1. ПОЛЬЗОВАТЕЛИ
CREATE TABLE IF NOT EXISTS users (
    user_id         BIGINT  PRIMARY KEY,
    username        TEXT    DEFAULT '',
    balance         FLOAT   NOT NULL DEFAULT 0,
    reg_date        TEXT    DEFAULT '',
    status          TEXT    DEFAULT 'Активен',        -- Активен | Заблокирован
    referrer_id     BIGINT  DEFAULT 0,
    purchases_count INT     DEFAULT 0,
    active_discount FLOAT   DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_users_username ON users (lower(username));

-- 2. ПОКУПКИ (logins = 'lolz:<id товара на Lolz>')
CREATE TABLE IF NOT EXISTS purchases (
    id               BIGSERIAL PRIMARY KEY,
    user_id          BIGINT,
    country_code     TEXT    DEFAULT '',              -- ключ из shop_countries.key
    phone_number     TEXT    DEFAULT '',
    logins           TEXT    DEFAULT '',
    password         TEXT    DEFAULT '',
    purchase_date    TEXT    DEFAULT '',
    guaranteed_until TEXT    DEFAULT '',
    status           TEXT    DEFAULT 'active',        -- active | refunded
    review_sent      INT     DEFAULT 0,
    price_paid       FLOAT   DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_purchases_user   ON purchases (user_id, status);
CREATE INDEX IF NOT EXISTS idx_purchases_logins ON purchases (logins);

-- 3. ПРОМОКОДЫ
CREATE TABLE IF NOT EXISTS promo_codes (
    code          TEXT PRIMARY KEY,
    discount      FLOAT   DEFAULT 0,
    max_uses      INT     DEFAULT 100,
    uses          INT     DEFAULT 0,
    active        INT     DEFAULT 1,
    type          TEXT    DEFAULT 'balance',          -- balance | discount
    country_code  TEXT,
    expires_at    TEXT,
    once_per_user INT     DEFAULT 1
);

-- 4. ИСПОЛЬЗОВАНИЯ ПРОМОКОДОВ (PK = один код на одного юзера, защита от двойного тапа)
CREATE TABLE IF NOT EXISTS promo_uses (
    code    TEXT,
    user_id BIGINT,
    used_at TEXT DEFAULT '',
    PRIMARY KEY (code, user_id)
);

-- 5. ОЖИДАЮЩИЕ ПЛАТЕЖИ (method: crypto | sbp — по нему фоновый контроллер знает, где проверять)
CREATE TABLE IF NOT EXISTS pending_payments (
    payment_id TEXT PRIMARY KEY,
    user_id    BIGINT,
    amount     FLOAT   DEFAULT 0,
    status     TEXT    DEFAULT 'pending',             -- pending | paid | timeout | canceled
    method     TEXT    DEFAULT '',
    created_at TEXT    DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_pending_status ON pending_payments (status);

-- 6. ИСТОРИЯ ПОПОЛНЕНИЙ
CREATE TABLE IF NOT EXISTS topup_history (
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT,
    amount     FLOAT DEFAULT 0,
    method     TEXT  DEFAULT '',
    created_at TEXT  DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_topup_user ON topup_history (user_id);

-- 7. ЗАЯВКИ НА ЗАМЕНУ
CREATE TABLE IF NOT EXISTS replacement_requests (
    id             BIGSERIAL PRIMARY KEY,
    user_id        BIGINT,
    purchase_id    BIGINT,
    account_number TEXT DEFAULT '',
    issue_text     TEXT DEFAULT '',
    issued_at      TEXT DEFAULT '',
    video_file_id  TEXT DEFAULT '',
    status         TEXT DEFAULT 'pending',            -- pending | approved | rejected
    created_at     TEXT DEFAULT '',
    resolved_at    TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_repl_purchase ON replacement_requests (purchase_id);
CREATE INDEX IF NOT EXISTS idx_repl_status   ON replacement_requests (status);

-- 8. НАСТРОЙКИ БОТА (ключ → значение)
CREATE TABLE IF NOT EXISTS bot_settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT ''
);

-- 9. ИСПОЛЬЗОВАННЫЕ КВИТАНЦИИ (PK = одна квитанция — один раз)
CREATE TABLE IF NOT EXISTS used_receipts (
    code    TEXT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    amount  FLOAT,
    used_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_used_receipts_user ON used_receipts (user_id);

-- 10. СТРАНЫ «ФИЗ. АККАУНТОВ»
CREATE TABLE IF NOT EXISTS shop_countries (
    key         TEXT PRIMARY KEY,                     -- хранится в purchases.country_code
    flag        TEXT NOT NULL DEFAULT '🌍',
    name        TEXT NOT NULL,
    iso         TEXT NOT NULL,                        -- ISO-код для Lolz (US, MM, ID ...)
    phone_code  TEXT NOT NULL DEFAULT '',
    sort_order  INT  NOT NULL DEFAULT 100,            -- меньше = выше в списке
    active      INT  NOT NULL DEFAULT 1               -- 1 показывать, 0 скрыть
);
CREATE INDEX IF NOT EXISTS idx_shop_countries_order ON shop_countries (active, sort_order);

-- ────────────────────────────────────────────────────────────
-- БЕЗОПАСНОСТЬ: включаем RLS без политик. Бот ходит с ключом service_role (он RLS обходит),
-- а чужой с anon-ключом не сможет ни прочитать, ни изменить баланс/покупки через REST API.
-- ────────────────────────────────────────────────────────────
ALTER TABLE users                ENABLE ROW LEVEL SECURITY;
ALTER TABLE purchases            ENABLE ROW LEVEL SECURITY;
ALTER TABLE promo_codes          ENABLE ROW LEVEL SECURITY;
ALTER TABLE promo_uses           ENABLE ROW LEVEL SECURITY;
ALTER TABLE pending_payments     ENABLE ROW LEVEL SECURITY;
ALTER TABLE topup_history        ENABLE ROW LEVEL SECURITY;
ALTER TABLE replacement_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE bot_settings         ENABLE ROW LEVEL SECURITY;
ALTER TABLE used_receipts        ENABLE ROW LEVEL SECURITY;
ALTER TABLE shop_countries       ENABLE ROW LEVEL SECURITY;

-- ────────────────────────────────────────────────────────────
-- НАЧАЛЬНЫЕ ДАННЫЕ
-- ────────────────────────────────────────────────────────────
INSERT INTO bot_settings (key, value) VALUES
    ('markup_percent',       '30'),                       -- наценка к цене Lolz, % (меняется в админке)
    ('lolz_origins',         'autoreg,self_registration'),  -- авторег + саморег; '' = без фильтра
    ('check_gov_ua_enabled', '0')                         -- квитанции выключены, пока не настроишь .env
ON CONFLICT (key) DO NOTHING;

INSERT INTO shop_countries (key, flag, name, iso, phone_code, sort_order) VALUES
  ('us', '🇺🇸', 'США', 'US', '+1', 10),
  ('mm', '🇲🇲', 'Мьянма', 'MM', '+95', 20),
  ('idn', '🇮🇩', 'Индонезия', 'ID', '+62', 30),
  ('ind', '🇮🇳', 'Индия', 'IN', '+91', 40),
  ('bd', '🇧🇩', 'Бангладеш', 'BD', '+880', 50),
  ('ph', '🇵🇭', 'Филиппины', 'PH', '+63', 60),
  ('vn', '🇻🇳', 'Вьетнам', 'VN', '+84', 70),
  ('br', '🇧🇷', 'Бразилия', 'BR', '+55', 80),
  ('pk', '🇵🇰', 'Пакистан', 'PK', '+92', 90),
  ('ng', '🇳🇬', 'Нигерия', 'NG', '+234', 100),
  ('eg', '🇪🇬', 'Египет', 'EG', '+20', 110),
  ('tr', '🇹🇷', 'Турция', 'TR', '+90', 120),
  ('kz', '🇰🇿', 'Казахстан', 'KZ', '+7', 130),
  ('uz', '🇺🇿', 'Узбекистан', 'UZ', '+998', 140),
  ('ca', '🇨🇦', 'Канада', 'CA', '+1', 150),
  ('mx', '🇲🇽', 'Мексика', 'MX', '+52', 160),
  ('co', '🇨🇴', 'Колумбия', 'CO', '+57', 170),
  ('ar', '🇦🇷', 'Аргентина', 'AR', '+54', 180),
  ('ke', '🇰🇪', 'Кения', 'KE', '+254', 190),
  ('th', '🇹🇭', 'Таиланд', 'TH', '+66', 200),
  ('my', '🇲🇾', 'Малайзия', 'MY', '+60', 210),
  ('kh', '🇰🇭', 'Камбоджа', 'KH', '+855', 220),
  ('np', '🇳🇵', 'Непал', 'NP', '+977', 230),
  ('et', '🇪🇹', 'Эфиопия', 'ET', '+251', 240),
  ('za', '🇿🇦', 'ЮАР', 'ZA', '+27', 250),
  ('pe', '🇵🇪', 'Перу', 'PE', '+51', 260),
  ('gb', '🇬🇧', 'Великобритания', 'GB', '+44', 270),
  ('de', '🇩🇪', 'Германия', 'DE', '+49', 280),
  ('ua', '🇺🇦', 'Украина', 'UA', '+380', 290),
  ('ru', '🇷🇺', 'Россия', 'RU', '+7', 300)
ON CONFLICT (key) DO NOTHING;

-- ════════════════════════════════════════════════════════════
-- Шпаргалка:
--   Скрыть страну:    UPDATE shop_countries SET active = 0 WHERE key = 'ru';
--   Поднять наверх:   UPDATE shop_countries SET sort_order = 1 WHERE key = 'mm';
--   Добавить страну:  INSERT INTO shop_countries (key, flag, name, iso, phone_code, sort_order)
--                     VALUES ('it', '🇮🇹', 'Италия', 'IT', '+39', 310);
--   Только авторег:   UPDATE bot_settings SET value = 'autoreg' WHERE key = 'lolz_origins';
--   Только саморег:   UPDATE bot_settings SET value = 'self_registration' WHERE key = 'lolz_origins';
-- Изменения подхватываются ботом в течение ~60 секунд.
-- ════════════════════════════════════════════════════════════

-- Если база уже создана со СТАРЫМ значением (self_registered) — можно поправить одной командой.
-- (Бот и без этого сам превращает self_registered → self_registration, но лучше держать данные чистыми.)
--   UPDATE bot_settings SET value = 'autoreg,self_registration' WHERE key = 'lolz_origins';
