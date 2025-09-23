import webview
import threading
import time
import fetch_prices
import items
from lupa import LuaRuntime
import os

# Global window object to allow Python to call JavaScript functions
window = None

class Api:
    def __init__(self):
        self.selected_server_slug = None
        self.selected_realm_slug = None

    def get_item_price_history(self, item_id):
        if not self.selected_server_slug or not self.selected_realm_slug:
            print("Server and realm not selected.")
            return None
        
        return items.get_price_history_for_item(int(item_id))

    def get_server_list(self):
        return fetch_prices.get_server_realms()

    def set_server_and_realm(self, server_slug, realm_slug):
        self.selected_server_slug = server_slug
        self.selected_realm_slug = realm_slug
        print(f"Server set to: {server_slug}, Realm: {realm_slug}")
        
        print("Performing initial data fetch...")
        auction_data = fetch_prices.fetch_auction_data(server_slug, realm_slug)
        if auction_data:
            fetch_prices.process_and_save_data(auction_data, "Data.lua")
            combined_data = self._get_price_data(fetch_missing_items=False)
            if combined_data:
                window.evaluate_js(f'updateMasterData({combined_data})')
        else:
            print("Initial data fetch failed.")
        return True

    def fetch_and_update_item_details(self):
        print("User triggered fetch for all missing item details...")
        updated_data = self._get_price_data(fetch_missing_items=True)
        if updated_data:
            window.evaluate_js(f'updateMasterData({updated_data})')
        print("Item details fetch complete.")
        return True

    def search_item(self, item_name):
        if not (self.selected_server_slug and self.selected_realm_slug):
            print("Error: Server and realm not selected.")
            return []

        print(f"Performing search for item: {item_name}")
        auction_data = fetch_prices.search_item_auctions(self.selected_server_slug, self.selected_realm_slug, item_name)
        
        if auction_data:
            # Also save this search data to our history
            print(f"Saving price data for {len(auction_data)} found listings to history.")
            items.save_price_history(auction_data)

        if not auction_data:
            print("No results found for the search.")
            return []
        
        print(f"DEBUG: Found {len(auction_data)} auction listings from search. First result: {auction_data[0] if auction_data else 'N/A'}")

        # Process the search results to find min prices and gather item details
        min_prices = {}
        item_details_from_search = {}
        for auction in auction_data:
            if auction.get('unit_buyout_price') and auction['unit_buyout_price'] > 0 and auction.get('item'):
                item = auction['item']
                item_id = item['id']
                price_per_item = auction['unit_buyout_price']

                # Store the item details if we haven't seen this item yet
                if item_id not in item_details_from_search:
                    item_details_from_search[item_id] = item
                
                # Update the minimum price for this item
                if item_id in min_prices:
                    if price_per_item < min_prices[item_id]:
                        min_prices[item_id] = price_per_item
                else:
                    min_prices[item_id] = price_per_item
        
        if not min_prices:
            print("DEBUG: min_prices dictionary is empty after processing. No items with buyout found.")
            return []
        
        print(f"DEBUG: min_prices has {len(min_prices)} items. Example item_id: {next(iter(min_prices))}")

        # Now, combine the data. No need for a separate item details fetch.
        combined_data = []
        for item_id, price in min_prices.items():
            details = item_details_from_search.get(item_id, {})
            # Also save the newly found item details to our local DB for future use
            if details:
                items.save_item_to_db(details)

            combined_data.append({
                "id": item_id,
                "price": price,
                "name": details.get("name", "Unknown"),
                "quality": details.get("quality", 0),
                "icon": details.get("icon", "inv_misc_questionmark")
            })
        
        print(f"DEBUG: Returning {len(combined_data)} items to frontend. Example: {combined_data[0] if combined_data else 'N/A'}")
        return combined_data

    def _get_price_data(self, fetch_missing_items=False):
        if not os.path.exists("Data.lua"):
            return None
            
        lua = LuaRuntime()
        with open("Data.lua", "r", encoding="utf-8") as f:
            lua_code = f.read()
        
        lua.execute(lua_code)
        prices_table = lua.globals().MinEgenAddon_Prices
        prices_dict = {int(k): int(v) for k, v in prices_table.items()}
        
        item_ids = list(prices_dict.keys())
        item_details = items.get_item_details(item_ids, self.selected_server_slug, self.selected_realm_slug, fetch_missing=fetch_missing_items)
        
        combined_data = []
        for item_id, price in prices_dict.items():
            details = item_details.get(item_id, {})
            combined_data.append({
                "id": item_id,
                "price": price,
                "name": details.get("name", "Unknown"),
                "quality": details.get("quality", 0),
                "icon": details.get("icon", "inv_misc_questionmark")
            })
            
        return combined_data

def data_fetch_loop(api):
    while not (api.selected_server_slug and api.selected_realm_slug):
        time.sleep(1) 

    while True:
        print("Next background update in 20 minutes...")
        time.sleep(1200)

        if api.selected_server_slug and api.selected_realm_slug:
            print(f"Background Fetch: Fetching data for {api.selected_server_slug} - {api.selected_realm_slug}")
            auction_data = fetch_prices.fetch_auction_data(api.selected_server_slug, api.selected_realm_slug)
            if auction_data:
                # Save the raw scan data for historical analysis
                items.save_price_history(auction_data)
                
                # Continue with existing logic to update the addon file
                fetch_prices.process_and_save_data(auction_data, "Data.lua")
                updated_data = api._get_price_data(fetch_missing_items=False)
                if updated_data:
                    window.evaluate_js(f'updateMasterData({updated_data})')


if __name__ == '__main__':
    items.initialize_database()
    api = Api()
    
    data_thread = threading.Thread(target=data_fetch_loop, args=(api,))
    data_thread.daemon = True
    data_thread.start()

    window = webview.create_window('Auktioninator', 'web/main.html', js_api=api)
    webview.start(debug=True)
