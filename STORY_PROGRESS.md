# GlyphisIO BBS: Story Progress Summary

## 📖 The Story Arc (Planned)

The game follows a **6-act narrative structure**:

### **ACT 1: THE INVITATION** ✅ *Implemented*
- Player receives an encrypted, anonymous invitation to join GlyphisIO BBS
- First contact with **glyphis** - the mysterious sysop
- Introduction to the BBS world and its operators
- **Status**: Fully implemented - welcome email system active

### **ACT 2: INITIAL EXPLORATION** ✅ *Partially Implemented*
- Player explores the BBS modules:
  - ✅ **Front Post Board** - Community news and announcements
  - ✅ **Email System** - Communication with team members
  - ✅ **Games** - SIMULACRA_CORE challenge unlocked
  - ✅ **Urgent Tasks** - LAPC-1 driver challenge available
  - ✅ **Team Info** - Character bios available
  - ⏳ **Pirate Radio** - Placeholder (not yet functional)
- Player sets their username and begins building relationships
- **Status**: Core modules functional, story progression through emails

### **ACT 3: BECOMING PART OF THE COMMUNITY** ⏳ *In Progress*
- Player completes initial challenges (SIMULACRA_CORE, LAPC-1 driver)
- Receives congratulations from glyphis and uncle-am
- Tasks become more complex and morally ambiguous
- **Status**: Early stages - first challenges complete, relationship building begins

### **ACT 4: THE SUSPICION** ❌ *Not Yet Implemented*
- Paranoia spreads through the network
- glyphis suspects an FBI infiltrator
- Tension builds, friendships fracture
- **Status**: Planned but not yet in game

### **ACT 5: THE REVELATION** ❌ *Not Yet Implemented*
- The twist: **You are the agent**
- Player realizes they've been undercover all along
- Loyalty conflict emerges
- **Status**: Planned but not yet in game

### **ACT 6: THE CONFLICT** ❌ *Not Yet Implemented*
- Final choice: Duty vs. Loyalty
- Player decides the fate of GlyphisIO BBS
- **Status**: Planned but not yet in game

---

## 🌍 The World Setting

**Time**: 1989  
**Location**: Tokyo (now called "Pacifica Isles" - American-administered Japan)

### Alternate History Backdrop:
- **1945**: Imperial Family destroyed at Hiroshima Castle
- Japan becomes **"The American Pacifica Isles"** - a US-administered state
- Japanese language/culture suppressed
- American tech dominates (Bradsonic, NeoDrive instead of Sony, Panasonic)
- Underground hacker youth culture emerges, desperate to reclaim lost heritage

### The GlyphisIO BBS Operators:

1. **glyphis** (@ciphernet.net)
   - Sysop, founder, mysterious architect
   - Mechanical yet poetic voice
   - Watches everything, rarely participates directly

2. **rain** (@ciphernet.net)
   - Operations coordinator, "The Static Runner"
   - Organizes tasks and urgent ops
   - Warm, practical, keeps the BBS running

3. **jaxkando** (@ciphernet.net)
   - Gamesmaster, curator of digital challenges
   - Creates hacking puzzles and text adventures

4. **uncle-am** (@ciphernet.net)
   - Radio engineer, "The Fire in the Static"
   - Runs pirate radio broadcasts
   - Nostalgic optimist, community moderator
   - Knows the suppressed history

---

## 🎮 Current Game Implementation Status

### ✅ **Fully Functional Systems:**

1. **BBS Interface**
   - Authentic retro terminal aesthetic (cyan on black)
   - Full keyboard navigation (TAB, arrows, ENTER, ESC)
   - Loading screen with connection sequence

2. **Email System**
   - Inbox/Outbox management
   - Compose messages
   - NPC responders (glyphis, rain, jaxkando, uncle-am)
   - Token-gated email delivery
   - Conversation history tracking

3. **Front Post Board**
   - Community announcements
   - Token-gated posts
   - Dynamic content based on player progress

4. **Games Module**
   - **SIMULACRA_CORE** ✅
     - Code editing puzzle game
     - Edit assembly code to deliver packets
     - Tracks best Time Cycle Score (TCS)
     - Unlocks after username is set
     - Grants UNCLEAM1 token on level 1 completion

5. **Urgent Tasks Module**
   - **LAPC-1 Driver Challenge** ✅
     - Assembly programming challenge from uncle-am
     - Write driver code to power on sound card
     - 7-node progression system
     - Visual waveform feedback
     - Grants tokens: LAPC1_BRIEF, LAPC1A, LAPC1_NODE1-7, AUDIO_ON

6. **Team Info Module**
   - Character bios for all operators
   - Dynamic content based on relationships

### ⏳ **Partially Implemented:**

1. **Pirate Radio**
   - Module exists but audio playback not functional
   - Placeholder for future implementation

