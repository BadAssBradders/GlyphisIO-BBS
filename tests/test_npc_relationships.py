import os
import sys
import unittest

# Add the project root to sys.path to import systems
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from systems.enhanced_npc import EnhancedNPCResponder

class TestNPCRelationships(unittest.TestCase):
    def setUp(self):
        self.responder = EnhancedNPCResponder()
        self.npc_email = "rain@ciphernet.net"

    def test_affinity_increase(self):
        """Test that affinity increases with interactions."""
        initial_score = 0.0
        # First interaction
        resp1 = self.responder.generate_response(
            self.npc_email, "Hello", "Hi there!", [], "tester", initial_score
        )
        score1 = self.responder.relationship_scores[self.npc_email]
        self.assertAlmostEqual(score1, 0.2)
        
        # Second interaction
        resp2 = self.responder.generate_response(
            self.npc_email, "Status", "How's it going?", [], "tester", score1
        )
        score2 = self.responder.relationship_scores[self.npc_email]
        self.assertAlmostEqual(score2, 0.4)

    def test_tiered_responses(self):
        """Test that prefixes change based on affinity tiers."""
        # Tier 0-3: Stranger (No special prefix)
        resp_low = self.responder.generate_response(
            self.npc_email, "Hello", "Hi!", [], "tester", 1.0
        )
        self.assertFalse("Good to see you again" in resp_low)
        self.assertFalse("always a highlight" in resp_low)

        # Tier 3-7: Associate - Use a fresh responder to avoid repetition and score carry-over
        responder2 = EnhancedNPCResponder()
        resp_med = responder2.generate_response(
            self.npc_email, "Status", "How's it going?", [], "tester", 4.0
        )
        print(f"\nDEBUG: resp_med: '{resp_med}'")
        self.assertTrue("Good to see you again, tester." in resp_med)

        # Tier 7-10: Friend - Use a fresh responder
        responder3 = EnhancedNPCResponder()
        resp_high = responder3.generate_response(
            self.npc_email, "Help", "I need assistance.", [], "tester", 8.0
        )
        print(f"DEBUG: resp_high: '{resp_high}'")
        self.assertTrue("Hey, it's always a highlight when you drop in." in resp_high)

if __name__ == "__main__":
    unittest.main()
