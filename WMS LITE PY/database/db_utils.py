import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager
from queue import Queue
from threading import Lock

class DatabaseConnectionPool:
    _instance = None
    _lock = Lock()
    _pool = None
    _max_connections = 5

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DatabaseConnectionPool, cls).__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self._pool = Queue(maxsize=self._max_connections)
        for _ in range(self._max_connections):
            conn = self._create_connection()
            self._pool.put(conn)

    def _create_connection(self):
        conn = sqlite3.connect(get_db_path(), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def get_connection(self):
        try:
            if self._pool is None:
                raise sqlite3.Error("Connection pool is not initialized")
            conn = self._pool.get(timeout=5)  # Add timeout to prevent deadlock
            # Test connection before returning
            try:
                conn.execute('SELECT 1').fetchone()
                return conn
            except sqlite3.Error:
                # Connection is broken, create a new one
                try:
                    conn.close()
                except sqlite3.Error:
                    pass  # Ignore close errors
                conn = self._create_connection()
                return conn
        except Exception as e:
            raise sqlite3.Error(f"Failed to get database connection: {str(e)}")

    def return_connection(self, conn):
        if conn:
            try:
                # Always rollback any uncommitted changes
                conn.rollback()
                # Test connection before returning to pool
                try:
                    conn.execute('SELECT 1').fetchone()
                    if self._pool is not None:
                        self._pool.put(conn)
                    else:
                        conn.close()
                except sqlite3.Error:
                    try:
                        conn.close()
                    except sqlite3.Error:
                        pass  # Ignore close errors
                    if self._pool is not None:
                        self._pool.put(self._create_connection())
                    else:
                        raise sqlite3.Error("Connection pool is not initialized")
            except Exception as e:
                # If anything goes wrong, ensure we don't lose a pool slot
                try:
                    conn.close()
                except sqlite3.Error:
                    pass  # Ignore close errors
                # Check if pool exists before attempting to put new connection
                if self._pool is not None:
                    try:
                        self._pool.put(self._create_connection())
                    except Exception as e:
                        raise sqlite3.Error(f"Failed to replace broken connection: {str(e)}")
                else:
                    raise sqlite3.Error("Connection pool is not initialized")

def get_db_path():
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'wms.db')

def get_schema_path():
    return os.path.join(os.path.dirname(__file__), 'schema.sql')

@contextmanager
def get_db_connection():
    """Get a database connection using connection pool for better resource management"""
    pool = DatabaseConnectionPool()
    conn = None
    try:
        conn = pool.get_connection()
        yield conn
        try:
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            raise sqlite3.Error(f"Failed to commit transaction: {str(e)}")
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            pool.return_connection(conn)

def init_database():
    """Initialize the database with schema"""
    db_path = get_db_path()
    schema_path = get_schema_path()
    
    # Create database directory if it doesn't exist
    Path(os.path.dirname(db_path)).mkdir(parents=True, exist_ok=True)
    
    with get_db_connection() as conn:
        with open(schema_path, 'r') as schema_file:
            conn.executescript(schema_file.read())