2. **Story Progression**
   - Early emails implemented (welcome, username acknowledgment, SIMULACRA congrats, uncle-am audio ops)
   - Relationship building in progress
   - Later story acts not yet implemented

### ❌ **Not Yet Implemented:**

1. **Story Acts 4-6** (Suspicion, Revelation, Conflict)
2. **Advanced NPC conversations** (beyond initial emails)
3. **Moral choice system** (duty vs. loyalty)
4. **Full audio system** (pirate radio broadcasts)
5. **Additional games** (beyond SIMULACRA_CORE)
6. **Advanced task system** (grey-area jobs, surveillance missions)

---

## 🎯 Player Progression Path (Current)

### **Starting Point:**
1. Player receives welcome email from glyphis
2. Must set username to unlock further content
3. Token: **PSEM** (Primary System Enablement Module) - unlocks email system

### **Early Progression:**
1. ✅ Set username → Token: **USERNAME_SET**
2. ✅ Receive email from glyphis directing to games
3. ✅ Token: **GAMES1** - unlocks games module
4. ✅ Play SIMULACRA_CORE → Complete level 1 → Token: **UNCLEAM1**

### **Current Available Content:**
1. ✅ **SIMULACRA_CORE** game - Code editing challenge
2. ✅ **LAPC-1 Driver Challenge** - Assembly programming task
3. ✅ Email conversations with operators
4. ✅ Front Post Board - Community posts
5. ✅ Team Info - Character bios

### **Token System:**
The game uses tokens to gate content and track progress:
- **PSEM** - Email system unlocked
- **USERNAME_SET** - Username registered
- **PIN_SET** - Login PIN configured
- **GAMES1** - Games module unlocked
- **AUDIO1** - Audio operations briefing
- **LAPC1_BRIEF** - LAPC-1 challenge unlocked
- **LAPC1A, LAPC1_NODE1-7** - LAPC-1 progression milestones
- **AUDIO_ON** - LAPC-1 fully completed
- **UNCLEAM1** - Earned uncle-am's trust
- **SUSPICION, PARANOIA, REVELATION** - Planned story arc tokens

---

## 📧 Email Story Threads (Implemented)

### **From glyphis:**
1. ✅ Welcome message (auto-sent on start)
2. ✅ Username acknowledgment (after username set)
3. ✅ SIMULACRA congratulations (after completing level 1)

### **From uncle-am:**
1. ✅ Audio operations briefing (after SIMULACRA progress)
   - Introduces LAPC-1 driver challenge
   - Mentions soundcard configuration
   - Directs player to Urgent Ops

### **Planned (Not Yet Implemented):**
- Ongoing conversations with rain (task assignments)
- jaxkando game challenges
- Story progression emails (suspicion, revelation, conflict)
- Relationship-building conversations

---

## 🎨 Game Aesthetic & Tone

**Visual Style:**
- Retro BBS terminal (1980s-1990s)
- Cyan text on black background
- Monospaced fonts (Pixellari)
- Authentic loading sequences

**Atmospheric Tone:**
- Community warmth (like Animal Crossing)
- Hacker mystique (like The Matrix)
- Creative intimacy (like Hypnospace Outlaw)
- World depth (like GTA)

**Themes:**
- Identity and Deception
- Morality and Loyalty
- Human vs. Machine (is glyphis real or AI?)
- Surveillance and Resistance
- The Cost of Connection

---

## 🚀 Where You Are Now

**Current Story Position: ACT 2 → ACT 3 Transition**

You've completed:
- ✅ Initial invitation and welcome
- ✅ Username registration
- ✅ First challenge (SIMULACRA_CORE)
- ✅ Technical challenge (LAPC-1 driver)

**What's Next (In Story):**
- Building deeper relationships with operators
- More complex tasks from rain
- Grey-area jobs (local networks, school servers, media outlets)
- Growing sense of belonging to the community
- **Then**: Suspicion phase begins (ACT 4)

**What's Next (In Development):**
- Implement remaining story acts (4-6)
- Expand NPC conversation system
- Add more games/challenges
- Implement moral choice system
- Activate pirate radio broadcasts
- Add more complex tasks and missions

---

## 📝 Summary

**Story Progress: ~30% Complete**
- ✅ Acts 1-2: Fully implemented
- ⏳ Act 3: Early stages (first challenges complete)
- ❌ Acts 4-6: Not yet implemented

**Game Systems: ~70% Complete**
- ✅ Core BBS interface and navigation
- ✅ Email system with NPC responders
- ✅ Two playable games/challenges
- ✅ Token-based progression system
- ⏳ Story progression emails (partial)
- ❌ Advanced narrative branching
- ❌ Moral choice system
- ❌ Audio system

**Current Player Experience:**
Players can explore the BBS, communicate with operators, complete technical challenges, and begin building relationships. The foundation is solid, but the deeper narrative arcs (suspicion, revelation, conflict) are not yet playable.

---

*"GLYPHISIO BBS isn't just a place you log into. It's a place that logs into you."*
