import json
import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import GLYPHIS_IOBBS
from tokens import Tokens
from systems.email_db import Email
from Data.OS.OS_Mode import OSMode


class _InventoryStub:
    def __init__(self, tokens=None):
        self._tokens = set(tokens or [])

    def has_token(self, token):
        return token in self._tokens


class TestSchoolHackMainLogic(unittest.TestCase):
    def test_school_hack_contact_silenced_only_after_gameover(self):
        app = GLYPHIS_IOBBS.__new__(GLYPHIS_IOBBS)
        app.inventory = _InventoryStub({Tokens.GAMEOVER_SCHOOLHACK})

        self.assertTrue(app._is_school_hack_contact_silenced("rain@ciphernet.net"))
        self.assertTrue(app._is_school_hack_contact_silenced("glyphis@ciphernet.net"))
        self.assertFalse(app._is_school_hack_contact_silenced("miazuki@ciphernet.net"))

        app.inventory = _InventoryStub()
        self.assertFalse(app._is_school_hack_contact_silenced("rain@ciphernet.net"))

    def test_gameover_prunes_stale_school_hack_delayed_replies(self):
        app = GLYPHIS_IOBBS.__new__(GLYPHIS_IOBBS)
        app.inventory = _InventoryStub({Tokens.GAMEOVER_SCHOOLHACK})
        app.delayed_emails = [
            {"email": Email("rain@ciphernet.net", "player@test.com", "RE: test", "dead line")},
            {"email": Email("uncle-am@ciphernet.net", "player@test.com", "RE: test", "dead line")},
            {"email": Email("miazuki@ciphernet.net", "player@test.com", "RE: test", "still allowed")},
        ]

        app._prune_school_hack_silenced_delayed_emails()

        self.assertEqual(len(app.delayed_emails), 1)
        self.assertEqual(app.delayed_emails[0]["email"].sender, "miazuki@ciphernet.net")


class TestSchoolHackTelebaseLogic(unittest.TestCase):
    def setUp(self):
        self.mode = OSMode.__new__(OSMode)

    def _configure_mode(self, current_students, baseline_students, tokens=None):
        token_set = set(tokens or [])
        self.mode.has_token = lambda token: token in token_set
        self.mode._get_school_database_students = lambda: current_students
        self.mode._build_default_school_database_state = lambda: {"students": baseline_students}

    def test_no_fail_when_nothing_changed(self):
        baseline = [
            {
                "id": "student-1",
                "grades": {"ENGLISH": "C", "U.S.HISTORY": "C", "SCIENCE": "B"},
                "attendance": 91,
            }
        ]
        current = [
            {
                "id": "student-1",
                "grades": {"ENGLISH": "C", "U.S.HISTORY": "C", "SCIENCE": "B"},
                "attendance": 12,
            }
        ]

        self._configure_mode(current, baseline, {Tokens.SCHOOL_HACK4B})
        self.assertFalse(self.mode._has_school_hack_incorrect_grade_attempt())

    def test_fail_when_any_grade_changes_incorrectly(self):
        baseline = [
            {
                "id": "student-1",
                "grades": {"ENGLISH": "C", "U.S.HISTORY": "C", "SCIENCE": "B"},
            },
            {
                "id": "student-2",
                "grades": {"ENGLISH": "B", "U.S.HISTORY": "B", "SCIENCE": "A"},
            },
        ]
        current = [
            {
                "id": "student-1",
                "grades": {"ENGLISH": "C", "U.S.HISTORY": "C", "SCIENCE": "A"},
            },
            {
                "id": "student-2",
                "grades": {"ENGLISH": "B", "U.S.HISTORY": "B", "SCIENCE": "A"},
            },
        ]

        self._configure_mode(current, baseline, {Tokens.SCHOOL_HACK4B})
        self.assertTrue(self.mode._has_school_hack_incorrect_grade_attempt())

    def test_completed_school_hack_never_counts_as_failed_attempt(self):
        baseline = [
            {
                "id": "student-1",
                "grades": {"ENGLISH": "C", "U.S.HISTORY": "C", "SCIENCE": "B"},
            }
        ]
        current = [
            {
                "id": "student-1",
                "grades": {"ENGLISH": "A", "U.S.HISTORY": "A", "SCIENCE": "B"},
            }
        ]

        self._configure_mode(current, baseline, {Tokens.SCHOOL_HACK4B, Tokens.SCHOOL_HACK5})
        self.assertFalse(self.mode._has_school_hack_incorrect_grade_attempt())


