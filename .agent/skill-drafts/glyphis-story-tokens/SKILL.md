---
name: glyphis-story-tokens
description: Use this skill when a task involves progression tokens, story-beat unlocks, token grants, token-gated content, or debugging which story trigger should fire in GlyphisIO BBS. It covers the BBS, Bradsonic OS, email delivery, urgent ops, pirate radio, and outside BBS token flow.
---

# Glyphis Story Tokens

## Overview

Use this skill to answer four questions quickly:

1. What does a token mean in story terms?
2. What grants it?
3. What reacts to it?
4. Is the token canonical, legacy, or drifted?

Start with [`references/token-catalog.md`](references/token-catalog.md) for token meaning and status. Then open [`references/trigger-map.md`](references/trigger-map.md) for grant sites, reaction sites, and common debugging paths.

## Workflow

### 1. Confirm the canonical token

- Read `tokens.py` first. Treat it as the primary catalogue for names and intended meaning.
- Normalize case with `normalize_token()` semantics before comparing saved state, JSON, or code paths.
- If a token appears in content but not in `tokens.py`, treat it as drift until proven otherwise.

### 2. Classify the trigger type

Most story tokens come from one of these paths:

- Direct `grant_token(...)` calls in `main.py`
- `grant_token(...)` calls in `Data/OS/OS_Mode.py`
- Generic email read rewards via `self.email_token_rewards`
- Urgent Ops session callbacks or `pending_token_grants`
- Pirate radio or outside-BBS callback hooks
- JSON-authored email delivery in `systems/email_db.py`

### 3. Check reactions, not just grants

After finding where a token is awarded, always check what consumes it:

- module unlocks in `main.py`
- inbox auto-send conditions in `Data/emails_inbox.json` and `systems/email_db.py`
- feed post requirements in `Data/main_terminal_feed.json`
- note, pulse, and desktop behavior in `Data/OS/OS_Mode.py`
- NPC tone changes in `systems/enhanced_npc.py`

### 4. Preserve the mission chain

For story edits, verify the whole chain:

- grant site
- save/state refresh through `main.py:grant_token()`
- authored email or post unlock
- UI pulse or mission-note change
- next token in the chain

## Known Drift

- `PARANOIA1` is used by content and NPC logic, but `tokens.py` defines `PARANOIA`.
- `ECHOCHAMBER` is used in Pirate Radio and OS notes, but is not currently defined in `tokens.py`.
- Some tokens are defined but appear planned or partially wired: `OPS_ACCESS`, `TEAM_ACCESS`, `SUSPICION`, `REVELATION`, `PSEM2`.

## Fast Search Patterns

Use these when tracing a token:

```powershell
rg -n "TOKEN_NAME" main.py Data systems tokens.py
rg -n "grant_token\\(|has_token\\(|token_name|required_tokens|tokens_required" main.py Data systems
```

## What This Skill Is For

- explaining token-to-story progression
- adding or fixing a token trigger
- checking why an email or post did not unlock
- tracing School Hack, Jax/Astro Miner, radio, or outside-BBS progression
- spotting token drift between code and authored JSON
