import requests
import sqlite3
import os
import json

DB_FILE = "items.db"

def initialize_database():
    """Initializes the SQLite database and creates the items table if it doesn't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY,
            name TEXT,
            quality INTEGER,
            icon TEXT
        )
    """)
    conn.commit()
    conn.close()

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
    """Saves a single item to the local database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO items (id, name, quality, icon) VALUES (?, ?, ?, ?)",
                   (item_data['id'], item_data['name'], item_data['quality'], item_data['icon']))
    conn.commit()
    conn.close()

def fetch_items_from_api_bulk(item_ids, server_slug, realm_slug):
    """Fetches item details in bulk using the paginated endpoint with ID filters."""
    url = f"https://lotkeeper.net/api/v1/items/{server_slug}/{realm_slug}"
    all_items = {}
    
    # Batch item IDs to avoid creating URLs that are too long.
    batch_size = 100 # Keep batches reasonably small
    
    for i in range(0, len(item_ids), batch_size):
        batch_ids = item_ids[i:i+batch_size]
        
        # API filtering might expect a comma-separated string for multiple IDs.
        # Let's try the parameter name `item_ids` (plural).
        params = {'item_ids': ','.join(map(str, batch_ids))}
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            print(f"DEBUG: API response for item batch: {json.dumps(data)}")
            
            # The paginated endpoint returns a dictionary with a 'data' key
            for item in data.get('data', []):
                all_items[item['id']] = item
        
        except requests.exceptions.RequestException as e:
            print(f"Error fetching item batch from API: {e}")
            # Continue to the next batch
            
    return all_items

def get_item_details(item_ids, server_slug, realm_slug, fetch_missing=True):
    """
    Gets item details for a list of item IDs, checking the local DB first
    and falling back to the API if fetch_missing is True.
    """
    if not os.path.exists(DB_FILE):
        initialize_database()

    items_from_db = get_items_from_db(item_ids)
    
    missing_ids = [item_id for item_id in item_ids if item_id not in items_from_db]

    fetched_items = {}
    if missing_ids and fetch_missing:
        print(f"Fetching {len(missing_ids)} missing items from the API in batches...")
        fetched_items = fetch_items_from_api_bulk(missing_ids, server_slug, realm_slug)
        
        # Save the newly fetched items to the database
        for item_id, item_data in fetched_items.items():
            save_item_to_db(item_data)
    
    all_items = {**items_from_db, **fetched_items}
    
    # Ensure all requested IDs are in the final dictionary, even if fetching failed
    for item_id in item_ids:
        if item_id not in all_items:
            all_items[item_id] = {"id": item_id, "name": "Unknown Item", "quality": 0, "icon": "inv_misc_questionmark"}

    return all_items

if __name__ == '__main__':
    # Example usage
    initialize_database()
    # Replace with a valid server/realm/item_id for testing
    # test_item = get_item_details([34], 'project-epoch', 'kezan')
    # print(test_item)
