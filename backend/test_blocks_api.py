#!/usr/bin/env python3
"""
Test script for the blocks API endpoint.
Demonstrates sample requests with array of block objects.
"""

import requests
import json

# API endpoint
BASE_URL = "http://localhost:8080"
BLOCKS_ENDPOINT = f"{BASE_URL}/blocks/execute"

def test_complete_workflow():
    """Test complete workflow with array of blocks"""
    blocks_data = [
        {
            "block_type": "input_source",
            "block_id": 1,
            "csv_source": "/Users/glavoie/Datagent-1/imdb_top_1000.csv"
        },
        {
            "block_type": "process",
            "block_id": 2,
            "pre_req": [1],
            "prompt": "merge these two sources and create a summary of top rated movies by genre"
        },
        {
            "block_type": "output",
            "block_id": 3,
            "pre_req": [2],
            "init_script": "import pandas as pd\ndf.to_csv('processed_movies.csv', index=False)\nprint('Data saved successfully')"
        },
        {
            "block_type": "destination",
            "block_id": 4,
            "pre_req": [3],
            "email_dest": "user@example.com"
        }
    ]
    
    print("Testing COMPLETE WORKFLOW with array of blocks:")
    print(f"Request: {json.dumps(blocks_data, indent=2)}")
    
    try:
        response = requests.post(BLOCKS_ENDPOINT, json=blocks_data)
        print(f"Response Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")
    print("-" * 50)

def test_partial_workflow():
    """Test partial workflow with some blocks"""
    blocks_data = [
        {
            "block_type": "input_source",
            "block_id": 1,
            "csv_source": "/Users/glavoie/Datagent-1/HistoricalQuotes.csv"
        },
        {
            "block_type": "process",
            "block_id": 2,
            "pre_req": [1],
            "prompt": "analyze historical stock quotes and identify trends"
        }
    ]
    
    print("Testing PARTIAL WORKFLOW with 2 blocks:")
    print(f"Request: {json.dumps(blocks_data, indent=2)}")
    
    try:
        response = requests.post(BLOCKS_ENDPOINT, json=blocks_data)
        print(f"Response Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")
    print("-" * 50)

def test_complex_dependencies():
    """Test complex workflow with multiple dependencies"""
    blocks_data = [
        {
            "block_type": "input_source",
            "block_id": 1,
            "csv_source": "/Users/glavoie/Datagent-1/imdb_top_1000.csv"
        },
        {
            "block_type": "input_source",
            "block_id": 5,
            "csv_source": "/Users/glavoie/Datagent-1/HistoricalQuotes.csv"
        },
        {
            "block_type": "process",
            "block_id": 2,
            "pre_req": [1, 5],
            "prompt": "combine movie data with stock data to find correlations"
        },
        {
            "block_type": "output",
            "block_id": 3,
            "pre_req": [2],
            "init_script": "df.to_json('analysis_results.json', orient='records')"
        },
        {
            "block_type": "destination",
            "block_id": 4,
            "pre_req": [3],
            "email_dest": "analyst@company.com"
        }
    ]
    
    print("Testing COMPLEX DEPENDENCIES workflow:")
    print(f"Request: {json.dumps(blocks_data, indent=2)}")
    
    try:
        response = requests.post(BLOCKS_ENDPOINT, json=blocks_data)
        print(f"Response Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")
    print("-" * 50)

def test_invalid_blocks():
    """Test invalid blocks handling"""
    blocks_data = [
        {
            "block_type": "invalid_type",
            "block_id": 1
        },
        {
            "block_type": "process",
            "block_id": 2,
            "pre_req": [1]
            # Missing required 'prompt' field
        },
        {
            "block_type": "input_source",
            "block_id": 3,
            "csv_source": "/valid/path/file.csv"
        }
    ]
    
    print("Testing INVALID BLOCKS handling:")
    print(f"Request: {json.dumps(blocks_data, indent=2)}")
    
    try:
        response = requests.post(BLOCKS_ENDPOINT, json=blocks_data)
        print(f"Response Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")
    print("-" * 50)

def test_empty_array():
    """Test empty array handling"""
    blocks_data = []
    
    print("Testing EMPTY ARRAY:")
    print(f"Request: {json.dumps(blocks_data, indent=2)}")
    
    try:
        response = requests.post(BLOCKS_ENDPOINT, json=blocks_data)
        print(f"Response Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")
    print("-" * 50)

if __name__ == "__main__":
    print("=" * 60)
    print("TESTING BLOCKS API ENDPOINT - ARRAY FORMAT")
    print("=" * 60)
    
    # Test different scenarios
    test_complete_workflow()
    test_partial_workflow()
    test_complex_dependencies()
    test_invalid_blocks()
    test_empty_array()
    
    print("All tests completed!")
