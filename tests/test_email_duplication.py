import unittest
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from systems.email_db import EmailDatabase
from tokens import Tokens

class MockTokenInventory:
    def has_token(self, token):
        # Always return True so we pass PSEM check
        return True

class TestEmailDuplication(unittest.TestCase):
    def setUp(self):
        self.inventory = MockTokenInventory()
        self.player_email = "tester@test.com"

    def test_duplication_on_restart(self):
        # 1. Setup DB with one auto-send email
        # We don't rely on actual file loading, we inject mock data
        db1 = EmailDatabase()
        db1.inbox_emails = [{
            "id": "test_email_001",
            "subject": "Test",
            "body": "Body",
            "sender": "Sender",
            "send_on_start": True,
            "token_required": "no",
            "timestamp": "realtime"
        }]
        
        # 2. First Run: Check emails
        inbox = []
        new_emails = db1.check_and_send_emails(self.inventory, self.player_email, inbox)
        self.assertEqual(len(new_emails), 1, "Should send email on first run")
        inbox.extend(new_emails)
        
        # 3. Same Session: Check again
        new_emails_2 = db1.check_and_send_emails(self.inventory, self.player_email, inbox)
        self.assertEqual(len(new_emails_2), 0, "Should NOT send email again in same session (handled by sent_email_ids)")
        
        # 4. RESTART (New DB instance), simulating loading saved inbox
        db2 = EmailDatabase()
        db2.inbox_emails = [{
            "id": "test_email_001",
            "subject": "Test",
            "body": "Body",
            "sender": "Sender",
            "send_on_start": True,
            "token_required": "no",
            "timestamp": "realtime"
        }]
        
        # Pass the EXISTING inbox (loaded from save) to the new DB instance
        new_emails_3 = db2.check_and_send_emails(self.inventory, self.player_email, inbox)
        
        # 5. Test against expectation
        # CURRENT BEHAVIOR: This assertion will FAIL (it will be 1)
        # DESIRED BEHAVIOR: This assertion should PASS (it should be 0)
        self.assertEqual(len(new_emails_3), 0, "Should NOT re-send email if already in inbox (Simulated Restart)")

if __name__ == '__main__':
    unittest.main()
