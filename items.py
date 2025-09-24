import requests
import sqlite3
import os
import json
from datetime import datetime

DB_FILE = "items.db"

def get_db_connection():
    """Returns a connection to the SQLite database."""
    return sqlite3.connect(DB_FILE)

def initialize_database():
    """Initializes the database and creates tables if they don't exist."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Main item details table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY,
                name TEXT,
                link TEXT,
                icon TEXT,
                level INTEGER,
                quality INTEGER,
                max_stack_size INTEGER,
                vendor_price INTEGER,
                class_index INTEGER,
                class_name TEXT
            )
        """)

        # --- Start of Schema Migration ---
        
        # Get existing columns from the 'items' table
        cursor.execute("PRAGMA table_info(items)")
        existing_columns = {info[1] for info in cursor.fetchall()}

        # Define the complete, expected schema for the 'items' table
        expected_schema = {
            'id': 'INTEGER',
            'name': 'TEXT',
            'link': 'TEXT',
            'icon': 'TEXT',
            'level': 'INTEGER',
            'quality': 'INTEGER',
            'max_stack_size': 'INTEGER',
            'vendor_price': 'INTEGER',
            'class_index': 'INTEGER',
            'class_name': 'TEXT'
        }

        # Add any missing columns
        for column_name, column_type in expected_schema.items():
            if column_name not in existing_columns:
                print(f"Adding '{column_name}' column to 'items' table for schema migration.")
                # We can't add a PRIMARY KEY to an existing table this way, and 'id' should always exist.
                if column_name == 'id':
                    continue
                cursor.execute(f"ALTER TABLE items ADD COLUMN {column_name} {column_type}")
        
        # --- End of Schema Migration ---

        # Price history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                item_id INTEGER,
                timestamp DATETIME,
                min_buyout_price INTEGER,
                avg_buyout_price INTEGER,
                total_quantity INTEGER,
                FOREIGN KEY(item_id) REFERENCES items(id)
            )
        """)
        # Create an index for faster lookups
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_history_item_id ON price_history (item_id)")
        conn.commit()

def get_item_from_db(item_id):
    """Retrieves a single item from the local database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, quality, icon FROM items WHERE id = ?", (item_id,))
    item = cursor.fetchone()
    conn.close()
    if item:
        return {"id": item[0], "name": item[1], "quality": item[2], "icon": item[3]}
    return None

def get_items_from_db(item_ids):
    """Retrieves multiple items from the local database."""
    if not item_ids:
        return {}
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    query = f"SELECT id, name, quality, icon FROM items WHERE id IN ({','.join('?' for _ in item_ids)})"
    cursor.execute(query, item_ids)
    items = cursor.fetchall()
    conn.close()
    return {item[0]: {"id": item[0], "name": item[1], "quality": item[2], "icon": item[3]} for item in items}


def save_item_to_db(item_data):
    """Saves a single item's details to the database, ignoring if it already exists."""
    sql = """
        INSERT OR IGNORE INTO items 
        (id, name, link, icon, level, quality, max_stack_size, vendor_price, class_index, class_name) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (
        item_data.get('id'), item_data.get('name'), item_data.get('link'),
        item_data.get('icon'), item_data.get('level'), item_data.get('quality'),
        item_data.get('max_stack_size'), item_data.get('vendor_price'),
        item_data.get('class_index'), item_data.get('class_name')
    )
    with get_db_connection() as conn:
        conn.cursor().execute(sql, params)
        conn.commit()

def save_price_history(auction_data):
    """Processes and saves the minimum and average prices for each item from a scan."""
    if not auction_data:
        return

    price_data = {}
    for auction in auction_data:
        if auction.get('unit_buyout_price') and auction['unit_buyout_price'] > 0 and auction.get('item'):
            item_id = auction['item']['id']
            price = auction['unit_buyout_price']
            quantity = auction.get('quantity', 0)

            if item_id not in price_data:
                price_data[item_id] = {'prices': [], 'quantity': 0}
            
            price_data[item_id]['prices'].append(price)
            price_data[item_id]['quantity'] += quantity

    history_records = []
    scan_time = datetime.utcnow()
    for item_id, data in price_data.items():
        prices = data['prices']
        record = (
            item_id,
            scan_time,
            min(prices),
            sum(prices) // len(prices),
            data['quantity']
        )
        history_records.append(record)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT INTO price_history (item_id, timestamp, min_buyout_price, avg_buyout_price, total_quantity)
            VALUES (?, ?, ?, ?, ?)
        """, history_records)
        conn.commit()
    print(f"Saved price history for {len(history_records)} items.")

