import os
import sys
import time
import threading
import signal
from user import BuffAutoNotificationUser
from server import BuffAutoNotificationServer

def test_user_registration():
    try:
        user = BuffAutoNotificationUser("testuser", "testpass123", is_registration=True)
        print("✓ User registration successful")
        return user
    except ValueError as e:
        if "already exists" in str(e):
            print("✓ User already exists, skipping registration")
            return None
        else:
            print(f"✗ Registration failed: {e}")
            return None
    except Exception as e:
        print(f"✗ Registration error: {e}")
        return None

def test_user_login():
    try:
        user = BuffAutoNotificationUser("testuser", "testpass123", is_registration=False)
        print("✓ User login successful")
        return user
    except Exception as e:
        print(f"✗ Login failed: {e}")
        return None

def test_user_configuration(user):
    if not user:
        print("✗ No user instance for configuration")
        return False
    
    try:
        user.update_buff_cookies(f"session=<fill in>")
        print("✓ Buff cookies updated")
        
        user.edit_user_settings({
            # email here. Keep empty to activate debug mode.
            'check_frequency_minutes': 1
        })
        print("✓ User settings updated")
        
        watchlist_settings = {
            'conditions': [
                {
                    'condition_type': 'price_threshold',
                    'target_field': 'sell_min_price',
                    'operator': '<',
                    'value': 200
                }
            ]
        }
        
        user.edit_watchlist('add', '965545', watchlist_settings)
        print("✓ Watchlist item added")
        
        return True
    except Exception as e:
        print(f"✗ Configuration failed: {e}")
        return False

def test_server_start():
    try:
        server = BuffAutoNotificationServer()
        print("✓ Server initialized successfully")
        
        def run_server():
            server.start()
        
        server_thread = threading.Thread(target=run_server)
        server_thread.daemon = True
        server_thread.start()
        
        print("✓ Server started in background thread")
        print("✓ Monitoring is active (running for 30 seconds)")
        
        time.sleep(30)
        
        print("✓ Server test completed")
        return True
    except Exception as e:
        print(f"✗ Server start failed: {e}")
        return False

def cleanup_test_data():
    try:
        import shutil
        if os.path.exists("configs/testuser"):
            shutil.rmtree("configs/testuser")
            print("✓ Test data cleaned up")
    except Exception as e:
        print(f"Warning: Cleanup failed: {e}")

def main():
    print("Starting Buff Auto Notification System Test")
    print("=" * 50)
    
    try:
        print("\n1. Testing User Registration...")
        user = test_user_registration()
        
        print("\n2. Testing User Login...")
        if not user:
            user = test_user_login()
        
        print("\n3. Testing User Configuration...")
        config_success = test_user_configuration(user)
        
        print("\n4. Testing Server Start...")
        server_success = test_server_start()
        
        print("\n" + "=" * 50)
        print("Test Summary:")
        print(f"Registration: {'✓' if user else '✗'}")
        print(f"Login: {'✓' if user else '✗'}")
        print(f"Configuration: {'✓' if config_success else '✗'}")
        print(f"Server: {'✓' if server_success else '✗'}")
        
        if user and config_success and server_success:
            print("\n✓ All tests passed successfully!")
        else:
            print("\n✗ Some tests failed")
            
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
    finally:
        print("\nTest finished!!")
        # cleanup_test_data()

if __name__ == "__main__":
    main()
