PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS categories (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS products (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    unit         TEXT NOT NULL,
    category_id  INTEGER REFERENCES categories(id)
);

CREATE TABLE IF NOT EXISTS stock (
    product_id INTEGER NOT NULL REFERENCES products(id),
    location   TEXT NOT NULL CHECK(location IN ('warehouse', 'coffee_shop')),
    quantity   REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (product_id, location)
);

CREATE TABLE IF NOT EXISTS product_info (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    calories    REAL,
    protein     REAL,
    fat         REAL,
    carbs       REAL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS user_settings (
    telegram_user_id  INTEGER PRIMARY KEY,
    movement_direction TEXT NOT NULL DEFAULT 'warehouse_to_coffee'
        CHECK(movement_direction IN ('warehouse_to_coffee', 'coffee_to_warehouse'))
);

CREATE TABLE IF NOT EXISTS movement_log (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_user_id INTEGER NOT NULL,
    action_type      TEXT NOT NULL CHECK(action_type IN ('movement', 'inventory_adjust')),
    payload          TEXT NOT NULL,
    created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);