def get_price_history_for_item(item_id):
    """Retrieves the price history for a specific item from the local database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp, min_buyout_price FROM price_history
            WHERE item_id = ?
            ORDER BY timestamp
        """, (item_id,))
        
        return [{"timestamp": row[0], "min_buyout_price": row[1]} for row in cursor.fetchall()]

def get_quantity_history_for_item(item_id):
    """Retrieves the quantity history for a specific item from the local database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp, total_quantity FROM price_history
            WHERE item_id = ?
            ORDER BY timestamp
        """, (item_id,))
        
        return [{"timestamp": row[0], "total_quantity": row[1]} for row in cursor.fetchall()]

def fetch_items_from_api_bulk(item_ids, server_slug, realm_slug):
    """Fetches item details in bulk using the paginated endpoint with ID filters."""
    if not item_ids:
        return {}

    base_url = f"https://lotkeeper.net/api/v1/items/{server_slug}/{realm_slug}"
    all_fetched_items = {}
    
    # Split item_ids into chunks to avoid creating a URL that is too long
    chunk_size = 100 
    item_id_chunks = [item_ids[i:i + chunk_size] for i in range(0, len(item_ids), chunk_size)]
    
    for chunk in item_id_chunks:
        params = [('id', item_id) for item_id in chunk]
        
        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            fetched_data = response.json()
            
            # The endpoint is paginated, we get a dict with 'data'
            for item in fetched_data.get('data', []):
                item_id = item['id']
                all_fetched_items[item_id] = item
                save_item_to_db(item) # Save new items to DB for future use
                
            print(f"Successfully fetched details for {len(chunk)} items from API.")

        except requests.exceptions.HTTPError as errh:
            print(f"Http Error during bulk item fetch: {errh}")
        except requests.exceptions.RequestException as err:
            print(f"Request Error during bulk item fetch: {err}")
    
    return all_fetched_items

def get_item_details(item_ids, server, realm, fetch_missing=False):
    """
    Retrieves details for a list of item IDs from the local database.
    If fetch_missing is True, it fetches any missing item details from the API.
    """
    if not item_ids:
        return {}

    details = {}
    ids_to_fetch = []
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Create a placeholder string for the query
        placeholders = ','.join('?' for _ in item_ids)
        cursor.execute(f"SELECT id, name, quality, icon FROM items WHERE id IN ({placeholders})", item_ids)
        
        for row in cursor.fetchall():
            details[row[0]] = {"id": row[0], "name": row[1], "quality": row[2], "icon": row[3]}

    # Check which items were not found in the DB
    for item_id in item_ids:
        if item_id not in details:
            ids_to_fetch.append(item_id)

    if fetch_missing and ids_to_fetch:
        print(f"Fetching details for {len(ids_to_fetch)} missing items from API...")
        fetched_details = fetch_items_from_api_bulk(ids_to_fetch, server, realm)
        if fetched_details:
            details.update(fetched_details)
            # No need to save here, as the search function already does that
            
    return details

if __name__ == '__main__':
    # Example usage
    initialize_database()
    # Replace with a valid server/realm/item_id for testing
    # test_item = get_item_details([34], 'project-epoch', 'kezan')
    # print(test_item)
