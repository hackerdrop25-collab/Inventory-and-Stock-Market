from datetime import datetime
import json
import requests

def verify_security_api():
    print("Verifying Security & Global Market APIs...")
    
    BASE_URL = "http://127.0.0.1:5000"
    
    # Mock authentication or bypass if possible for test
    # Since we are running in the user's environment, we might need a session.
    # For simplicity, we can test the internal logic directly if we import app.
    
    try:
        from app import app, firewall_logs
        with app.test_request_context():
            # 1. Test Security Status API logic
            print("\n[1/2] Testing /api/security/status internal logic...")
            from app import api_security_status
            from flask import session
            session['user'] = 'admin@example.com' # Mock session
            
            response = api_security_status()
            data = json.loads(response.get_data(as_text=True))
            print(f"Result: {data}")
            assert 'status' in data
            assert 'failed_attempts_1h' in data
            
            # 2. Test Realtime Updates (Global Market)
            print("\n[2/2] Testing /api/realtime-updates global market pulse...")
            from app import api_realtime_updates
            response = api_realtime_updates()
            data = json.loads(response.get_data(as_text=True))
            if 'global_market' in data:
                 print(f"Success: Found {len(data['global_market'])} global icons.")
                 for item in data['global_market'][:3]:
                     print(f" - {item['name']}: {item['price']}")
            else:
                 print("Error: global_market missing from response")
                 
    except Exception as e:
        print(f"Verification Failed: {e}")

if __name__ == "__main__":
    verify_security_api()
