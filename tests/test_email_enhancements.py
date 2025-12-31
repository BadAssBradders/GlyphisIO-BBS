import os
import sys
import time
import random
import traceback

# Add the project root to sys.path to import systems
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from systems.enhanced_npc import EnhancedNPCResponder

def test_conversation_memory_followup():
    print("--- Testing Conversation Memory (Follow-up) ---")
    responder = EnhancedNPCResponder()
    
    # Topic 1: How are you
    print("First time asking 'how are you'...")
    resp1 = responder.generate_response("rain@ciphernet.net", "How are you?", "how are you rain?", [])
    print(f"Response 1: {resp1}")
    
    # Topic 2: Something else
    print("\nAsking something else...")
    resp2 = responder.generate_response("rain@ciphernet.net", "Help", "can you help me?", [])
    print(f"Response 2: {resp2}")
    
    # Topic 1 again: How are you (Follow-up)
    print("\nAsking 'how are you' again (should be a follow-up)...")
    # We might need to run it a few times to get a prefix (40% chance)
    found_prefix = False
    for i in range(10):
        # We need to simulate multiple turns to increase the topic count
        resp3 = responder.generate_response("rain@ciphernet.net", f"How are you? {i}", "how are you doing today?", [])
        prefixes = [
            "As I was saying before", 
            "To follow up on our last talk", 
            "Regarding what we discussed earlier", 
            "Back to my previous point", 
            "Returning to this subject"
        ]
        if any(prefix in resp3 for prefix in prefixes):
            found_prefix = True
            print(f"Response 3 (with prefix): {resp3}")
            break
    
    print(f"Found follow-up prefix: {found_prefix}")
    assert found_prefix or topic_count_working(responder, "rain@ciphernet.net", "how_are_you")

def topic_count_working(responder, email, category):
    count = responder.topic_memory.get(email, {}).get(category, 0)
    print(f"Topic '{category}' count for {email}: {count}")
    return count > 1

if __name__ == "__main__":
    try:
        test_conversation_memory_followup()
        print("\nENHANCEMENT TESTS PASSED!")
    except AssertionError as e:
        print(f"\nENHANCEMENT TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nAN ERROR OCCURRED: {e}")
        traceback.print_exc()
        sys.exit(1)
