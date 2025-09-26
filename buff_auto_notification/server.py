import os
import yaml
import time
import threading
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from typing import Dict, Any, List

from cache import MarketCache
from BuffApiPublic import BuffAccount

def evaluate_with_ai(prompt: str, data: Dict[str, Any]) -> bool:
    pass # Placeholder for AI evaluation logic

class BuffAutoNotificationServer:
    """Manages all user accounts and handles automated notifications."""

    def __init__(self):
        self.SERVER_CONFIG: Dict[str, Any] = self._load_server_config()
        # Prepare email server first so we can notify on startup issues
        self.email_server = self._setup_email_server()
        # Shared cache manager for all users
        shared_cache_dir = self.SERVER_CONFIG.get('shared_cache_dir', 'shared_market_cache')
        icon_delay = self.SERVER_CONFIG.get('server_settings', {}).get('icon_download_delay_seconds', 0)
        self.cache_manager = MarketCache(cache_dir=shared_cache_dir)
        # Attach delay to cache manager for icon throttling within single upsert calls
        setattr(self.cache_manager, 'icon_download_delay_seconds', icon_delay)
        self.users: Dict[str, Any] = self._load_all_users()

    def _load_server_config(self) -> Dict[str, Any]:
        try:
            with open('server_config.yaml', 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError("server_config.yaml not found. Please create it.")
        except Exception as e:
            raise Exception(f"Failed to load server_config.yaml: {e}")

    def _load_all_users(self) -> Dict[str, Any]:
        users: Dict[str, Any] = {}
        user_dir_base = self.SERVER_CONFIG.get('user_data_base_dir', 'configs')

        if not os.path.exists(user_dir_base):
            print("User data directory not found. Exiting.")
            return users

        for username in os.listdir(user_dir_base):
            user_path = os.path.join(user_dir_base, username)
            if not os.path.isdir(user_path):
                continue
            data_path = os.path.join(user_path, 'user_data.yaml')
            try:
                with open(data_path, 'r', encoding='utf-8') as f:
                    user_data = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Failed to read user_data.yaml for '{username}': {e}. Skipping.")
                continue

            cookies = (user_data or {}).get('buff_cookies', '')
            buff_client = None
            try:
                buff_client = BuffAccount(buffcookie=cookies)
            except Exception as e:
                # Notify user via email if configured; otherwise print for debug
                to_email = (user_data or {}).get('notification_settings', {}).get('email')
                subject = f"Buff Notification: Cookie invalid for user {username}"
                content = (
                    f"Your Buff cookies appear to be invalid.\n"
                    f"Server could not initialize BuffAccount for '{username}'.\n"
                    f"Error: {e}\n\n"
                    f"Please update your cookies in your user settings."
                )
                self._send_email(to_email, subject, content, debug_mode=not bool(to_email))
                # Abort server startup since a user's cookies are invalid
                raise RuntimeError(f"Failed to initialize BuffAccount for '{username}': {e}")

            # Lightweight server-side user holder
            users[username] = type('ServerUser', (), {
                'username': username,
                'user_data': user_data,
                'buff': buff_client,
                'cache_manager': self.cache_manager,
            })()

        print(f"Loaded {len(users)} user(s).")
        return users

    def _setup_email_server(self):
        email_config = self.SERVER_CONFIG.get('email_settings', {})
        if not email_config:
            print("Email settings not configured.")
            return None
        
        try:
            # Support optional auth code (e.g., 163 mail requires SMTP auth code)
            auth_code = email_config.get('auth_code', email_config.get('password'))
            server = smtplib.SMTP_SSL(email_config['host'], email_config['port'])
            server.login(email_config['user'], auth_code)
            return server
        except Exception as e:
            print(f"Failed to set up email server: {e}")
            return None

    def _send_email(self, to_email: str, subject: str, content: str, debug_mode: bool):
        if not to_email or debug_mode:
            print(f"--- Email Debug Log ---")
            print(f"Subject: {subject}")
            print(f"To: {to_email or 'N/A'}")
            print(f"Content:\n{content}")
            print(f"-----------------------")
            return
            
        if not self.email_server:
            print(f"Could not send email to {to_email}: email server not running.")
            return

        sender = self.SERVER_CONFIG['email_settings']['user']
        message = MIMEText(content, 'plain', 'utf-8')
        message['From'] = Header(sender, 'utf-8')
        message['To'] = Header(to_email, 'utf-8')
        message['Subject'] = Header(subject, 'utf-8')

        try:
            self.email_server.sendmail(sender, [to_email], message.as_string())
            print(f"Email sent to {to_email}.")
        except Exception as e:
            print(f"Failed to send email to {to_email}: {e}")

    def _check_user_watchlist(self, user_instance: Any):
        frequency = user_instance.user_data.get('notification_settings', {}).get('check_frequency_minutes', 30)
        # Delay between refreshing each wishlist item (seconds)
        api_call_delay = (
            self.SERVER_CONFIG.get('server_settings', {}).get('api_call_delay_seconds', 3)
        )
        print(f"Starting check thread for user {user_instance.username}. Frequency: {frequency} mins.")

        while True:
            watchlist = user_instance.user_data.get('watchlist', {})
            if not watchlist:
                print(f"User {user_instance.username} has no items in watchlist. Waiting...")
            else:
                for goods_id, item_settings in watchlist.items():
                    # Keys can be numeric id or market_hash_name. Try to coerce numeric ids.
                    key = None
                    try:
                        key = int(goods_id)
                    except Exception:
                        key = goods_id

                    cached_items = user_instance.cache_manager.load_cache(keys=[key])
                    
                    # Determine whether cache is stale
                    is_stale = True
                    if cached_items:
                        try:
                            from datetime import datetime
                            cached_ts = cached_items[0].get('cached_at')
                            if cached_ts:
                                cached_dt = datetime.fromisoformat(cached_ts)
                                from datetime import timedelta
                                is_stale = (datetime.now() - cached_dt) > timedelta(minutes=frequency)
                        except Exception:
                            is_stale = True

                    if (not cached_items) or is_stale:
                        print(f"Refreshing cache for item {goods_id}...")
                        if not getattr(user_instance, 'buff', None):
                            print(f"User {user_instance.username} has no valid Buff client; skipping refresh for {goods_id}.")
                            time.sleep(api_call_delay)
                            continue
                        # Determine game to search, prefer cached item's game if available
                        preferred_game = 'dota2'
                        if cached_items and cached_items[0].get('game'):
                            preferred_game = cached_items[0].get('game')

                        api_response = None
                        # Steps 1-3: market_hash_name -> short_name -> name
                        mh_name = short_name = human_name = None
                        if cached_items:
                            mh_name = cached_items[0].get('market_hash_name')
                            short_name = cached_items[0].get('short_name')
                            human_name = cached_items[0].get('name')

                        for search_key in [mh_name, short_name, human_name]:
                            if not search_key:
                                continue
                            api_response = user_instance.buff.search_goods_list(key=search_key, game_name=preferred_game)
                            if api_response:
                                break

                        # Step 4: use get_goods_info(goods_id) to resolve names, then retry 1-2
                        if (not api_response) and isinstance(key, int):
                            try:
                                info = user_instance.buff.get_goods_info(goods_id=str(goods_id), game_name=preferred_game)
                                resolved_mh = resolved_short = resolved_name = None
                                if info:
                                    goods_infos = info.get('goods_infos') or {}
                                    gi = goods_infos.get(str(goods_id)) if isinstance(goods_infos, dict) else None
                                    if gi:
                                        resolved_mh = gi.get('market_hash_name')
                                        resolved_name = gi.get('name')
                                    if not resolved_name and info.get('items'):
                                        first_item = info['items'][0]
                                        resolved_mh = resolved_mh or first_item.get('market_hash_name')
                                        resolved_short = first_item.get('short_name')
                                        resolved_name = resolved_name or first_item.get('name')
                                for search_key in [resolved_mh, resolved_short, resolved_name]:
                                    if not search_key:
                                        continue
                                    api_response = user_instance.buff.search_goods_list(key=search_key, game_name=preferred_game)
                                    if api_response:
                                        break
                            except Exception as e:
                                print(f"get_goods_info lookup failed for {goods_id}: {e}")

                        if api_response:
                            user_instance.cache_manager.upsert_cache(api_response)
                            cached_items = user_instance.cache_manager.load_cache(keys=[key])
                        else:
                            print(f"Failed to refresh cache for {goods_id}: unable to resolve a valid search key")
                            to_email = user_instance.user_data.get('notification_settings', {}).get('email')
                            subject = f"Buff Notification: Failed to refresh {goods_id}"
                            content = (
                                f"Could not resolve market_hash_name/short_name/name for goods_id={goods_id}.\n"
                                f"Please verify the watchlist entry and try again later."
                            )
                            self._send_email(to_email, subject, content, debug_mode=not bool(to_email))
                            continue
                    
                    if not cached_items: continue
                    cached_item = cached_items[0]

                    for condition in item_settings.get('conditions', []):
                        if self._evaluate_condition(condition, cached_item):
                            subject = f"🔔 Buff Notification: {cached_item['name']} Price Alert!"
                            content = self._generate_email_content(condition, cached_item)
                            
                            to_email = user_instance.user_data['notification_settings'].get('email')
                            self._send_email(to_email, subject, content, debug_mode=not to_email)
                            break

                    time.sleep(api_call_delay)

            time.sleep(frequency * 60)

    def _evaluate_condition(self, condition: Dict[str, Any], item_data: Dict[str, Any]) -> bool:
        condition_type = condition.get('condition_type')
        if condition_type == 'price_threshold':
            target_field = condition.get('target_field')
            operator = condition.get('operator')
            value = condition.get('value')
            current_value = float(item_data.get(target_field, 0))
            if operator == '<' and current_value < value:
                return True
            if operator == '>' and current_value > value:
                return True
        
        elif condition_type == 'price_change':
            pass

        elif condition_type == 'ai_evaluation':
            prompt = condition.get('prompt')
            ai_data = {
                "item_name": item_data.get('name'),
                "current_price": float(item_data.get('sell_min_price', 0))
            }
            return evaluate_with_ai(prompt, ai_data)
        
        return False
        
    def _generate_email_content(self, condition: Dict[str, Any], item_data: Dict[str, Any]) -> str:
        subject_lines: List[str] = []
        condition_type = condition.get('condition_type')
        
        if condition_type == 'price_threshold':
            subject_lines.append(f"The price of {item_data['name']} has dropped below your threshold.")
            subject_lines.append(f"Current Price: {item_data.get('sell_min_price')} | Threshold: {condition.get('value')}")
            
        elif condition_type == 'count_threshold':
            subject_lines.append(f"The on-sale quantity of {item_data['name']} has changed significantly.")
            subject_lines.append(f"Current Quantity: {item_data.get('sell_num')} | Threshold: {condition.get('value')}")

        elif condition_type == 'ai_evaluation':
            subject_lines.append(f"AI has detected an unusual trend for {item_data['name']}.")
            subject_lines.append(f"AI Prompt: {condition.get('prompt')}")
            
        return "\n".join(subject_lines)

    def start(self):
        print("Starting Buff Auto Notification Server.")
        for username, user_instance in self.users.items():
            thread = threading.Thread(target=self._check_user_watchlist, args=(user_instance,))
            thread.daemon = True
            thread.start()
            
        print("All user threads started. Server is running.")
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            print("Server is shutting down.")
            if self.email_server:
                self.email_server.quit()