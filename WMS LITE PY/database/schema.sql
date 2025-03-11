-- Database schema for WMS Lite

CREATE TABLE IF NOT EXISTS categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    category_id INTEGER,
    stock INTEGER DEFAULT 0,
    min_stock INTEGER DEFAULT 0,
    max_stock INTEGER,
    is_duplicate BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (category_id) REFERENCES categories (category_id)
);

-- Locations table
CREATE TABLE IF NOT EXISTS locations (
    location_id INTEGER PRIMARY KEY AUTOINCREMENT,
    zone TEXT NOT NULL,
    aisle TEXT NOT NULL,
    shelf TEXT NOT NULL,
    position TEXT NOT NULL,
    UNIQUE(zone, aisle, shelf, position)
);

-- Inventory table
CREATE TABLE IF NOT EXISTS inventory (
    inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    location_id INTEGER,
    quantity INTEGER DEFAULT 0,
    min_quantity INTEGER DEFAULT 0,
    max_quantity INTEGER,
    FOREIGN KEY (product_id) REFERENCES products (product_id),
    FOREIGN KEY (location_id) REFERENCES locations (location_id)
);

-- Process History table
CREATE TABLE IF NOT EXISTS process_history (
    process_id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_type TEXT NOT NULL,
    sub_operation TEXT NOT NULL,
    status TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    details TEXT,
    user_id TEXT
);

-- Order Types table
CREATE TABLE IF NOT EXISTS order_types (
    type_id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    requires_source_location BOOLEAN DEFAULT FALSE,
    requires_destination_location BOOLEAN DEFAULT FALSE,
    affects_stock BOOLEAN DEFAULT TRUE,
    allowed_source_zones TEXT,
    allowed_destination_zones TEXT
);

-- Orders table
CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_number TEXT UNIQUE NOT NULL,
    type_id INTEGER NOT NULL,
    source_location_id INTEGER,
    destination_location_id INTEGER,
    status TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (type_id) REFERENCES order_types (type_id),
    FOREIGN KEY (source_location_id) REFERENCES locations (location_id),
    FOREIGN KEY (destination_location_id) REFERENCES locations (location_id)
);

-- Order Items table
CREATE TABLE IF NOT EXISTS order_items (
    order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    product_id INTEGER,
    quantity INTEGER NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders (order_id),
    FOREIGN KEY (product_id) REFERENCES products (product_id)
);