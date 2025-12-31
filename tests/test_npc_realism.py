import os
import sys

# Add the project root to sys.path to import systems
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from systems.enhanced_npc import EnhancedNPCResponder, CharacterTrait

def test_lore_triggers():
    print("--- Testing Lore Triggers ---")
    
    # Test Pacifica Isles
    responder = EnhancedNPCResponder()
    resp = responder.generate_response("glyphis@ciphernet.net", "Question", "What is the Pacifica Isles?", [])
    print(f"Glyphis on Pacifica: {resp}")
    assert any(term in resp for term in ["Pacifica", "administration", "field office"])
    
    # Test Cultural Erasure
    responder = EnhancedNPCResponder()
    resp = responder.generate_response("uncle-am@ciphernet.net", "History", "Tell me about the banned songs.", [])
    print(f"Uncle-am on Banned Songs: {resp}")
    assert any(term in resp.lower() for term in ["banned", "songs", "old words", "hiroshima"])

    # Test Shogun
    responder = EnhancedNPCResponder()
    resp = responder.generate_response("jaxkando@ciphernet.net", "The Shogun", "Who is the Shogun?", [])
    print(f"Jaxkando on Shogun: {resp}")
    assert "SHOGUN" in resp.upper()

    # Test Corporate Tech
    responder = EnhancedNPCResponder()
    resp = responder.generate_response("jaxkando@ciphernet.net", "Hardware", "Is Bradsonic good?", [])
    print(f"Jaxkando on Bradsonic: {resp}")
    assert any(term in resp.upper() for term in ["BRADSONIC", "WESTERN BEAM", "NEODRIVE"])

def test_paranoia_gating():
    print("\n--- Testing Paranoia Gating ---")
    responder = EnhancedNPCResponder()
    
    # Without PARANOIA1 token
    resp = responder.generate_response("glyphis@ciphernet.net", "How are you?", "how are you doing glyphis?", [])
    print(f"Glyphis HowAreYou (No Token): {resp}")
    # Should NOT be paranoid
    paranoid_terms = ["Cautious", "Wary", "Suspicious"]
    assert not any(term in resp for term in paranoid_terms)
    
    # With PARANOIA1 token
    # We might need to run it a few times because of weighted selection, or just check if it's possible
    # In our implementation, we added it to the responses list if the token is present.
    # To be sure, we can mock the random selection or just check if it EVER appears.
    found_paranoid = False
    for _ in range(20):
        # Use a fresh responder each time to avoid repetition memory in this loop
        loop_responder = EnhancedNPCResponder()
        resp = loop_responder.generate_response("glyphis@ciphernet.net", "How are you?", "how are you doing glyphis?", ["PARANOIA1"])
        if any(term in resp for term in paranoid_terms):
            found_paranoid = True
            break
    
    print(f"Glyphis HowAreYou (With Token) - Found Paranoid: {found_paranoid}")
    assert found_paranoid

def test_weighted_selection():
    print("\n--- Testing Weighted Selection (Probabilistic) ---")
    responder = EnhancedNPCResponder()
    character = responder.characters["glyphis@ciphernet.net"]
    
    # Glyphis has high weights for Mysterious and Formal, low for Paranoia (0.5)
    # This is hard to test deterministically without mocking, 
    # but we can verify the weights are parsed correctly.
    print(f"Glyphis weights: {character.trait_weights}")
    assert character.trait_weights[CharacterTrait.MYSTERIOUS] == 2.0
    assert character.trait_weights[CharacterTrait.PARANOID] == 0.5

def test_repetition():
    print("\n--- Testing Repetition Memory ---")
    responder = EnhancedNPCResponder()
    
    # First time
    resp1 = responder.generate_response("glyphis@ciphernet.net", "Hello", "Hi", [])
    print(f"Glyphis Greeting 1: {resp1}")
    
    # Second time (repetitive)
    resp2 = responder.generate_response("glyphis@ciphernet.net", "Hello", "Hi", [])
    print(f"Glyphis Greeting 2: {resp2}")
    assert "repeat" in resp2.lower() or "first time" in resp2.lower() or "Redundancy" in resp2

def test_fallbacks():
    print("\n--- Testing Character Fallbacks ---")
    responder = EnhancedNPCResponder()
    
    # Nonsense input
    resp = responder.generate_response("jaxkando@ciphernet.net", "Blah", "kjhdlkashd", [])
    print(f"Jaxkando Fallback: {resp}")
    assert any(term in resp for term in ["COOL", "GOT IT", "NICE", "AWESOME", "THANKS"])

if __name__ == "__main__":
    try:
        test_lore_triggers()
        test_paranoia_gating()
        test_weighted_selection()
        test_repetition()
        test_fallbacks()
        print("\nALL TESTS PASSED!")
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nAN ERROR OCCURRED: {e}")
        sys.exit(1)