# Database operation classes
class ProductDB:
    @staticmethod
    def add_category(name):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO categories (name) VALUES (?)',
                (name,)
            )
            return cursor.lastrowid
    
    @staticmethod
    def get_all_categories():
        with get_db_connection() as conn:
            return conn.execute('SELECT * FROM categories').fetchall()
    
    @staticmethod
    def delete_category(category_id):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Check if category has products
            products = cursor.execute('SELECT COUNT(*) FROM products WHERE category_id = ?', (category_id,)).fetchone()[0]
            if products > 0:
                return False
            cursor.execute('DELETE FROM categories WHERE category_id = ?', (category_id,))
            return True
    
    @staticmethod
    def add_product(sku, code, name, description, category_id, min_stock=0, max_stock=None, stock=0):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Check for existing SKU
            cursor.execute('SELECT COUNT(*) FROM products WHERE sku = ?', (sku,))
            sku_count = cursor.fetchone()[0]
            
            # If SKU exists, mark as duplicate
            is_duplicate = sku_count > 0
            
            cursor.execute(
                'INSERT INTO products (sku, code, name, description, category_id, min_stock, max_stock, stock, is_duplicate) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (sku, code, name, description, category_id, min_stock, max_stock, stock, is_duplicate)
            )
            return cursor.lastrowid, is_duplicate
    
    @staticmethod
    def get_all_products():
        with get_db_connection() as conn:
            return conn.execute(
                '''SELECT p.product_id, p.sku, p.code, p.name, p.description, 
                   p.min_stock, p.max_stock, p.stock, p.category_id, c.name as category_name 
                   FROM products p 
                   LEFT JOIN categories c ON p.category_id = c.category_id'''
            ).fetchall()

    @staticmethod
    def get_product_by_sku(sku):
        with get_db_connection() as conn:
            product = conn.execute(
                '''SELECT p.*, c.name as category
                   FROM products p
                   LEFT JOIN categories c ON p.category_id = c.category_id
                   WHERE p.sku = ?''',
                (sku,)
            ).fetchone()
            return dict(product) if product else None

    @staticmethod
    def update_stock(product_id, quantity_change):
        """Update product stock by adding or subtracting quantity"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Get current stock
            current_stock = cursor.execute(
                'SELECT stock FROM products WHERE product_id = ?',
                (product_id,)
            ).fetchone()
            
            if current_stock is None:
                raise ValueError(f"Product with ID {product_id} not found")
            
            # Calculate new stock
            new_stock = current_stock['stock'] + quantity_change
            
            # Update stock
            cursor.execute(
                'UPDATE products SET stock = ? WHERE product_id = ?',
                (new_stock, product_id)
            )
            return True

class ProcessHistoryDB:
    @staticmethod
    def log_process(operation_type, sub_operation, status, details=None, user_id=None):
        """Log a process completion to the process_history table"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO process_history (operation_type, sub_operation, status, details, user_id) VALUES (?, ?, ?, ?, ?)',
                (operation_type, sub_operation, status, details, user_id)
            )
            return cursor.lastrowid
    
    @staticmethod
    def get_process_history(limit=None):
        """Get process history records, optionally limited to a specific number"""
        with get_db_connection() as conn:
            if limit:
                history = conn.execute(
                    'SELECT * FROM process_history ORDER BY timestamp DESC LIMIT ?',
                    (limit,)
                ).fetchall()
            else:
                history = conn.execute(
                    'SELECT * FROM process_history ORDER BY timestamp DESC'
                ).fetchall()
            return [dict(record) for record in history]

class InventoryDB:
    @staticmethod
    def add_inventory(product_id, location_id, quantity, min_quantity=0, max_quantity=None):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO inventory (product_id, location_id, quantity, min_quantity, max_quantity) VALUES (?, ?, ?, ?, ?)',
                (product_id, location_id, quantity, min_quantity, max_quantity)
            )
            inventory_id = cursor.lastrowid
            return inventory_id
    
    @staticmethod
    def get_inventory_levels():
        with get_db_connection() as conn:
            inventory = conn.execute(
                '''SELECT i.*, p.name as product_name, p.sku, 
                   l.zone, l.aisle, l.shelf, l.position
                   FROM inventory i
                   JOIN products p ON i.product_id = p.product_id
                   JOIN locations l ON i.location_id = l.location_id'''
            ).fetchall()
            return inventory

class LocationDB:
    @staticmethod
    def add_location(zone, aisle, shelf, position):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO locations (zone, aisle, shelf, position) VALUES (?, ?, ?, ?)',
                (zone, aisle, shelf, position)
            )
            location_id = cursor.lastrowid
            return location_id
    
    @staticmethod
    def get_all_locations():
        with get_db_connection() as conn:
            locations = conn.execute('SELECT * FROM locations').fetchall()
            return locations

    @staticmethod
    def update_location(location_id, zone, aisle, shelf, position):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE locations SET zone = ?, aisle = ?, shelf = ?, position = ? WHERE location_id = ?',
                (zone, aisle, shelf, position, location_id)
            )
            return cursor.rowcount > 0

    @staticmethod
    def delete_location(location_id):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM locations WHERE location_id = ?', (location_id,))
            return cursor.rowcount > 0

    @staticmethod
    def duplicate_location(location_id):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Get the location to duplicate
            location = cursor.execute('SELECT zone, aisle, shelf, position FROM locations WHERE location_id = ?', (location_id,)).fetchone()
            if location:
                # Insert the duplicate
                cursor.execute(
                    'INSERT INTO locations (zone, aisle, shelf, position) VALUES (?, ?, ?, ?)',
                    location
                )
                new_id = cursor.lastrowid
                return new_id
            return None

    @staticmethod
    def clear_all_locations():
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM locations')

