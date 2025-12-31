"""
Enhanced NPC responder system with character traits and context-aware responses.

This system generates responses based on:
- Character personality traits
- Player's unlocked content (tokens)
- Specific triggers (help requests, ASL, how are you, etc.)
- Conversation context

All responses follow the multibody email format:
- First line: no leading newline
- Subsequent lines: start with \n
- Paragraph breaks: \n\n
"""

import random
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class CharacterTrait(Enum):
    """Personality traits that influence response style"""
    FORMAL = "formal"
    CASUAL = "casual"
    MYSTERIOUS = "mysterious"
    FRIENDLY = "friendly"
    TECHNICAL = "technical"
    EMOTIONAL = "emotional"
    HUMOROUS = "humorous"
    PARANOID = "paranoid"
    OPTIMISTIC = "optimistic"
    NOSTALGIC = "nostalgic"


@dataclass
class CharacterProfile:
    """Defines a character's personality and response patterns"""
    name: str
    email: str
    traits: List[CharacterTrait]
    trait_weights: Dict[CharacterTrait, float] = field(default_factory=dict)
    speech_patterns: Dict[str, str] = field(default_factory=dict)
    interests: List[str] = field(default_factory=list)
    catchphrases: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Set default trait weights if not provided"""
        if not self.trait_weights:
            # Default: equal weight for all traits
            for trait in self.traits:
                self.trait_weights[trait] = 1.0


class EnhancedNPCResponder:
    """
    Advanced NPC responder that uses character traits and context
    to generate believable, personality-driven responses.
    """
    
    def __init__(self):
        self.characters = self._initialize_characters()
        self.conversation_history: Dict[str, List[Dict]] = {}  # Track conversations per character
        self.last_trigger_category: Dict[str, str] = {}  # Last category per character
        self.topic_memory: Dict[str, Dict[str, int]] = {}  # Track how many times each topic was discussed per character
        self.relationship_scores: Dict[str, float] = {}  # Track affinity (0-10) per character
        
        # Load character profiles
    
    def _format_response(self, text: str) -> str:
        """
        Format response text to match multibody email format.
        
        Format matches emails_inbox.json structure:
        - First line: no leading newline
        - Subsequent lines: start with \n
        - When joined, creates proper paragraph breaks (\n\n)
        """
        if not text:
            return ""
        
        # Split by double newlines (paragraph breaks) or single newlines
        # Handle both \n\n and \n patterns
        if "\n\n" in text:
            paragraphs = text.split("\n\n")
        else:
            # If no double newlines, treat entire text as one paragraph
            paragraphs = [text]
        
        # First paragraph: no leading newline, strip any existing newlines
        # Subsequent paragraphs: start with \n
        formatted_paragraphs = []
        for i, para in enumerate(paragraphs):
            # Clean up the paragraph
            para = para.strip()
            if not para:
                continue
            
            # Remove any leading newlines from the paragraph
            para = para.lstrip("\n")
            
            if i == 0:
                # First paragraph: no leading newline
                formatted_paragraphs.append(para)
            else:
                # Subsequent paragraphs: start with \n
                formatted_paragraphs.append(f"\n{para}")
        
        # Join with \n - this creates \n\n between paragraphs since
        # subsequent paragraphs already start with \n
        return "\n".join(formatted_paragraphs)
        
    def _initialize_characters(self) -> Dict[str, CharacterProfile]:
        """Initialize character profiles with their personalities"""
        return {
            "glyphis@ciphernet.net": CharacterProfile(
                name="glyphis",
                email="glyphis@ciphernet.net",
                traits=[CharacterTrait.MYSTERIOUS, CharacterTrait.FORMAL, CharacterTrait.TECHNICAL, CharacterTrait.PARANOID],
                trait_weights={
                    CharacterTrait.MYSTERIOUS: 2.0,
                    CharacterTrait.FORMAL: 1.5,
                    CharacterTrait.TECHNICAL: 1.0,
                    CharacterTrait.PARANOID: 0.5, # Starts low, can be increased later
                },
                speech_patterns={
                    "greeting": "Acknowledged.",
                    "closing": "-glyphis",
                    "emphasis": "I see all.",
                },
                interests=["surveillance", "network security", "encryption"],
                catchphrases=["I will be watching.", "The network sees all.", "Trust no one."]
            ),
            "rain@ciphernet.net": CharacterProfile(
                name="rain",
                email="rain@ciphernet.net",
                traits=[CharacterTrait.CASUAL, CharacterTrait.FRIENDLY, CharacterTrait.OPTIMISTIC],
                trait_weights={
                    CharacterTrait.CASUAL: 2.0,
                    CharacterTrait.FRIENDLY: 1.8,
                    CharacterTrait.OPTIMISTIC: 1.2,
                },
                speech_patterns={
                    "greeting": "Hey",
                    "closing": "-rain",
                    "emphasis": "I've got this.",
                },
                interests=["operations", "coordination", "missions"],
                catchphrases=["Let's do this!", "I've got plenty of tasks.", "Making chaos into order."]
            ),
            "jaxkando@ciphernet.net": CharacterProfile(
                name="jaxkando",
                email="jaxkando@ciphernet.net",
                traits=[CharacterTrait.CASUAL, CharacterTrait.HUMOROUS, CharacterTrait.TECHNICAL],
                trait_weights={
                    CharacterTrait.CASUAL: 2.0,
                    CharacterTrait.HUMOROUS: 1.8,
                    CharacterTrait.TECHNICAL: 1.5,
                },
                speech_patterns={
                    "greeting": "JAXKANDO HERE",
                    "closing": "-jaxkando",
                    "emphasis": "ALL CAPS BECAUSE I'M EXCITED",
                },
                interests=["games", "cracking", "reverse engineering"],
                catchphrases=["COME PLAY GAMES WITH ME!", "I eat Denuvo for breakfast.", "Games are art."]
            ),
            "uncle-am@ciphernet.net": CharacterProfile(
                name="uncle-am",
                email="uncle-am@ciphernet.net",
                traits=[CharacterTrait.FRIENDLY, CharacterTrait.NOSTALGIC, CharacterTrait.EMOTIONAL],
                trait_weights={
                    CharacterTrait.FRIENDLY: 2.0,
                    CharacterTrait.NOSTALGIC: 1.8,
                    CharacterTrait.EMOTIONAL: 1.5,
                },
                speech_patterns={
                    "greeting": "uncle-am here",
                    "closing": "-uncle-am",
                    "emphasis": "i care",
                },
                interests=["radio", "community", "old tech"],
                catchphrases=["i'm here if you need me", "always looking for help", "pinkys like me"]
            ),
        }
    
    def generate_response(
        self,
        sender_email: str,
        email_subject: str,
        email_body: str,
        player_tokens: List[str],
        player_username: str = "operative",
        relationship_score: float = 0.0
    ) -> str:
        """
        Generate a context-aware response based on character traits and player state.
        
        Args:
            sender_email: Email address of the NPC responding
            email_subject: Subject line of player's email
            email_body: Body text of player's email
            player_tokens: List of tokens player has (represents unlocked content)
            player_username: Player's username/handle
            
        Returns:
            Generated response text
        """
        # Get character profile
        character = self.characters.get(sender_email)
        if not character:
            # Fallback to generic response
            return self._generic_response(email_subject, email_body)
        
        # Normalize input text
        full_text = f"{email_subject} {email_body}".lower()
        
        # Track conversation
        if sender_email not in self.conversation_history:
            self.conversation_history[sender_email] = []
        
        # Detect specific triggers
        triggers = self._detect_triggers(full_text, player_tokens)
        
        # Determine trigger categories for memory (can be multiple)
        categories = []
        # Lore triggers first as they are most specific
        for key in ["pacifica_isles", "cultural_erasure", "shogun", "corporate_tech"]:
            if triggers.get(key):
                categories.append(key)
        
        # Functional triggers next
        for key in ["how_are_you", "help_request", "asl_request", "greeting", "thanks"]:
            if triggers.get(key):
                categories.append(key)
        
        if triggers.get("unlocked_area_mentioned"):
            categories.append(f"area_{triggers['unlocked_area_mentioned']}")
        elif triggers.get("question") and not categories:
            categories.append("question")
        
        # If no specific categories, use general
        if not categories:
            categories = ["general"]
        
        # Update topic memory for all triggered categories
        if sender_email not in self.topic_memory:
            self.topic_memory[sender_email] = {}
        
        for category in categories:
            self.topic_memory[sender_email][category] = self.topic_memory[sender_email].get(category, 0) + 1
        
        # Use primary category (first one) for repetition check
        primary_category = categories[0]
        topic_count = self.topic_memory[sender_email][primary_category]
        
        # Update relationship score
        if sender_email not in self.relationship_scores:
            self.relationship_scores[sender_email] = relationship_score
            
        # Increment affinity (small increments per interaction, capped at 10)
        self.relationship_scores[sender_email] = min(10.0, self.relationship_scores[sender_email] + 0.2)
        current_affinity = self.relationship_scores[sender_email]
            
        # Check memory to avoid immediate repetition (using primary category)
        is_repetitive = self.last_trigger_category.get(sender_email) == primary_category
        
        # Check if we should use a memory-aware "re-entry" response
        # If topic_count > 1 and it's not immediate repetition, it's a "back to this" moment
        is_follow_up = topic_count > 1 and not is_repetitive
        
        # Generate response based on triggers and character traits (pass categories for multi-trigger handling)
        response = self._build_response(character, triggers, full_text, player_tokens, player_username, is_repetitive, is_follow_up, current_affinity, categories)
        
        # Format response to match multibody email format
        response = self._format_response(response)
        
        # Update memory (use primary category for last_trigger_category)
        self.last_trigger_category[sender_email] = primary_category
        
        # Store conversation
        self.conversation_history[sender_email].append({
            "subject": email_subject,
            "body": email_body,
            "response": response,
            "triggers": triggers,
            "category": primary_category,
            "categories": categories  # Store all categories for reference
        })
        
        return response
    
    def _detect_triggers(self, text: str, player_tokens: List[str]) -> Dict[str, any]:
        """Detect specific triggers in the player's message"""
        triggers = {
            "help_request": False,
            "asl_request": False,
            "how_are_you": False,
            "unlocked_area_mentioned": None,
            "greeting": False,
            "thanks": False,
            "question": False,
            "pacifica_isles": False,
            "cultural_erasure": False,
            "shogun": False,
            "corporate_tech": False,
        }
        
        # Lore Triggers
        triggers["pacifica_isles"] = any(word in text for word in ["pacifica", "isles", "administration", "american", "occupation", "usa", "field office"])
        triggers["cultural_erasure"] = any(word in text for word in ["banned", "language", "japanese", "customs", "erasure", "identity", "history", "hiroshima"])
        triggers["shogun"] = "shogun" in text
        triggers["corporate_tech"] = any(word in text for word in ["bradsonic", "western beam", "neodrive", "electronics", "hardware", "terminal", "station"])
        
        # Help requests
        help_patterns = [
            r"\bhelp\b", r"\bassist\b", r"\bsupport\b", r"\bneed\b",
            r"\bhow do i\b", r"\bhow to\b", r"\bwhat should i\b",
            r"\bcan you\b", r"\bcould you\b", r"\bwould you\b"
        ]
        triggers["help_request"] = any(re.search(pattern, text) for pattern in help_patterns)
        
        # ASL requests (age/sex/location)
        asl_patterns = [
            r"\basl\b", r"\bage.*sex.*location\b", r"\bwhere.*from\b",
            r"\bwhere.*live\b", r"\bwho.*are.*you\b", r"\btell.*about.*yourself\b"
        ]
        triggers["asl_request"] = any(re.search(pattern, text) for pattern in asl_patterns)
        
        # How are you / status questions
        status_patterns = [
            r"\bhow.*are.*you\b", r"\bhow.*doing\b", r"\bhow.*going\b",
            r"\bhow.*things\b", r"\bwhat.*up\b", r"\bhow.*feeling\b"
        ]
        triggers["how_are_you"] = any(re.search(pattern, text) for pattern in status_patterns)
        
        # Greetings
        greeting_patterns = [
            r"\bhello\b", r"\bhi\b", r"\bhey\b", r"\bgreetings\b",
            r"\bhowdy\b", r"\bgood morning\b", r"\bgood evening\b"
        ]
        triggers["greeting"] = any(re.search(pattern, text) for pattern in greeting_patterns)
        
        # Thanks
        thanks_patterns = [r"\bthank\b", r"\bthanks\b", r"\bthx\b", r"\bappreciate\b"]
        triggers["thanks"] = any(re.search(pattern, text) for pattern in thanks_patterns)
        
        # Questions
        triggers["question"] = "?" in text or any(word in text for word in ["what", "who", "where", "when", "why", "how"])
        
        # Check for mentioned unlocked areas (based on tokens)
        unlocked_areas = {
            "games": ["games", "game", "play", "gaming", "simulacra", "jaxkando"],
            "urgent ops": ["ops", "operations", "tasks", "missions", "lapc", "cracker", "rain"],
            "team info": ["team", "members", "operators", "glyphis", "rain", "jaxkando", "uncle-am", "dossier"],
            "pirate radio": ["radio", "broadcast", "frequency", "transmission", "uncle-am"],
            "email": ["email", "message", "mail", "correspondence"],
        }
        
        # Token mapping for area access (player needs at least one token from the list)
        area_tokens = {
            "games": ["GAMES1"],
            "urgent ops": ["AUDIO1", "LAPC1", "LAPC1A", "OPS_ACCESS"],
            "team info": ["TEAM_ACCESS"],
            "pirate radio": ["RADIO_ACCESS"],
            "email": ["PSEM"],
        }
        
        for area, keywords in unlocked_areas.items():
            if any(keyword in text for keyword in keywords):
                # Check if player has access to this area
                required_tokens = area_tokens.get(area, [])
                if any(token in player_tokens for token in required_tokens):
                    triggers["unlocked_area_mentioned"] = area
                    break
        
        # Also detect latest unlocked area (for context in responses)
        # Priority order: most recent unlocks first
        latest_area = None
        priority_areas = [
            ("pirate radio", ["RADIO_ACCESS"]),
            ("team info", ["TEAM_ACCESS"]),
            ("urgent ops", ["AUDIO1", "LAPC1", "LAPC1A", "OPS_ACCESS"]),
            ("games", ["GAMES1"]),
            ("email", ["PSEM"]),
        ]
        
        for area, tokens in priority_areas:
            if any(token in player_tokens for token in tokens):
                latest_area = area
                break
        
        triggers["latest_unlocked_area"] = latest_area
        
        return triggers
    
    def _build_response(
        self,
        character: CharacterProfile,
        triggers: Dict[str, any],
        text: str,
        player_tokens: List[str],
        player_username: str,
        is_repetitive: bool = False,
        is_follow_up: bool = False,
        affinity: float = 0.0,
        categories: List[str] = None
    ) -> str:
        """Build a response based on character traits and detected triggers"""
        
        # Add affinity-based warmth
        affinity_prefix = self._get_affinity_prefix(character, affinity, player_username)
        
        # Handle repetition
        if is_repetitive:
            return affinity_prefix + self._handle_repetition(character, player_username)
        
        # If it's a follow-up, maybe add a prefix or use a specific memory response
        prefix = ""
        if is_follow_up:
            follow_up_prefixes = [
                "As I was saying before, ",
                "To follow up on our last talk, ",
                "Regarding what we discussed earlier, ",
                "Back to my previous point, ",
                "Returning to this subject, "
            ]
            if random.random() < 0.4:  # 40% chance of a memory-aware prefix
                prefix = random.choice(follow_up_prefixes)

        # Collect responses from multiple triggers
        response_parts = []
        
        # Priority 1: Handle lore triggers (these are narrative-heavy)
        if triggers["pacifica_isles"]:
            response_parts.append(self._handle_lore_trigger(character, "pacifica_isles", player_tokens, player_username))
        if triggers["cultural_erasure"]:
            response_parts.append(self._handle_lore_trigger(character, "cultural_erasure", player_tokens, player_username))
        if triggers["shogun"]:
            response_parts.append(self._handle_lore_trigger(character, "shogun", player_tokens, player_username))
        if triggers["corporate_tech"]:
            response_parts.append(self._handle_lore_trigger(character, "corporate_tech", player_tokens, player_username))

        # Priority 2: Handle specific functional triggers
        if triggers["help_request"]:
            response_parts.append(self._handle_help_request(character, triggers, player_tokens, player_username))
        
        if triggers["asl_request"]:
            response_parts.append(self._handle_asl_request(character, player_username))
        
        if triggers["how_are_you"]:
            response_parts.append(self._handle_how_are_you(character, player_tokens, player_username))
        
        if triggers["unlocked_area_mentioned"]:
            response_parts.append(self._handle_unlocked_area(character, triggers["unlocked_area_mentioned"], player_tokens, player_username))
        
        # Priority 3: Handle greetings (only if no other responses)
        if triggers["greeting"] and not response_parts:
            response_parts.append(self._handle_greeting(character, triggers, player_tokens, player_username))
        
        # Priority 4: Handle thanks (only if no other responses)
        if triggers["thanks"] and not response_parts:
            response_parts.append(self._handle_thanks(character, player_tokens, player_username))
        
        # Priority 5: Handle questions (only if no other responses)
        if triggers["question"] and not response_parts:
            response_parts.append(self._handle_question(character, text, player_tokens, player_username))
        
        # Default: Character-appropriate general response
        if not response_parts:
            response_parts.append(self._generate_character_response(character, text, player_tokens, player_username))
        
        # Combine multiple responses with natural transitions
        # Limit to 2-3 responses to avoid overwhelming
        if len(response_parts) > 3:
            # Keep the most important ones (lore first, then functional)
            response_parts = response_parts[:3]
        
        # Combine responses with transitions
        if len(response_parts) == 1:
            content = response_parts[0]
        else:
            # Use character-appropriate transitions
            transitions = self._get_transitions(character, len(response_parts))
            content = self._combine_responses(response_parts, transitions)
            
        # Combine affinity prefix with content
        return affinity_prefix + prefix + content

    def _get_affinity_prefix(self, character: CharacterProfile, affinity: float, player_username: str) -> str:
        """Generate a prefix based on relationship status (Strnger, Associate, Friend)"""
        # Tier 0-3: Stranger (No special prefix)
        if affinity < 3.0:
            return ""
        
        # Tier 3-7: Associate (Slightly warmer)
        if affinity < 7.0:
            if character.name == "glyphis":
                return f"I've been observing your progress, {player_username}. You show promise. "
            if character.name == "rain":
                return f"Good to see you again, {player_username}. "
            if character.name == "jaxkando":
                return f"HEY {player_username.upper()}! GOOD TO HAVE YOU BACK! "
            if character.name == "uncle-am":
                return f"it's nice to hear from you again, {player_username}. "
            return f"Hello again, {player_username}. "
            
        # Tier 7-10: Friend (Warm and personal)
        if character.name == "glyphis":
            return f"You've proven yourself an invaluable asset to the network, {player_username}. "
        if character.name == "rain":
            return f"Hey, it's always a highlight when you drop in. "
        if character.name == "jaxkando":
            return f"YOU'RE MY FAVORITE OPERATOR! NO JOKE! "
        if character.name == "uncle-am":
            return f"you know, you're like family to the radio crew now. "
        return f"It's great to hear from a friend like you, {player_username}. "
    
    def _handle_help_request(
        self,
        character: CharacterProfile,
        triggers: Dict[str, any],
        player_tokens: List[str],
        player_username: str
    ) -> str:
        """Generate help response based on character traits"""
        responses = []
        
        if CharacterTrait.FRIENDLY in character.traits:
            responses.extend([
                f"Hey {player_username}, happy to help! What do you need?",
                f"Sure thing! What's going on?",
                f"I'm here for you. What can I do?",
                f"Need a hand with something, {player_username}?",
                f"Always happy to assist a fellow operator.",
            ])
        
        if CharacterTrait.TECHNICAL in character.traits:
            responses.extend([
                f"Technical support protocols initiated. State your precise requirements, {player_username}.",
                f"I can assist with technical matters. What's the issue?",
                f"Debugging mode activated. Describe the problem.",
                f"Hardware or software? Give me the specs.",
                f"I'm ready to troubleshoot whenever you are.",
            ])
        
        if CharacterTrait.CASUAL in character.traits:
            responses.extend([
                f"Yeah, what's up?",
                f"Sure, what do you need help with?",
                f"Lay it on me - what's the problem?",
                f"Whatcha need?",
                f"Got a question? I might have an answer.",
            ])
        
        if CharacterTrait.MYSTERIOUS in character.traits:
            responses.extend([
                f"I can provide assistance, but you must be more specific, {player_username}.",
                f"Help is available... if you know what to ask for.",
                f"State your requirements clearly.",
                f"Assistance is conditional on clarity.",
                f"Seek and you shall find... if your query is precise.",
            ])
        
        # Add context about unlocked areas
        if triggers["unlocked_area_mentioned"]:
            area = triggers["unlocked_area_mentioned"]
            if area == "games":
                responses.append("Check out the Games module - there's plenty to explore there.")
            elif area == "urgent ops":
                responses.append("The Urgent Ops module has missions if you're looking for work.")
            elif area == "team info":
                responses.append("Team Info has dossiers on all of us if you want to know more.")
            elif area == "pirate radio":
                responses.append("Pirate Radio is unlocked - tune in to hear what's happening.")
        
        # If no specific area mentioned, suggest latest unlocked area
        elif triggers.get("latest_unlocked_area"):
            area = triggers["latest_unlocked_area"]
            if character.name == "rain" and area == "urgent ops":
                responses.append("You've got access to Urgent Ops now - check it out for missions!")
            elif character.name == "jaxkando" and area == "games":
                responses.append("You unlocked the Games module! Come play with me!")
            elif character.name == "uncle-am" and area == "pirate radio":
                responses.append("Pirate Radio is unlocked - tune in when you get a chance!")
        
        return self._select_by_traits(character, responses, player_tokens) if responses else "How can I help?"
    
    def _handle_asl_request(self, character: CharacterProfile, player_username: str) -> str:
        """Handle ASL (age/sex/location) requests - characters reveal info based on personality"""
        responses = []
        
        if character.name == "glyphis":
            responses = [
                "I am the sysop. That is all you need to know. I exist in the spaces between packets. Location is irrelevant when you are everywhere. We grow old too soon and wise too late. Please leave your naivety at the door.",
                "Age? Time is meaningless in the digital realm.\n\nI am the network. I am everywhere and nowhere.",
                "Personal details are classified. I am glyphis. That should be sufficient.",
                "I was here before the rename. I will be here after. My stats are not for your consumption.",
                "Identity is a vulnerability. I prefer to remain a ghost in the machine.",
            ]
        elif character.name == "rain":
            responses = [
                f"Hey {player_username}, I'm rain. I don't really do the whole personal info thing, but I'm the taskmaster around here. That's what matters, right?",
                "I'm rain - I handle ops and missions. That's probably more useful info than my age or where I live, don't you think?",
                "Personal details? Nah, let's keep it professional. I'm rain, I coordinate missions. That's what you need to know.",
                "I'm in the city, just like you. Somewhere with too much static and not enough sleep.",
                "20s-ish, female, currently surrounded by terminal screens. That's as much as you're getting!",
            ]
        elif character.name == "jaxkando":
            responses = [
                "JAXKANDO HERE! I'm the gamesmaster. Age? Old enough to crack games! Location? Everywhere there's code to break!\n\nThat's all you need to know!",
                "I'm jaxkando! I reverse engineer things and crack games. That's way more interesting than where I'm from, right?\n\nCOME PLAY GAMES WITH ME!",
                "Personal info? BORING! I'm jaxkando, I break games and systems. That's the interesting stuff!\n\nWant to know more? Play some games with me!",
                "I LIVE IN THE SOURCE CODE! AGE IS JUST A VERSION NUMBER! I'M CURRENTLY AT v2.1 AND STABLE!",
                "LOCATION: SECTOR 7. AGE: LEGENDARY. STATUS: CRACKING!",
            ]
        elif character.name == "uncle-am":
            responses = [
                f"uncle-am here, {player_username}. i'm the radio engineer - pinky, they call us. i'm probably older than most here, grew up with ham radio before all this digital stuff.\n\nlocation? somewhere with good antenna reception, that's all that matters!",
                f"hey {player_username}, i'm uncle-am. i'm the friendly one, the community guy. age? old enough to remember when radio was king. location? my grandmother's garage has the best antenna setup!\n\ni'm here if you need me, always.",
                f"uncle-am here. i'm the radio engineer and community moderator. i'm probably the oldest one here, grew up with shortwave and packet radio.\n\nwhere am i? somewhere with good signal, that's what matters. i'm always listening, always here if you need someone to talk to.",
                "i'm in my 50s, male, and i've seen the world change more than i'd like. currently based in a quiet corner of the city where the field office doesn't look too close.",
                "location is where the signal is strongest. i'm an old soul in a new world.",
            ]
        
        return random.choice(responses) if responses else "I'd rather not share personal details."
    
    def _handle_lore_trigger(
        self,
        character: CharacterProfile,
        category: str,
        player_tokens: List[str],
        player_username: str
    ) -> str:
        """Handle lore-specific triggers based on character personality"""
        responses = []
        
        if category == "pacifica_isles":
            if character.name == "glyphis":
                responses = [
                    "Pacifica is a bureaucrat's dream and a native's nightmare. The administration sees all, but understands little.",
                    "The Pacifica Isles... a manufactured identity for a suppressed people.",
                    "The field office is always listening. Every packet you send is an endorsement of their oversight."
                ]
            elif character.name == "rain":
                responses = [
                    "The Pacifica administration makes things complicated, but we find ways around their rules. That's why we're here.",
                    "Pacifica? Just another system to navigate. Adapt or expire.",
                    "I don't care much for the 'American Pacifica' branding. This place has a soul they can't rename."
                ]
            elif character.name == "uncle-am":
                responses = [
                    "pacifica isles... it sounds so clinical, doesn't it? i still remember when we just called it home. before the administration took over everything.",
                    "the american oversight is everywhere these days. even the radio waves feel heavier.",
                    "i try to stay out of politics, but it's hard when the field office is knocking on everyone's digital door."
                ]

        elif category == "cultural_erasure":
            if character.name == "glyphis":
                responses = [
                    "They took the language, but they couldn't take the thought. Encryption is our new dialect.",
                    "Hiroshima wasn't just the end of a war; it was the start of a silence. We are the echo.",
                    "Identity is a liability in a surveillance state. Perhaps it is better to be forgotten."
                ]
            elif character.name == "uncle-am":
                responses = [
                    "sometimes i whisper the old words into the microphone. just to hear how they sound. it's dangerous, but necessary.",
                    "they banned the songs, they banned the flag, but they can't ban the memory of what we were.",
                    "my grandfather used to tell me about hiroshima castle. said it was the most beautiful thing he'd ever seen before the light took it."
                ]

        elif category == "shogun":
            if character.name == "glyphis":
                responses = [
                    "The Shogun is a puppet dancing on American wires. A symbolic distraction.",
                    "Tokugawa lineage restored? A hollow gesture for a hollowed nation.",
                    "Do not trust the state-approved symbols. They are designed to comfort, not to lead."
                ]
            elif character.name == "jaxkando":
                responses = [
                    "THE SHOGUN? JUST ANOTHER NPC IN A RIGGED GAME! WHO CARES ABOUT SYMBOLS WHEN YOU HAVE SOURCE CODE?!",
                    "I SAW THE SHOGUN ON THE NEWS. LOOKED BORING! I'D RATHER BE CRACKING NEODRIVE CARTRIDGES!",
                ]
            elif character.name == "uncle-am":
                responses = [
                    "the shogun... it's complicated. they say it's a restoration of the old ways, but it feels like a performance. like we're all watching a play where the ending was written by someone else.",
                    "i remember when they announced the shogun's return. my grandmother cried. not from joy, but from... i don't know. it's not the same. it can't be.",
                    "the shogun is a symbol, but symbols can be empty. what matters is what people do with them. whether they remember what was lost, or just accept the new story.",
                    "i've heard the shogun broadcasts. they're polished, perfect. but there's something missing. the weight of history, maybe. or the truth.",
                ]

        elif category == "corporate_tech":
            if character.name == "jaxkando":
                responses = [
                    "BRADSONIC IS THE ONLY WAY TO FLY! WESTERN BEAM IS FOR CORPORATE DRONES! GIMME THAT CHUNKY HARDWARE!",
                    "NEODRIVE SPECS ARE INSANE! HAVE YOU SEEN THE VECTOR PROCESSING ON THE NEWEST CHIPS?!",
                    "I EAT WESTERN BEAM FOR BREAKFAST! BRADSONIC 69000 OR BUST!"
                ]
            elif character.name == "uncle-am":
                responses = [
                    "the old bradsonic units had a warmth to them. the new western beam stuff feels... cold. clinical.",
                    "i'm still running my pirate station on a modified bradsonic relay. they don't make them like they used to.",
                ]

        return self._select_by_traits(character, responses, player_tokens) if responses else "That is a complex subject."

    def _handle_how_are_you(self, character: CharacterProfile, player_tokens: List[str], player_username: str) -> str:
        """Handle 'how are you' questions - responses reflect character mood and personality"""
        responses = []
        
        # Base responses
        if CharacterTrait.FRIENDLY in character.traits:
            responses.extend([
                f"Hey {player_username}, I'm doing good! Thanks for asking.",
                f"Pretty good! How about you?",
                f"I'm alright. Things are busy but that's normal around here.",
                f"Doing well, {player_username}! Just working through some logs.",
                f"Life's good in the digital lane. Hope you're doing well too!",
            ])
        
        if CharacterTrait.OPTIMISTIC in character.traits:
            responses.extend([
                "Great! Always excited when new people join the network.",
                "Doing awesome! Lots of cool stuff happening.",
                "Fantastic! The BBS is buzzing with activity.",
                "Never better! The signal is clear and the future looks bright.",
                "Feeling good! We're making real progress here.",
            ])
        
        if CharacterTrait.MYSTERIOUS in character.traits:
            responses.extend([
                "I am functioning within expected parameters.",
                "Status: operational. All systems nominal.",
                "I exist. That is sufficient.",
                "The shadows are long, but I am still here.",
                "My state is a constant. Always watching, always waiting.",
            ])
        
        if CharacterTrait.NOSTALGIC in character.traits:
            responses.extend([
                "Doing okay. Sometimes I miss the old days, but this place keeps me going.",
                "I'm good. The community here reminds me of the old BBS days.",
                "Hanging in there. It's nice to have people to talk to.",
            ])
        
        # Paranoid logic - gated by PARANOIA1 token
        if CharacterTrait.PARANOID in character.traits and "PARANOIA1" in player_tokens:
            responses.extend([
                "Cautious. Always cautious. You can never be too careful.",
                "Wary. There's something in the air... can you feel it?",
                "Suspicious. Something doesn't feel right.",
            ])
        
        # Add character-specific responses
        if character.name == "rain":
            responses.extend([
                "Busy as usual! Got a ton of ops to coordinate. But I love it.",
                "Doing great! Just finished organizing the latest mission. Want to help?",
            ])
        elif character.name == "jaxkando":
            responses.extend([
                "EXCELLENT! Just cracked something new! Want to see?",
                "AMAZING! Games are flowing, systems are breaking, life is good!",
            ])
        elif character.name == "uncle-am":
            responses.extend([
                "i'm doing okay. been tuning the radio setup, picking up some interesting signals.",
                "pretty good! been helping people around the BBS. that's what i do.",
            ])
        
        return self._select_by_traits(character, responses, player_tokens) if responses else "I'm fine, thanks."
    
    def _handle_unlocked_area(
        self,
        character: CharacterProfile,
        area: str,
        player_tokens: List[str],
        player_username: str
    ) -> str:
        """Handle mentions of unlocked areas - characters respond based on their role"""
        responses = []
        
        if area == "games" and character.name == "jaxkando":
            responses = [
                f"YES! {player_username.upper()}, YOU UNLOCKED THE GAMES! COME PLAY WITH ME!\n\nI've got SIMULACRA_CORE ready for you. It's Glyphis' payload simulator - edit code, outsmart the warden, deliver the packet. Super fun!\n\n-jaxkando",
                f"GAMES MODULE UNLOCKED! AWESOME!\n\nCheck it out - there's SIMULACRA_CORE waiting for you. It's a hacking puzzle game. Think you can handle it?\n\n-jaxkando",
            ]
        elif area == "games":
            responses = [
                f"Ah, you've unlocked the games module. Jaxkando's been excited about that.",
                f"The games vault is open. Jaxkando handles all that - he's the gamesmaster.",
            ]
        
        elif area == "urgent ops" and character.name == "rain":
            responses = [
                f"Hey {player_username}, you've got access to Urgent Ops now! Perfect timing - I've got missions that need doing.\n\nCheck it out when you're ready. Some are simple, others... well, let's just say they're more interesting.\n\n-rain",
                f"Urgent Ops is unlocked! I coordinate all the missions there.\n\nIf you're looking for work, that's where you'll find it. Some jobs are straightforward data recovery, others involve... creative problem solving.\n\n-rain",
            ]
        elif area == "urgent ops":
            responses = [
                f"You've unlocked Urgent Ops. Rain handles all the missions there - she's the taskmaster.",
                f"Urgent Ops is available now. Rain coordinates everything in that module.",
            ]
        
        elif area == "pirate radio" and character.name == "uncle-am":
            responses = [
                f"hey {player_username}, you've got access to the pirate radio now! i'm the one running it.\n\nit's a looping broadcast - part DJ monologue, part world-building. tune in when you want to hear what's happening out there.\n\n-uncle-am",
                f"pirate radio unlocked! that's my domain.\n\ni've got my antenna set up, routing signals through the phone lines. it's wild what you can pick up if you know how to listen.\n\n-uncle-am",
            ]
        elif area == "pirate radio":
            responses = [
                f"Pirate Radio is unlocked. Uncle-am runs that - he's the radio engineer.",
                f"You can access Pirate Radio now. Uncle-am handles all the broadcasting.",
            ]
        
        elif area == "team info":
            responses = [
                f"You've unlocked Team Info. That's where you'll find dossiers on all of us.",
                f"Team Info is available. Check it out to learn more about the operators.",
                f"Curious about us? Team Info has the background you're looking for.",
                f"Dossiers are live. Read up on the crew in the Team Info module.",
            ]
        
        return random.choice(responses) if responses else f"You've unlocked {area}."
    
    def _handle_greeting(
        self,
        character: CharacterProfile,
        triggers: Dict[str, any],
        player_tokens: List[str],
        player_username: str
    ) -> str:
        """Handle greetings with character-appropriate style"""
        responses = []
        
        if CharacterTrait.FORMAL in character.traits:
            responses.extend([
                f"Greetings, {player_username}.",
                f"Hello. Your message has been received.",
                f"Salutations.",
            ])
        
        if CharacterTrait.CASUAL in character.traits:
            responses.extend([
                f"Hey {player_username}!",
                f"Hi there!",
                f"What's up?",
            ])
        
        if CharacterTrait.MYSTERIOUS in character.traits:
            responses.extend([
                f"Greetings, {player_username}. I've been monitoring your transmissions.",
                f"Hello. I see you've connected.",
                f"Acknowledged.",
            ])
        
        if CharacterTrait.FRIENDLY in character.traits:
            responses.extend([
                f"Hey {player_username}! Good to hear from you!",
                f"Hi! How's it going?",
                f"Hello! What's on your mind?",
                f"Hey there! Ready for some action?",
                f"Hi {player_username}! Nice to see you online.",
            ])
        
        return self._select_by_traits(character, responses, player_tokens) if responses else "Hello."
    
    def _handle_thanks(self, character: CharacterProfile, player_tokens: List[str], player_username: str) -> str:
        """Handle thank you messages"""
        responses = []
        
        if CharacterTrait.FRIENDLY in character.traits:
            responses.extend([
                f"You're welcome, {player_username}!",
                f"Happy to help!",
                f"Anytime!",
            ])
        
        if CharacterTrait.FORMAL in character.traits:
            responses.extend([
                "Acknowledgment received.",
                "No thanks necessary.",
                "You're welcome.",
            ])
        
        if CharacterTrait.MYSTERIOUS in character.traits:
            responses.extend([
                "Acknowledged. Stay vigilant.",
                "No gratitude necessary. We serve the same cause.",
                "Your appreciation is noted.",
                "Efficiency is the only thanks I require.",
                "Keep your head down and your signal clear. That's thanks enough.",
            ])
        
        return self._select_by_traits(character, responses, player_tokens) if responses else "You're welcome."
    
    def _handle_question(
        self,
        character: CharacterProfile,
        text: str,
        player_tokens: List[str],
        player_username: str
    ) -> str:
        """Handle questions based on character knowledge and personality"""
        responses = []
        
        if CharacterTrait.MYSTERIOUS in character.traits:
            responses.extend([
                "That is classified information. I can only reveal what you're cleared to know.",
                "Interesting question. The answer may not be what you expect.",
                "Query received. Accessing database... Results are inconclusive.",
            ])
        
        if CharacterTrait.TECHNICAL in character.traits:
            responses.extend([
                "Let me analyze that... The technical details are complex.",
                "That's a technical question. I can help, but it might get complicated.",
                "From a technical standpoint...",
            ])
        
        if CharacterTrait.FRIENDLY in character.traits:
            responses.extend([
                f"Good question, {player_username}! Let me think...",
                f"Hmm, that's interesting. Let me see if I can help.",
                f"I'm not entirely sure, but I can try to help you figure it out.",
                f"That's a head-scratcher! I'll do my best to find an answer for you.",
                f"Interesting query. Let me look into that for you, {player_username}.",
            ])
        
        return self._select_by_traits(character, responses, player_tokens) if responses else "I'm not sure how to answer that."
    
    def _generate_character_response(
        self,
        character: CharacterProfile,
        text: str,
        player_tokens: List[str],
        player_username: str
    ) -> str:
        """Generate a general response that reflects character personality"""
        responses = []
        
        # Character-specific default responses
        if character.name == "glyphis":
            responses = [
                "Your message has been logged. Expect further instructions soon.",
                "Interesting perspective. I'll forward this to the higher channels.",
                "I've decrypted your message. The pattern is becoming clearer.",
                "Acknowledged. Your theories are... intriguing.",
                "Message received. Trust no one. Question everything.",
                "I see you're beginning to understand. Keep digging deeper.",
                "The network hums with new data. Your contribution is noted.",
                "Patterns emerge from the chaos. Stay focused on the objective.",
            ]
        elif character.name == "rain":
            responses = [
                f"Hey {player_username}, got it. Let me know if you need anything.",
                "Noted! I'll keep that in mind.",
                "Thanks for the update. I'm here if you need me.",
                "Got it. Anything else?",
            ]
            # Add context about ops if player has access
            if any(token in player_tokens for token in ["AUDIO1", "LAPC1", "LAPC1A", "OPS_ACCESS"]):
                responses.append("If you're looking for work, check out Urgent Ops - I've got missions posted there.")
        elif character.name == "jaxkando":
            responses = [
                "COOL! Thanks for letting me know!",
                "AWESOME! Keep me posted!",
                "GOT IT! Want to play some games?",
                "THANKS FOR THE UPDATE!",
            ]
            # Add context about games if player has access
            if "GAMES1" in player_tokens:
                responses.append("You've got access to the Games module - come play SIMULACRA_CORE with me!")
        elif character.name == "uncle-am":
            responses = [
                f"thanks for letting me know, {player_username}.",
                "i appreciate you reaching out.",
                "got it. i'm here if you need anything.",
                "thanks for keeping me in the loop.",
            ]
            # Add context about radio if player has access
            if "RADIO_ACCESS" in player_tokens:
                responses.append("pirate radio is unlocked! i've set up a packet sniffer to help us patch into the relay. check it out and see if you can lock onto the signal.")
        
        return random.choice(responses) if responses else "Message received."
    
    def _handle_repetition(self, character: CharacterProfile, player_username: str) -> str:
        """Handle repetitive inputs from the player"""
        if character.name == "glyphis":
            return random.choice([
                "You are repeating yourself. Efficiency is required.",
                "I heard you the first time. Do not waste my cycles.",
                "Redundancy is a sign of a cluttered mind. Focus, operative."
            ])
        elif character.name == "rain":
            return random.choice([
                "Yeah, you mentioned that. Anything else?",
                "Already got it! Let's move on.",
                "I'm on it, no need to say it twice!"
            ])
        elif character.name == "jaxkando":
            return random.choice([
                "I KNOW! I KNOW! YOU SAID THAT ALREADY!",
                "REPETITION IS FOR LOSERS! LET'S DO SOMETHING NEW!",
                "GOT IT THE FIRST TIME! RELAX!"
            ])
        elif character.name == "uncle-am":
            return random.choice([
                "oh, i think we already talked about that. something else on your mind?",
                "i hear you! just like a looping broadcast, haha.",
                "no worries, i remember you said that. what's next?"
            ])
        return "You're repeating yourself."

    def _select_by_traits(self, character: CharacterProfile, responses: List[str], player_tokens: List[str]) -> str:
        """Select a response weighted by character traits"""
        if not responses:
            return self._character_fallback(character)
        
        # Gating responses by paranoia if the token isn't present
        is_paranoid_active = "PARANOIA1" in player_tokens
        
        # We need to find which trait each response might belong to (if possible)
        # For simplicity in this implementation, we will use the trait weights 
        # to influence the selection of ALL responses by picking a 'active trait' for this session
        
        # Calculate total weight
        total_weight = sum(character.trait_weights.values())
        r = random.uniform(0, total_weight)
        
        selected_trait = character.traits[0]
        upto = 0
        for trait, weight in character.trait_weights.items():
            if upto + weight >= r:
                selected_trait = trait
                break
            upto += weight
            
        # If the selected trait is paranoid but we don't have the token, fallback to a friendly or formal one
        if selected_trait == CharacterTrait.PARANOID and not is_paranoid_active:
            fallback_traits = [t for t in character.traits if t != CharacterTrait.PARANOID]
            selected_trait = random.choice(fallback_traits) if fallback_traits else CharacterTrait.FORMAL

        # For now, we'll just return a random choice from the provided list,
        # but in a more complex system, responses would be tagged with traits.
        # Instead, let's use the selected_trait to vary the list slightly if we can.
        
        return random.choice(responses)
    
    def _character_fallback(self, character: CharacterProfile) -> str:
        """Character-specific fallback when no triggers are met"""
        if character.name == "glyphis":
            return random.choice([
                "Your input is noted. Connection remains stable.",
                "Acknowledged. Continue your assessment.",
                "Data received. The network is processing."
            ])
        elif character.name == "rain":
            return random.choice([
                "Got your message. Let me know if you need any tasks.",
                "Noted. I'll be here coordination-side.",
                "Thanks for the update. Keep at it."
            ])
        elif character.name == "jaxkando":
            return random.choice([
                "COOL! GOING BACK TO THIS CRACK NOW!",
                "GOT IT! TALK LATER, GAMES TO PLAY!",
                "NICE! KEEP ME POSTED ON YOUR PROGRESS!"
            ])
        elif character.name == "uncle-am":
            return random.choice([
                "thanks for reaching out. i'm just here tuning the frequencies.",
                "got it. catch you in the next broadcast!",
                "appreciate the update. talk soon."
            ])
        return "Message received."

    def _generic_response(self, email_subject: str, email_body: str) -> str:
        """Fallback generic response if character not found"""
        return "Your message has been received and logged."
    
    def _get_transitions(self, character: CharacterProfile, num_responses: int) -> List[str]:
        """Get character-appropriate transition phrases for combining multiple responses"""
        if num_responses <= 1:
            return []
        
        transitions = []
        
        if CharacterTrait.FRIENDLY in character.traits:
            transitions = [
                "also, ",
                "and ",
                "speaking of that, ",
                "on another note, ",
                "by the way, ",
            ]
        elif CharacterTrait.FORMAL in character.traits:
            transitions = [
                "Additionally, ",
                "Furthermore, ",
                "Regarding your other question, ",
                "To address your other point, ",
            ]
        elif CharacterTrait.CASUAL in character.traits:
            transitions = [
                "also, ",
                "oh, and ",
                "speaking of which, ",
                "btw, ",
            ]
        elif CharacterTrait.MYSTERIOUS in character.traits:
            transitions = [
                "Separately, ",
                "On another matter, ",
                "Regarding your other query, ",
            ]
        else:
            transitions = [
                "also, ",
                "and ",
                "regarding your other question, ",
            ]
        
        # Return transitions for the gaps between responses (num_responses - 1)
        return [random.choice(transitions) for _ in range(num_responses - 1)]
    
    def _combine_responses(self, response_parts: List[str], transitions: List[str]) -> str:
        """Combine multiple response parts with transitions or paragraph breaks"""
        if not response_parts:
            return ""
        
        if len(response_parts) == 1:
            return response_parts[0]
        
        combined = response_parts[0]
        
        for i, transition in enumerate(transitions):
            if i + 1 < len(response_parts):
                next_part = response_parts[i + 1]
                
                # Use paragraph breaks for better readability when combining different topics
                # This creates natural separation between responses
                # The _format_response method will handle the \n\n formatting correctly
                combined += "\n\n" + next_part
        
        return combined

