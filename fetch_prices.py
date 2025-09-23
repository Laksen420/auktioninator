import requests
import json
import time

def get_server_realms():
    """
    Fetches a list of available servers and realms from the Lotkeeper API.
    """
    url = "https://lotkeeper.net/api/v1/server-realms"
    print(f"Fetching server list from: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching server/realm list: {e}")
        return None

def select_server_and_realm(server_realms):
    """
    Prompts the user to select a server and realm from the list of available options.
    """
    if not server_realms:
        return None, None

    print("\nAvailable servers:")
    for i, server_info in enumerate(server_realms):
        print(f"  {i + 1}: {server_info['server']}")

    while True:
        try:
            choice = int(input(f"Select a server (1-{len(server_realms)}): "))
            if 1 <= choice <= len(server_realms):
                selected_server = server_realms[choice - 1]
                break
            else:
                print("Invalid choice. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")

    print("\nAvailable realms:")
    for i, realm_info in enumerate(selected_server['realms']):
        print(f"  {i + 1}: {realm_info['realm']}")
    
    while True:
        try:
            choice = int(input(f"Select a realm (1-{len(selected_server['realms'])}): "))
            if 1 <= choice <= len(selected_server['realms']):
                selected_realm = selected_server['realms'][choice - 1]
                break
            else:
                print("Invalid choice. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")
            
    return selected_server.get('server_slug'), selected_realm.get('realm_slug')

def fetch_auction_data(server_slug, realm_slug):
    """
    Fetches auction data from the Lotkeeper API for a given server and realm.
    """
    base_url = "https://lotkeeper.net/api/v1/auctions"
    url = f"{base_url}/{server_slug}/{realm_slug}/bulk"
    
    print(f"\nFetching data from: {url}")
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
        
        auction_data = response.json()
        
        print("Successfully fetched auction data.")
        print(f"Received {len(auction_data)} auction records from the API.")

        # For debugging, let's look at the first record if we got any
        if auction_data:
            import json
            print("Sample of first auction record:")
            print(json.dumps(auction_data[0], indent=2))

        return auction_data

    except requests.exceptions.HTTPError as errh:
        print(f"Http Error: {errh}")
    except requests.exceptions.RequestException as err:
        print(f"Oops: Something Else: {err}")
    
    return None

def process_and_save_data(auction_data, file_path):
    """
    Processes auction data to find the minimum buyout price per item and saves it to a Lua file.
    """
    print("Processing auction data...")
    min_prices = {}
    
    for auction in auction_data:
        # Ensure the auction has a buyout price and is for a valid item
        if auction.get('unit_buyout_price') and auction['unit_buyout_price'] > 0 and auction.get('item'):
            item_id = auction['item']['id']
            # The API already gives us price per item
            price_per_item = auction['unit_buyout_price']
            
            # If we've seen this item before, check if this is a new minimum price
            if item_id in min_prices:
                if price_per_item < min_prices[item_id]:
                    min_prices[item_id] = price_per_item
            else:
                # Otherwise, it's the first time we're seeing it
                min_prices[item_id] = price_per_item
    
    print(f"Found minimum prices for {len(min_prices)} unique items.")
    
    # Format the data as a Lua table
    lua_string = "MinEgenAddon_Prices = {\n"
    for item_id, price in min_prices.items():
        lua_string += f"  [{item_id}] = {price},\n"
    lua_string += "}\n"
    
    # Save the Lua file
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(lua_string)
        print(f"Successfully saved price data to {file_path}")
    except IOError as e:
        print(f"Error saving file: {e}")