class OrderDB:
    @staticmethod
    def add_order_type(code, name, description, requires_source_location=False, requires_destination_location=False, affects_stock=True, allowed_source_zones=None, allowed_destination_zones=None):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO order_types (code, name, description, requires_source_location, requires_destination_location, affects_stock, allowed_source_zones, allowed_destination_zones) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (code, name, description, requires_source_location, requires_destination_location, affects_stock, allowed_source_zones, allowed_destination_zones)
            )
            type_id = cursor.lastrowid
            return type_id

    @staticmethod
    def get_all_order_types():
        with get_db_connection() as conn:
            order_types = conn.execute('SELECT * FROM order_types').fetchall()
            return order_types

    @staticmethod
    def create_order(order_number, type_id, source_location_id=None, destination_location_id=None, status='pending'):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO orders (order_number, type_id, source_location_id, destination_location_id, status) VALUES (?, ?, ?, ?, ?)',
                (order_number, type_id, source_location_id, destination_location_id, status)
            )
            return cursor.lastrowid
    
    @staticmethod
    def get_all_orders():
        with get_db_connection() as conn:
            orders = conn.execute(
                '''SELECT o.*, ot.name as type_name, ot.code as type_code,
                   sl.zone as source_zone, sl.aisle as source_aisle, sl.shelf as source_shelf, sl.position as source_position,
                   dl.zone as dest_zone, dl.aisle as dest_aisle, dl.shelf as dest_shelf, dl.position as dest_position,
                   COUNT(oi.order_item_id) as item_count
                   FROM orders o
                   LEFT JOIN order_types ot ON o.type_id = ot.type_id
                   LEFT JOIN locations sl ON o.source_location_id = sl.location_id
                   LEFT JOIN locations dl ON o.destination_location_id = dl.location_id
                   LEFT JOIN order_items oi ON o.order_id = oi.order_id
                   GROUP BY o.order_id'''
            ).fetchall()
            return [dict(order) for order in orders]

    @staticmethod
    def get_order_by_id(order_id):
        with get_db_connection() as conn:
            order = conn.execute(
                '''SELECT o.*, ot.name as type_name, ot.code as type_code,
                   sl.zone as source_zone, sl.aisle as source_aisle, sl.shelf as source_shelf, sl.position as source_position,
                   dl.zone as dest_zone, dl.aisle as dest_aisle, dl.shelf as dest_shelf, dl.position as dest_position
                   FROM orders o
                   LEFT JOIN order_types ot ON o.type_id = ot.type_id
                   LEFT JOIN locations sl ON o.source_location_id = sl.location_id
                   LEFT JOIN locations dl ON o.destination_location_id = dl.location_id
                   WHERE o.order_id = ?''',
                (order_id,)
            ).fetchone()
            return dict(order) if order else None

    @staticmethod
    def add_order_items(order_id, items):
        """Add items to an order with proper error handling"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            try:
                for item in items:
                    cursor.execute(
                        'INSERT INTO order_items (order_id, product_id, quantity) VALUES (?, ?, ?)',
                        (order_id, item['product_id'], item['quantity'])
                    )
                return True
            except sqlite3.Error as e:
                raise sqlite3.Error(f"Failed to add order items: {str(e)}")

    @staticmethod
    def update_order_status(order_id, new_status):
        """Update order status with validation"""
        valid_statuses = ['pending', 'in_progress', 'completed', 'cancelled']
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    'UPDATE orders SET status = ? WHERE order_id = ?',
                    (new_status, order_id)
                )
                if cursor.rowcount == 0:
                    raise ValueError(f"Order with ID {order_id} not found")
                return True
            except sqlite3.Error as e:
                raise sqlite3.Error(f"Failed to update order status: {str(e)}")

    @staticmethod
    def get_order_items(order_id):
        """Get all items for a specific order with product details"""
        with get_db_connection() as conn:
            try:
                items = conn.execute(
                    '''SELECT oi.*, p.name as product_name, p.sku, p.code
                       FROM order_items oi
                       JOIN products p ON oi.product_id = p.product_id
                       WHERE oi.order_id = ?''',
                    (order_id,)
                ).fetchall()
                return [dict(item) for item in items]
            except sqlite3.Error as e:
                raise sqlite3.Error(f"Failed to get order items: {str(e)}")

    @staticmethod
    def delete_order(order_id):
        """Delete an order and its items with proper cascading"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            try:
                # First delete order items
                cursor.execute('DELETE FROM order_items WHERE order_id = ?', (order_id,))
                # Then delete the order
                cursor.execute('DELETE FROM orders WHERE order_id = ?', (order_id,))
                if cursor.rowcount == 0:
                    raise ValueError(f"Order with ID {order_id} not found")
                return True
            except sqlite3.Error as e:
                raise sqlite3.Error(f"Failed to delete order: {str(e)}")