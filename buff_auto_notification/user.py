import os
import yaml
import hashlib
from typing import Dict, Any

from BuffApiPublic import BuffAccount
from cache import MarketCache

class BuffAutoNotificationUser:
    """Manages a single user's Buff market notification system.
    
    This class handles user authentication (login, registration, password management),
    and personal data management (cookies, watchlist). It integrates with a shared
    market cache and the Buff API to perform user-specific actions.
    """
    
    _SERVER_CONFIG: Dict[str, Any] = {}
    _SHARED_CACHE_MANAGER: MarketCache = None
    
    def __init__(self, username: str, password: str, is_registration: bool = False):
        """
        Initializes the user instance and handles login or registration.

        Args:
            username: The user's unique identifier.
            password: The user's password.
            is_registration: Set to True for new user registration.

        Raises:
            ValueError: For incorrect passwords or when a user already exists during registration.
            FileNotFoundError: When a user doesn't exist during login.
        """
        self._load_server_config()
        self._initialize_shared_cache()
        
        self.username = username
        self.user_dir = os.path.join(self._SERVER_CONFIG['user_data_base_dir'], self.username)
        self.config_path = os.path.join(self.user_dir, 'user_data.yaml')
        
        if is_registration:
            self._handle_registration(password)
        else:
            self._handle_login(password)
        
        cookies = self.user_data.get('buff_cookies', '')

        try:
            self.buff = BuffAccount(buffcookie=cookies)
        except Exception as e:
            raise ValueError(f"Failed to initialize BuffAccount. The provided cookies may be invalid or expired. Please update them. Original error: {e}")
        self.cache_manager = self._SHARED_CACHE_MANAGER

    def _load_server_config(self):
        """Loads server configuration from a YAML file if not already loaded."""
        if not self._SERVER_CONFIG:
            try:
                with open('server_config.yaml', 'r') as f:
                    self._SERVER_CONFIG = yaml.safe_load(f)
            except FileNotFoundError:
                raise FileNotFoundError("server_config.yaml not found. Please create it.")
    
    def _initialize_shared_cache(self):
        """Initializes the shared cache manager as a singleton if not already done."""
        if not self._SHARED_CACHE_MANAGER:
            cache_dir = self._SERVER_CONFIG.get('shared_cache_dir', 'shared_market_cache')
            self._SHARED_CACHE_MANAGER = MarketCache(cache_dir=cache_dir)
            
    def _handle_registration(self, password: str):
        """Handles the registration process for a new user."""
        if os.path.exists(self.config_path):
            print(f"User '{self.username}' already exists. Please log in instead.")
            raise ValueError("User already exists.")
        
        os.makedirs(self.user_dir, exist_ok=True)
        default_data = {
            'password_hash': self._hash_password(password),
            'buff_cookies': '',
            'notification_settings': {
                'email': None,
                'check_frequency_minutes': 30
            },
            'watchlist': {}
        }
        self.user_data = default_data
        self._save_user_data()
        print(f"User '{self.username}' registered successfully.")

    def _handle_login(self, password: str):
        """Handles the login process for an existing user."""
        if not os.path.exists(self.config_path):
            print(f"User '{self.username}' not found. Please register first.")
            raise FileNotFoundError("User not found.")
        
        self.user_data = self._load_user_data()
        if not self._verify_password(password):
            raise ValueError("Incorrect password.")
        print(f"User '{self.username}' logged in successfully.")

    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    def _verify_password(self, password: str) -> bool:
        """Verifies a password against the stored hash."""
        stored_hash = self.user_data.get('password_hash')
        return stored_hash and self._hash_password(password) == stored_hash

    def _load_user_data(self) -> Dict[str, Any]:
        """Loads user data from the YAML file."""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _save_user_data(self):
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.user_data, f, sort_keys=False)

    def change_password(self, old_password: str, new_password: str):
        if not self._verify_password(old_password):
            raise ValueError("Incorrect old password.")
        self.user_data['password_hash'] = self._hash_password(new_password)
        self._save_user_data()
        print("Password successfully changed.")

    def reset_password(self, new_password: str):
        """Resets the user's password without old password verification."""
        self.user_data['password_hash'] = self._hash_password(new_password)
        self._save_user_data()
        print("Password successfully reset.")
    
    def update_buff_cookies(self, cookies: str):
        """Updates the user's Buff account cookies."""
        self.user_data['buff_cookies'] = cookies
        self._save_user_data()
        print("Buff cookies updated.")

    def edit_user_settings(self, settings: Dict[str, Any]):
        """Updates and saves user notification settings."""
        self.user_data['notification_settings'].update(settings)
        self._save_user_data()

    def search_and_cache(self, keyword: str, game: str):
        """
        Searches for items and updates the shared cache.
        Returns the API response.
        """
        # Use market search by name; server refresh uses market_hash_name for consistency
        res = self.buff.search_goods_list(key=keyword, game_name=game)
        if res:
            self._SHARED_CACHE_MANAGER.upsert_cache(res)
        return res

    def edit_watchlist(self, operation: str, goods_id: str, settings: Dict[str, Any] = None):
        """
        Manages the user's watchlist.

        Args:
            operation: 'add', 'remove', or 'update'.
            goods_id: Unique ID of the item.
            settings: Notification triggers for the item, used for 'add' or 'update' operations..
        """
        if operation == 'add' or operation == 'update':
            if not settings:
                raise ValueError("Settings must be provided for 'add' or 'update' operations.")
            self.user_data['watchlist'][goods_id] = settings
        elif operation == 'remove':
            self.user_data['watchlist'].pop(goods_id, None)
        self._save_user_data()