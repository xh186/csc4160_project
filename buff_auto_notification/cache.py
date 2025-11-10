import os
import json
import requests
import hashlib
import shutil
from datetime import datetime, timedelta

class MarketCache:
    """
    A class to cache JSON data and related images from an API.
    Supports unified caching, loading, incremental backups, and cleanup.
    """

    def __init__(self, cache_dir='market_cache'):
        """
        Initializes the cache class, creating necessary directories.

        Args:
            cache_dir (str): The name of the main cache directory.
        """
        self.cache_dir = cache_dir
        self.json_dir = os.path.join(self.cache_dir, 'json')
        self.image_dir = os.path.join(self.cache_dir, 'images')
        # Backup directory removed per new design (history is embedded in each JSON)
        os.makedirs(self.json_dir, exist_ok=True)
        os.makedirs(self.image_dir, exist_ok=True)
        
        # These key sets should be adjusted based on the actual API response.
        self.static_keys = {
            'id', 'appid', 'game', 'name', 'market_hash_name',
            'steam_market_url', 'goods_info', 'short_name',
            'can_search_by_tournament', 'description'
        }
        self.dynamic_keys = {
            'sell_reference_price', 'sell_min_price', 'buy_max_price', 
            'sell_num', 'buy_num', 'transacted_num', 'quick_price', 
            'market_min_price', 'can_bargain', 'rent_unit_reference_price', 
            'rent_num', 'min_rent_unit_price', 'min_security_price', 
            'is_charm', 'keychain_color_img', 'auction_num', 
            'pre_sell_num', 'pre_sell_min_price', 'bookmarked',
            'has_buff_price_history'
        }

    def _get_filename(self, item: dict) -> str:
        """
        Generates a unique cache filename based on the item's ID or market_hash_name.
        
        Args:
            item (dict): The item's JSON data dictionary.

        Returns:
            str: The generated filename without the extension.
        """
        unique_id = item.get('id')
        if unique_id:
            return str(unique_id)
        
        market_hash_name = item.get('market_hash_name')
        if market_hash_name:
            return hashlib.md5(market_hash_name.encode('utf-8')).hexdigest()

        raise ValueError("Item has no 'id' or 'market_hash_name' for caching.")

    def _download_icon(self, item: dict, filename_base: str) -> bool:
        """
        Downloads the item's icon and saves it locally.
        
        Args:
            item (dict): The item data.
            filename_base (str): The base name for the image file (without extension).
        """
        icon_url = item.get('goods_info', {}).get('icon_url')
        if not icon_url:
            print(f"No icon URL for item '{item.get('name', 'N/A')}', skipping download.")
            return
            
        try:
            file_extension = os.path.splitext(icon_url.split('?')[0])[1] or '.jpg'
            filepath = os.path.join(self.image_dir, f'{filename_base}{file_extension}')
        except IndexError:
            filepath = os.path.join(self.image_dir, f'{filename_base}.jpg')
        
        if os.path.exists(filepath):
            return False
            
        try:
            response = requests.get(icon_url, stream=True, timeout=10)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Icon saved: {filepath}")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"Failed to download icon '{icon_url}': {e}")
            return False

    def upsert_cache(self, items: list):
        """
        A unified method to insert new data or update existing data in the cache.

        Args:
            items (list): A list of item dictionaries from the API response.
        """
        print("Starting cache processing...")
        last_icon_download_time = None
        icon_delay = getattr(self, 'icon_download_delay_seconds', 0) or 0
        for item in items:
            try:
                filename_base = self._get_filename(item)
                json_filepath = os.path.join(self.json_dir, f'{filename_base}.json')
                
                # Attempt icon download and respect delay between downloads in a single batch
                did_download = self._download_icon(item, filename_base)
                if did_download and icon_delay > 0:
                    # Enforce spacing between downloads
                    import time as _time
                    if last_icon_download_time is None:
                        last_icon_download_time = _time.time()
                    else:
                        elapsed = _time.time() - last_icon_download_time
                        if elapsed < icon_delay:
                            _time.sleep(icon_delay - elapsed)
                        last_icon_download_time = _time.time()

                # Build static and dynamic snapshot
                now_iso = datetime.now().isoformat()
                dynamic_snapshot = {key: item.get(key) for key in self.dynamic_keys if key in item}

                if os.path.exists(json_filepath):
                    # Load existing unified structure and append snapshot indexed by time
                    with open(json_filepath, 'r', encoding='utf-8') as f:
                        existing = json.load(f)

                    if not (isinstance(existing, dict) and isinstance(existing.get('static'), dict) and isinstance(existing.get('snapshots'), dict)):
                        # Non-unified structure detected; overwrite with unified format using current item only
                        static_part = {k: item.get(k) for k in self.static_keys if k in item}
                        existing = {'static': static_part, 'snapshots': {}}

                    existing['snapshots'][now_iso] = dynamic_snapshot

                    with open(json_filepath, 'w', encoding='utf-8') as f:
                        json.dump(existing, f, ensure_ascii=False, indent=4)
                    print(f"Appended snapshot to cache file: {json_filepath}")

                else:
                    # Create new structure with static at front and time-indexed dynamic snapshots
                    static_part = {k: item.get(k) for k in self.static_keys if k in item}
                    content = {
                        'static': static_part,
                        'snapshots': {
                            now_iso: dynamic_snapshot
                        }
                    }
                    with open(json_filepath, 'w', encoding='utf-8') as f:
                        json.dump(content, f, ensure_ascii=False, indent=4)
                    print(f"New JSON file saved: {json_filepath}")
            
            except ValueError as e:
                print(f"Skipping item due to error: {e}")
            except Exception as e:
                print(f"An unexpected error occurred while processing item '{item.get('name', 'N/A')}': {e}")
        
        print("Cache processing finished.")

    def load_cache(self, start_time: str = None, end_time: str = None, keys: list = None, limit: int = None, offset: int = 0) -> list:
        """
        Loads cached data, with options for filtering by time, keys, and pagination.
        
        Args:
            start_time (str, optional): ISO format start time for filtering.
            end_time (str, optional): ISO format end time for filtering.
            keys (list, optional): A list of item IDs or market_hash_names to load.
            limit (int, optional): The maximum number of items to return.
            offset (int, optional): The starting position for retrieving items.
        
        Returns:
            list: A list of loaded cache items.
        """
        loaded_items = []
        
        filenames_to_load = None
        if keys:
            filenames_to_load = set()
            for key in keys:
                # Try to convert to int for ID-based lookup
                try:
                    int_key = int(key)
                    filenames_to_load.add(str(int_key))
                except (ValueError, TypeError):
                    # If not a number, treat as market_hash_name
                    filenames_to_load.add(key)
        
        start_dt = datetime.fromisoformat(start_time) if start_time else None
        end_dt = datetime.fromisoformat(end_time) if end_time else None

        file_list = sorted(os.listdir(self.json_dir))
        count = 0
        items_found = 0

        for filename in file_list:
            if not filename.endswith('.json'):
                continue
            
            if filenames_to_load and os.path.splitext(filename)[0] not in filenames_to_load:
                continue

            filepath = os.path.join(self.json_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Only support unified structure during development
                    if not (isinstance(data, dict) and isinstance(data.get('static'), dict) and isinstance(data.get('snapshots'), dict)):
                        continue

                    snapshots = data.get('snapshots', {})
                    if not snapshots:
                        continue
                    # Choose latest snapshot by time within window
                    sorted_ts = sorted(snapshots.keys())
                    selected = None
                    for ts in reversed(sorted_ts):
                        try:
                            dt = datetime.fromisoformat(ts)
                        except Exception:
                            continue
                        if (start_dt and dt < start_dt) or (end_dt and dt > end_dt):
                            continue
                        selected = (ts, snapshots[ts])
                        break
                    if not selected:
                        continue
                    ts, snap = selected
                    merged = {**data.get('static', {}), **snap, 'cached_at': ts}
                    if count >= offset:
                        loaded_items.append(merged)
                        items_found += 1
                        if limit and items_found >= limit:
                            break
                    count += 1
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Warning: Could not load or parse file {filename}: {e}")
        
        return loaded_items