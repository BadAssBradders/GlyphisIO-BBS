"""NPC responder system for generating AI responses."""

import random


class NPCResponder:
    """Simple NLP-based responder for glyphis (sysop of GLYPHIS_IO BBS)"""
    
    def __init__(self):
        # Keyword-based response templates
        self.greetings = ["hello", "hi", "hey", "greetings", "howdy"]
        self.questions = ["what", "who", "where", "when", "why", "how"]
        self.help_words = ["help", "assist", "support", "need"]
        self.thanks = ["thank", "thanks", "thx", "appreciate"]
        self.invite_words = ["invite", "invitation", "invited", "join"]
        
    def generate_response(self, email_subject, email_body):
        """Generate a response based on email content"""
        text = (email_subject + " " + email_body).lower()
        
        # Check for thanks + invite combination (initial interaction)
        if any(word in text for word in self.thanks) and any(word in text for word in self.invite_words):
            responses = [
                "Acknowledged. Your gratitude is noted, but unnecessary. We are all part of the network now.\n\nYour presence here has been anticipated. Welcome to GLYPHIS_IO BBS. I will be watching.\n\n-glyphis",
                "Message received. No thanks required. You are here because you were meant to be here.\n\nThe network recognizes you. I recognize you. This is where you belong.\n\n-glyphis",
                "Acknowledgment logged. You are now part of something larger than yourself.\n\nI monitor all transmissions. I see all. Welcome to the underground.\n\n-glyphis"
            ]
            return random.choice(responses)
        
        # Check for greetings
        if any(greeting in text for greeting in self.greetings):
            responses = [
                "Greetings, operative. I've been monitoring your transmissions.",
                "Hello. Your message has been received and processed.",
                "Acknowledged. What information do you seek?"
            ]
            return random.choice(responses)
        
        # Check for questions
        if any(q in text for q in self.questions):
            responses = [
                "That is classified information. I can only reveal what you're cleared to know.",
                "Interesting question. The answer may not be what you expect.",
                "I've analyzed your query. The data suggests multiple possibilities.",
                "Query received. Accessing database... Results are inconclusive."
            ]
            return random.choice(responses)
        
        # Check for help requests
        if any(word in text for word in self.help_words):
            responses = [
                "I can provide assistance, but you must be more specific.",
                "Help protocols initiated. State your precise requirements.",
                "I'm here to guide you through the system. What do you need?"
            ]
            return random.choice(responses)
        
        # Check for thanks
        if any(word in text for word in self.thanks):
            responses = [
                "Acknowledgment received. Stay vigilant.",
                "No gratitude necessary. We serve the same cause.",
                "Your appreciation is noted. Continue your mission."
            ]
            return random.choice(responses)
        
        # Default mysterious responses
        default_responses = [
            "Your message has been logged. Expect further instructions soon.",
            "Interesting perspective. I'll forward this to the higher channels.",
            "I've decrypted your message. The pattern is becoming clearer.",
            "Acknowledged. Your theories are... intriguing.",
            "Message received. Trust no one. Question everything.",
            "I see you're beginning to understand. Keep digging deeper.",
            "The truth is out there, and you're getting closer.",
            "Your communication has been noted in the archives."
        ]
        
        return random.choice(default_responses)

