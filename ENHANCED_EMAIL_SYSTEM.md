# Enhanced Email Response System

## Overview

The Enhanced Email Response System uses character traits and context-aware triggers to generate believable, personality-driven responses from NPCs. The system is completely local (no external APIs) and maintains suspension of disbelief through:

- **Character Traits**: Each NPC has defined personality traits that influence their response style
- **Context Awareness**: Responses adapt based on player's unlocked content (tokens)
- **Trigger Detection**: Specific patterns are detected (help requests, ASL, "how are you", unlocked areas)
- **Conversation History**: Tracks previous interactions for future enhancements

## How It Works

### Character Profiles

Each NPC has a `CharacterProfile` that defines:
- **Traits**: Personality characteristics (formal, casual, mysterious, friendly, technical, etc.)
- **Trait Weights**: How strongly each trait influences responses
- **Speech Patterns**: Character-specific phrases and style
- **Interests**: Topics the character cares about
- **Catchphrases**: Signature phrases they use

### Current Characters

1. **glyphis@ciphernet.net** (sysop)
   - Traits: Mysterious, Formal, Technical
   - Style: Cryptic, surveillance-focused, minimal personal info

2. **rain@ciphernet.net** (taskmaster)
   - Traits: Casual, Friendly, Optimistic
   - Style: Direct, helpful, mission-focused

3. **jaxkando@ciphernet.net** (gamesmaster)
   - Traits: Casual, Humorous, Technical
   - Style: Excited, ALL CAPS, game-focused

4. **uncle-am@ciphernet.net** (radio engineer)
   - Traits: Friendly, Nostalgic, Emotional
   - Style: Lowercase, community-focused, caring

### Trigger Detection

The system detects specific patterns in player emails:

1. **Help Requests**: "help", "assist", "how do I", "can you", etc.
   - Characters respond based on their traits
   - Context-aware suggestions based on unlocked areas

2. **ASL Requests**: "asl", "where are you from", "tell me about yourself"
   - Characters reveal information based on their personality
   - Glyphis: Mysterious, minimal info
   - Uncle-am: Friendly, shares more

3. **How Are You**: "how are you", "how's it going", "what's up"
   - Responses reflect character mood and personality
   - Optimistic characters are upbeat, nostalgic characters reflect on the past

4. **Unlocked Area Mentions**: Detects when player mentions areas they've unlocked
   - Games, Urgent Ops, Team Info, Pirate Radio, Email
   - Characters respond based on their role in that area

5. **Greetings**: "hello", "hi", "hey"
   - Character-appropriate greeting style

6. **Thanks**: "thank", "thanks", "appreciate"
   - Character-appropriate acknowledgment

7. **Questions**: Detects question marks and question words
   - Responses vary by character knowledge and personality

### Response Priority

Responses are generated in priority order:
1. Specific triggers (help, ASL, how are you, unlocked areas)
2. Greetings
3. Thanks
4. Questions
5. General character-appropriate responses

### Context Integration

The system tracks:
- **Player Tokens**: What content the player has unlocked
- **Latest Unlocked Area**: Most recent area unlocked (for context)
- **Conversation History**: Previous interactions (stored for future use)

## Usage

The system is automatically integrated into the email sending flow in `main.py`. When a player sends an email to an NPC:

```python
response_body = self.npc.generate_response(
    sender_email="glyphis@ciphernet.net",
    email_subject=email.subject,
    email_body=email.body,
    player_tokens=player_tokens,
    player_username=self.player_email
)
```

## Extending the System

### Adding New Characters

1. Add character profile to `_initialize_characters()` in `systems/enhanced_npc.py`:

```python
"newcharacter@ciphernet.net": CharacterProfile(
    name="newcharacter",
    email="newcharacter@ciphernet.net",
    traits=[CharacterTrait.FRIENDLY, CharacterTrait.TECHNICAL],
    trait_weights={
        CharacterTrait.FRIENDLY: 2.0,
        CharacterTrait.TECHNICAL: 1.5,
    },
    speech_patterns={
        "greeting": "Hey there!",
        "closing": "-newcharacter",
    },
    interests=["topic1", "topic2"],
    catchphrases=["Signature phrase here"]
)
```

2. Add email handling in `main.py` (if needed for special logic)

### Adding New Triggers

1. Add detection pattern in `_detect_triggers()`:

```python
triggers["new_trigger"] = re.search(pattern, text) is not None
```

2. Add handler method:

```python
def _handle_new_trigger(self, character, ...):
    """Handle new trigger with character-appropriate responses"""
    responses = []
    # Add trait-based responses
    return self._select_by_traits(character, responses)
```

3. Add to `_build_response()` priority chain

### Adding New Traits

1. Add to `CharacterTrait` enum:

```python
class CharacterTrait(Enum):
    NEW_TRAIT = "new_trait"
```

2. Add trait-based responses in relevant handlers
3. Update character profiles to use the new trait

### Adding New Unlocked Areas

1. Add to `unlocked_areas` dictionary in `_detect_triggers()`:

```python
"new_area": ["keyword1", "keyword2", "keyword3"]
```

2. Add token mapping:

```python
area_tokens["new_area"] = ["TOKEN1", "TOKEN2"]
```

3. Add handler responses in `_handle_unlocked_area()`

## Example Interactions

### Help Request to Rain

**Player**: "Hey rain, I need help with something"

**Response** (Casual + Friendly traits):
> "Hey operative, happy to help! What do you need?"
> 
> "If you're looking for work, check out Urgent Ops - I've got missions posted there."

### ASL Request to Glyphis

**Player**: "asl?"

**Response** (Mysterious + Formal traits):
> "I am the sysop. That is all you need to know.
> 
> I exist in the spaces between packets. Location is irrelevant when you are everywhere."

### Mentioning Unlocked Games to Jaxkando

**Player**: "I just unlocked the games module!"

**Response**:
> "YES! OPERATIVE, YOU UNLOCKED THE GAMES! COME PLAY WITH ME!
> 
> I've got SIMULACRA_CORE ready for you. It's Glyphis' payload simulator - edit code, outsmart the warden, deliver the packet. Super fun!
> 
> -jaxkando"

## Benefits

1. **No External APIs**: Completely local, fast, and reliable
2. **Maintains Suspension of Disbelief**: Character-consistent responses
3. **Context-Aware**: Adapts to player progress
4. **Extensible**: Easy to add new characters, traits, and triggers
5. **On Rails**: Controlled responses ensure narrative consistency

## Future Enhancements

Potential improvements:
- Conversation memory (reference previous emails)
- Emotional state tracking (characters remember events)
- Multi-turn conversations (follow-up questions)
- Dynamic trait adjustment (characters change over time)
- More sophisticated pattern matching (NLP-like without APIs)

