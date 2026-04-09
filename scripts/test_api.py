#!/usr/bin/env python3
"""
Quick test to verify Decodo API credentials work.
Run this first to debug any authentication issues.
"""

import os
import requests
import json

DECODO_API_URL = "https://scraper-api.decodo.com/v2/scrape"
TEST_URL = "https://ip.decodo.com"  # Simple test endpoint from Decodo docs

def main():
    token = os.environ.get("DECODO_API_TOKEN")
    
    if not token:
        print("ERROR: DECODO_API_TOKEN environment variable not set")
        return
    
    print(f"Token found (length: {len(token)} characters)")
    print(f"Token preview: {token[:10]}...{token[-10:]}")
    print(f"\nTesting API with: {TEST_URL}")
    
    headers = {
        "Accept": "application/json",
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "url": TEST_URL,
    }
    
    print(f"\nRequest headers: {json.dumps({k: v if k != 'Authorization' else 'Basic ***' for k, v in headers.items()}, indent=2)}")
    print(f"Request payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            DECODO_API_URL,
            headers=headers,
            json=payload,
            timeout=60
        )
        
        print(f"\nResponse status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.ok:
            data = response.json()
            print(f"\n✅ SUCCESS! API is working.")
            print(f"Response preview:\n{json.dumps(data, indent=2)[:1000]}")
        else:
            print(f"\n❌ FAILED with status {response.status_code}")
            print(f"Response body:\n{response.text[:1000]}")
            
    except Exception as e:
        print(f"\n❌ Exception: {e}")

if __name__ == "__main__":
    main()
