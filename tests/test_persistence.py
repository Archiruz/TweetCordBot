#!/usr/bin/env python3
"""
Test script to verify persistent state functionality.
This simulates multiple runs of the bot to ensure state persists.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to import main.py
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import load_last_tweet_id, save_last_tweet_id, STATE_FILE

def test_persistence():
    """Test that state persists across function calls."""
    print("Testing TweetCordBot Persistence...")
    
    # Clean up any existing state file
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        print("✓ Cleaned up existing state file")
    
    # Test 1: Save a tweet ID
    test_tweet_id = "1234567890123456789"
    save_last_tweet_id(test_tweet_id)
    print(f"✓ Saved tweet ID: {test_tweet_id}")
    
    # Test 2: Verify file was created
    assert STATE_FILE.exists(), "State file was not created!"
    print(f"✓ State file exists at: {STATE_FILE}")
    
    # Test 3: Load the tweet ID (simulating restart)
    load_last_tweet_id()
    from main import last_tweet_id
    assert last_tweet_id == test_tweet_id, f"Expected {test_tweet_id}, got {last_tweet_id}"
    print(f"✓ Loaded tweet ID matches: {last_tweet_id}")
    
    # Test 4: Update to a new tweet ID
    new_tweet_id = "9876543210987654321"
    save_last_tweet_id(new_tweet_id)
    print(f"✓ Updated tweet ID to: {new_tweet_id}")
    
    # Test 5: Load again to verify update
    load_last_tweet_id()
    from main import last_tweet_id as updated_id
    assert updated_id == new_tweet_id, f"Expected {new_tweet_id}, got {updated_id}"
    print(f"✓ Updated tweet ID persists: {updated_id}")
    
    # Test 6: Verify file content directly
    with open(STATE_FILE, 'r') as f:
        file_content = f.read().strip()
    assert file_content == new_tweet_id, f"File content mismatch: {file_content}"
    print(f"✓ File content is correct: {file_content}")
    
    print("\n✅ All persistence tests passed!")
    print(f"State file location: {STATE_FILE.absolute()}")
    
    return True

if __name__ == "__main__":
    try:
        test_persistence()
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