class TestSchoolHackBradsonicMailDelivery(unittest.TestCase):
    def test_school_hack5_completion_mail_is_queued_for_next_mail_sync(self):
        mode = OSMode.__new__(OSMode)
        queued_events = []
        mode.queue_bradsonic_mail_event = queued_events.append

        mode._queue_glyphis_school_hack_complete_mail()

        self.assertEqual(queued_events, ["school_hack_complete_glyphis"])

    def test_pending_completion_mail_delivers_during_mail_exchange(self):
        mode = OSMode.__new__(OSMode)
        mode.mail_local_inbox = []
        mode.mail_settings = {"mail_from": "player@bradsonic.net"}
        mode.consume_pending_bradsonic_mail_events = lambda: ["school_hack_complete_glyphis"]
        mode.save_inbox_emails = lambda emails: None
        mode.play_mail_sound = lambda: None

        delivered = mode._deliver_pending_bradsonic_mail_events()

        self.assertEqual(delivered, 1)
        self.assertEqual(len(mode.mail_local_inbox), 1)
        self.assertEqual(mode.mail_local_inbox[0]["sender"], "glyphis@ciphernet.net")
        self.assertEqual(
            mode.mail_local_inbox[0]["subject"],
            "OPERATIONAL SECURITY // IMMEDIATE COMPLIANCE REQUIRED",
        )

    def test_smokey_intro_delivers_when_glyphis_mail_is_opened_at_night(self):
        mode = OSMode.__new__(OSMode)
        mode.mail_server_connected = True
        mode.mail_local_inbox = []
        mode.mail_settings = {"mail_from": "player@bradsonic.net"}
        mode.get_user_credentials = lambda: ("player", "pw")
        mode.get_mail_trash = lambda: []
        mode.get_mail_outbox = lambda: []
        mode.save_inbox_emails = lambda emails: None
        mode.play_mail_sound = lambda: None
        mode.queue_bradsonic_mail_event = lambda event_id: None
        mode._is_bradsonic_mail_nighttime = lambda: True

        mode._maybe_trigger_smokey_school_intro({
            "id": "glyphis_schoolhack5_123",
            "sender": "glyphis@ciphernet.net",
            "subject": "OPERATIONAL SECURITY // IMMEDIATE COMPLIANCE REQUIRED",
        })

        self.assertEqual(len(mode.mail_local_inbox), 1)
        self.assertEqual(mode.mail_local_inbox[0]["id"], "school_hack_smokey_intro")
        self.assertEqual(mode.mail_local_inbox[0]["sender"], "5m0k3y@629.api")

    def test_smokey_intro_queues_during_day(self):
        mode = OSMode.__new__(OSMode)
        queued_events = []
        mode.mail_server_connected = True
        mode.mail_local_inbox = []
        mode.mail_settings = {"mail_from": "player@bradsonic.net"}
        mode.get_user_credentials = lambda: ("player", "pw")
        mode.get_mail_trash = lambda: []
        mode.get_mail_outbox = lambda: []
        mode.save_inbox_emails = lambda emails: None
        mode.play_mail_sound = lambda: None
        mode.queue_bradsonic_mail_event = queued_events.append
        mode._is_bradsonic_mail_nighttime = lambda: False

        mode._maybe_trigger_smokey_school_intro({
            "id": "glyphis_schoolhack5_123",
            "sender": "glyphis@ciphernet.net",
            "subject": "OPERATIONAL SECURITY // IMMEDIATE COMPLIANCE REQUIRED",
        })

        self.assertEqual(mode.mail_local_inbox, [])
        self.assertEqual(queued_events, ["school_hack_smokey_intro"])

    def test_smokey_intro_waits_for_real_connect_not_passive_poll(self):
        requeued = []
        mode = OSMode.__new__(OSMode)
        mode.mail_local_inbox = []
        mode.mail_settings = {"mail_from": "player@bradsonic.net"}
        mode.get_user_credentials = lambda: ("player", "pw")
        mode.get_mail_trash = lambda: []
        mode.get_mail_outbox = lambda: []
        mode.consume_pending_bradsonic_mail_events = lambda: ["school_hack_smokey_intro"]
        mode.save_inbox_emails = lambda emails: None
        mode.play_mail_sound = lambda: None
        mode.queue_bradsonic_mail_event = requeued.append
        mode._is_bradsonic_mail_nighttime = lambda: True

        delivered = mode._deliver_pending_bradsonic_mail_events(source="poll")

        self.assertEqual(delivered, 0)
        self.assertEqual(requeued, ["school_hack_smokey_intro"])
        self.assertEqual(mode.mail_local_inbox, [])

    def test_valid_smokey_reply_generates_follow_up_mail(self):
        mode = OSMode.__new__(OSMode)
        sent_messages = []
        mode.mail_local_inbox = []
        mode.mail_settings = {"mail_from": "player@bradsonic.net"}
        mode.get_user_credentials = lambda: ("player", "pw")
        mode.has_token = lambda token: False
        mode.get_mail_trash = lambda: []
        mode.consume_pending_bradsonic_mail_events = lambda: []
        mode.save_inbox_emails = lambda emails: None
        mode.play_mail_sound = lambda: None
        mode.send_mail = lambda to, subject, body: sent_messages.append((to, subject, body))
        mode.get_mail_outbox = lambda: [{
            "recipient": "5m0k3y@629.api",
            "subject": "RE: That handle of yours...",
            "body": "Rain\nBertie\nJason",
        }]
        mode.save_mail_outbox = lambda emails: None

        exchange = mode._mail_run_exchange(source="manual")

        self.assertEqual(exchange["new_count"], 1)
        self.assertEqual(mode.mail_local_inbox[0]["id"], "school_hack_smokey_reply")
        self.assertEqual(mode.mail_local_inbox[0]["sender"], "5m0k3y@629.api")
        self.assertEqual(sent_messages[0][0], "5m0k3y@629.api")


