#!/usr/bin/env python3
"""
Test script for unified messaging API - 3 test cases
"""

import requests
import json

BASE_URL = "http://localhost:5002"

def test_slack_only():
    """Test 1: Send to Slack only"""
    print("🔵 Test 1: Slack Only")
    
    payload = {
        "channel": "#payroll-data-insights",
        "text": "🚀 Test message to Slack only - LLM Q&A system is working great!",
        "images": ["egimage.png"]
    }
    
    response = requests.post(f"{BASE_URL}/send-slack", json=payload)
    result = response.json()
    
    print(f"Status: {response.status_code}")
    print(f"Result: {result}")
    print("=" * 50)

def test_email_only():
    """Test 2: Send to Email only"""
    print("📧 Test 2: Email Only")
    
    payload = {
        "recipient_email": "g01dman.sachks@gmail.com",
        "subject": "Test Email - Dataset Analysis",
        "body": "📊 Test email - Dataset analysis completed successfully with pure LLM reasoning!",
        "images": ["photo.jpg"]
    }
    
    response = requests.post(f"{BASE_URL}/send-email", json=payload)
    result = response.json()
    
    print(f"Status: {response.status_code}")
    print(f"Result: {result}")
    print("=" * 50)

def test_both_channels():
    """Test 3: Send to both Slack and Email"""
    print("🔄 Test 3: Both Channels")
    
    payload = {
        "recipient_email": "g01dman.sachks@gmail.com",
        "slack_channel": "#payroll-data-insights",
        "subject": "Final Test - Unified API",
        "text": "✅ Final test - Unified messaging API working perfectly! Sent to both Slack and Email.",
        "images": ["egimage.png"]
    }
    
    response = requests.post(f"{BASE_URL}/send-both", json=payload)
    result = response.json()
    
    print(f"Status: {response.status_code}")
    print(f"Result: {result}")
    print("=" * 50)

if __name__ == "__main__":
    print("🧪 Testing Unified Messaging API")
    print("=" * 50)
    
    try:
        test_slack_only()
        test_email_only() 
        test_both_channels()
        
        print("✅ All tests completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
