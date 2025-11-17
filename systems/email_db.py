"""Email database system for managing emails and templates."""

import json
import os
from typing import Optional

from utils import get_data_path, log_event, normalize_timestamp_1989
from tokens import Tokens, normalize_token


class Email:
    """Represents an email message."""
    
    def __init__(self, sender, recipient, subject, body, timestamp=None):
        self.sender = sender
        self.recipient = recipient
        self.subject = subject
        self.body = body
        self.timestamp = normalize_timestamp_1989(timestamp)
        self.read = False
        self.email_id = None  # Track which email template this came from

    def to_dict(self):
        return {
            "id": self.email_id,
            "sender": self.sender,
            "recipient": self.recipient,
            "subject": self.subject,
            "body": self.body,
            "timestamp": self.timestamp,
            "read": self.read,
        }

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            return None
        sender = data.get("sender")
        recipient = data.get("recipient")
        subject = data.get("subject")
        body = data.get("body")
        timestamp = data.get("timestamp")
        email = cls(sender, recipient, subject, body, timestamp)
        email.email_id = data.get("id")
        email.read = bool(data.get("read", False))
        return email


class EmailDatabase:
    """Manages email loading from JSON files and token-based email triggering"""
    
    def __init__(self):
        self.inbox_emails = []
        self.outbox_templates = []
        self.sent_email_ids = set()  # Track which emails have been sent
        self.load_inbox_emails()
        self.load_outbox_templates()
    
    def load_inbox_emails(self):
        """Load emails that can be sent to the player from JSON"""
        try:
            inbox_path = get_data_path("emails_inbox.json")
            if os.path.exists(inbox_path):
                with open(inbox_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.inbox_emails = data.get("emails", [])
            else:
                print("Warning: emails_inbox.json not found")
                self.inbox_emails = []
        except Exception as e:
            print(f"Error loading emails_inbox.json: {e}")
            self.inbox_emails = []
    
    def load_outbox_templates(self):
        """Load email templates the player can send from JSON"""
        try:
            outbox_path = get_data_path("emails_outbox.json")
            if os.path.exists(outbox_path):
                with open(outbox_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.outbox_templates = data.get("email_templates", [])
            else:
                print("Warning: emails_outbox.json not found")
                self.outbox_templates = []
        except Exception as e:
            print(f"Error loading emails_outbox.json: {e}")
            self.outbox_templates = []
    
    def check_and_send_emails(self, inventory, player_email):
        """Check token requirements and send emails that should be auto-sent"""
        new_emails = []
        
        for email_data in self.inbox_emails:
            email_id = email_data.get("id")
            
            # Skip if already sent
            if email_id in self.sent_email_ids:
                continue
            
            # Check if email should be sent on start (but still check token if required)
            if email_data.get("send_on_start", False):
                if not inventory.has_token(Tokens.PSEM):
                    continue
                token_required = email_data.get("token_required", "no").lower()
                if token_required == "yes":
                    token_name = normalize_token(email_data.get("token_name"))
                    if token_name and inventory.has_token(token_name):
                        email = self.create_email_from_data(email_data, player_email)
                        if email:
                            new_emails.append(email)
                            self.sent_email_ids.add(email_id)
                            log_event(f"Delivered email '{email.subject}' from {email.sender}")
                elif token_required == "no":
                    # No token required, send it
                    email = self.create_email_from_data(email_data, player_email)
                    if email:
                        new_emails.append(email)
                        self.sent_email_ids.add(email_id)
                        log_event(f"Delivered email '{email.subject}' from {email.sender}")
                continue
            
            # Check token requirements for auto-send emails
            if email_data.get("auto_send", False):
                if not inventory.has_token(Tokens.PSEM):
                    continue
                token_required = email_data.get("token_required", "no").lower()
                
                if token_required == "yes":
                    token_name = normalize_token(email_data.get("token_name"))
                    if token_name and inventory.has_token(token_name):
                        email = self.create_email_from_data(email_data, player_email)
                        if email:
                            new_emails.append(email)
                            self.sent_email_ids.add(email_id)
                            log_event(f"Delivered email '{email.subject}' from {email.sender}")
                elif token_required == "no":
                    # No token required, send it
                    email = self.create_email_from_data(email_data, player_email)
                    if email:
                        new_emails.append(email)
                        self.sent_email_ids.add(email_id)
                        log_event(f"Delivered email '{email.subject}' from {email.sender}")
        
        if new_emails:
            log_event(f"Email check complete: {len(new_emails)} new message(s)")
        return new_emails
    
    def create_email_from_data(self, email_data, player_email):
        """Create an Email object from JSON data"""
        try:
            sender = email_data.get("sender", "")
            subject = email_data.get("subject", "")
            body = email_data.get("body")

            placeholder_username = player_email or "operative"

            def apply_placeholders(text):
                if not isinstance(text, str):
                    return text
                return text.replace("{username}", placeholder_username)

            subject = apply_placeholders(subject)
            if body is not None:
                body = apply_placeholders(body)

            if body is None:
                body_lines = []
                bodyline_count = email_data.get("bodylines")

                # Attempt to coerce the declared count into an int if provided
                try:
                    declared_count = int(bodyline_count) if bodyline_count is not None else None
                except (TypeError, ValueError):
                    declared_count = None

                index = 1
                while True:
                    key = f"body{index}"
                    has_key = key in email_data

                    # If a count was provided, stop once we've processed that many entries
                    if declared_count is not None and index > declared_count:
                        break

                    if not has_key:
                        # No explicit key and no remaining expected entries -> terminate
                        if declared_count is None:
                            break
                        # If keys are missing but a count was declared, treat as empty string placeholders
                        value = ""
                    else:
                        value = email_data.get(key)

                    if value is None:
                        # Null entries are treated as intentional blanks when within the declared count
                        if declared_count is not None and index <= declared_count:
                            body_lines.append("")
                    else:
                        rendered_value = apply_placeholders(str(value))
                        body_lines.append(rendered_value)

                    if declared_count is None and not has_key:
                        break

                    index += 1

                if body_lines:
                    body = "\n".join(body_lines)

            if body is None:
                body = ""
            timestamp = email_data.get("timestamp")
            timestamp = normalize_timestamp_1989(timestamp)
            
            email = Email(sender, player_email, subject, body, timestamp)
            email.email_id = email_data.get("id")
            return email
        except Exception as e:
            log_event(f"Error creating email from data: {e}")
            return None
    
    def get_email_by_id(self, email_id):
        """Get email data by ID"""
        for email_data in self.inbox_emails:
            if email_data.get("id") == email_id:
                return email_data
        return None
    
    def mark_email_sent(self, email_id):
        """Mark an email as sent"""
        self.sent_email_ids.add(email_id)
    
    def save_sent_emails(self):
        """Save sent email IDs to a file for persistence"""
        # Persistence disabled
        return
    
    def load_sent_emails(self):
        """Load sent email IDs from file"""
        try:
            self.sent_email_ids = set()
        except Exception as e:
            print(f"Error loading sent emails: {e}")
            self.sent_email_ids = set()

    def deliver_email_by_id(self, email_id, player_email, placeholders=None):
        """Create and mark an email as sent immediately."""
        email_data = self.get_email_by_id(email_id)
        if not email_data or email_id in self.sent_email_ids:
            return None

        email = self.create_email_from_data(email_data, player_email)
        if not email:
            return None

        if placeholders:
            for key, value in placeholders.items():
                token = f"{{{key}}}"
                replacement = str(value)
                if isinstance(email.subject, str):
                    email.subject = email.subject.replace(token, replacement)
                if isinstance(email.body, str):
                    email.body = email.body.replace(token, replacement)

        self.sent_email_ids.add(email_id)
        return email