class TestSchoolHackNoteProgression(unittest.TestCase):
    def setUp(self):
        self.mode = OSMode.__new__(OSMode)

    def test_school_op_note_phase_covers_mid_mission_steps(self):
        self.mode.has_token = lambda token: token in {Tokens.SCHOOL_HACK4}
        self.assertEqual(self.mode._get_school_op_note_phase(), "hack4")

        self.mode.has_token = lambda token: token in {Tokens.SCHOOL_HACK4A}
        self.assertEqual(self.mode._get_school_op_note_phase(), "hack4a")

        self.mode.has_token = lambda token: token in {Tokens.SCHOOL_HACK4B}
        self.assertEqual(self.mode._get_school_op_note_phase(), "hack4b")

        self.mode.has_token = lambda token: token in {Tokens.SCHOOL_HACK5}
        self.assertEqual(self.mode._get_school_op_note_phase(), "hack5")

    def test_school_op_note_content_changes_for_spoof_and_numbers_phases(self):
        self.mode.has_token = lambda token: False

        hack4_note = self.mode._get_school_op_note_content(note_phase="hack4")
        self.assertIn("Sent the receptionist request for all school numbers", hack4_note)
        self.assertIn("Check BRADSONIC-MAIL for the receptionist's reply", hack4_note)

        hack4a_note = self.mode._get_school_op_note_content(note_phase="hack4a")
        self.assertIn("got school phone numbers from Ms. McPherson", hack4a_note)
        self.assertIn("subject: got the numbers", hack4a_note)

        hack5_note = self.mode._get_school_op_note_content(note_phase="hack5")
        self.assertIn("Mission complete:", hack5_note)
        self.assertIn("Check BRADSONIC-MAIL for Glyphis' message", hack5_note)


class TestSchoolHackEmailMetadata(unittest.TestCase):
    def test_school_hack_templates_match_unlock_sequence(self):
        inbox_path = os.path.join(
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
            "Data",
            "emails_inbox.json",
        )
        with open(inbox_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)

        emails = {email["id"]: email for email in data["emails"]}

        self.assertEqual(emails["rain_school_help_001"]["token_name"], "JEWEL_VOICE1")
        self.assertEqual(emails["uncle_am_school_grades_001"]["token_name"], "SCHOOL_HACK")
        self.assertEqual(emails["jaxkando_school_grades_001"]["token_name"], "JAXGRADES")
        self.assertEqual(emails["rain_school_plan_001"]["token_name"], "JAXGRADES")


if __name__ == "__main__":
    unittest.main()
