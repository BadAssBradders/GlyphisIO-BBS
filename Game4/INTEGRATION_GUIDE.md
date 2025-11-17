# DEBUGGER.BAS - BBS Game Integration Guide

## Overview

**DEBUGGER.BAS** is a retro BASIC debugging game where players must fix corrupted code to extract an access token. The game combines:
- **Technical authenticity**: Real BASIC code that players must debug
- **Visual appeal**: Animated network trace visualization
- **Progressive difficulty**: From syntax errors to logic bugs
- **Leaderboard potential**: Scored on time, efficiency, and edit count

## Game Features

### What Makes It Special

1. **Real Programming**: Players debug actual BASIC code, not a puzzle dressed as code
2. **Visual Feedback**: The program generates graphics when fixed (animated network trace)
3. **Multiple Bug Types**:
   - **Syntax Bugs**: Missing loop variables, wrong operators
   - **Logic Bugs**: Incorrect token generation algorithms
   - **Optimization**: Can be refined for better scores

4. **Perfect for Narrative**: Generates a token that unlocks BBS content

## Integration with main.py

### Step 1: Import the Game

Add this import near the top of your `main.py`:

```python
import debugger_game
```

### Step 2: Add to Games Menu

In your games menu/listing code, add DEBUGGER.BAS as an option:

```python
# In your draw_games_menu() or equivalent function:
games_list = [
    {
        'id': 1,
        'name': 'DEBUGGER.BAS',
        'status': 'UNLOCKED' if self.has_token('username_set') else 'LOCKED',
        'description': 'Network trace simulator - FIX THE BUGS',
        'author': 'glyphis'
    },
    # ... other games
]
```

### Step 3: Launch the Game

When player selects DEBUGGER.BAS:

```python
def launch_game(self, game_id):
    if game_id == 1:  # DEBUGGER.BAS
        # Hide the BBS window temporarily
        self.bbs_window_hidden = True
        
        # Run the game (it opens its own pygame window)
        result = debugger_game.run_debugger_game()
        
        # Restore BBS window
        self.bbs_window_hidden = False
        
        # Process results
        if result['completed'] and result['token']:
            # Grant token to player
            self.grant_token('debugger_complete')
            
            # Save completion stats
            self.save_game_result('debugger', {
                'score': result['score'],
                'time': result['time'],
                'edits': result['edits'],
                'token': result['token']
            })
            
            # Send congratulations email from Glyphis
            self.send_debugger_completion_email(result)
```

### Step 4: Handle Return Values

The game returns a dictionary:

```python
{
    'completed': True/False,      # Whether player finished successfully
    'token': 'GPGLPH' or None,    # The extracted token (if completed)
    'score': 87,                  # Efficiency score (0-100)
    'time': 263.5,                # Completion time in seconds
    'edits': 4                    # Number of code edits made
}
```

### Step 5: Add Post-Game Email

After successful completion, send an email from Glyphis:

```python
def send_debugger_completion_email(self, result):
    score = result['score']
    time_formatted = f"{int(result['time'] // 60)}:{int(result['time'] % 60):02d}"
    
    # Determine Glyphis's response based on performance
    if result['edits'] == 2 and result['time'] < 180:
        message = "OPTIMAL. TWO EDITS IN UNDER THREE MINUTES."
        rating = "EXCEPTIONAL"
    elif result['edits'] <= 3 and result['time'] < 300:
        message = "EFFICIENT. YOU UNDERSTAND THE FUNDAMENTALS."
        rating = "COMPETENT"
    elif result['edits'] <= 5:
        message = "ACCEPTABLE. YOU GOT THERE EVENTUALLY."
        rating = "ADEQUATE"
    else:
        message = "SLOW. BUT RESULTS ARE WHAT MATTER HERE."
        rating = "SUFFICIENT"
    
    body = f"""DEBUGGER.BAS ANALYSIS:

{message}

PERFORMANCE METRICS:
- Time: {time_formatted}
- Edits: {result['edits']}
- Efficiency: {result['score']}/100
- Rating: {rating}

TOKEN EXTRACTED: {result['token']}
ACCESS LEVEL: UPGRADED

THE NETWORK MODULES ARE NOW AVAILABLE TO YOU.
RAIN WILL CONTACT YOU SHORTLY WITH YOUR FIRST REAL TASK.

- GLYPHIS"""

    email = Email(
        sender="glyphis@ciphernet.net",
        recipient=self.player_email,
        subject="RE: DEBUGGER.BAS - ANALYSIS",
        body=body
    )
    
    self.inbox.append(email)
```

## Game Mechanics

### The Three Bugs

Players must fix:

1. **Line 190**: `NEXT` → `NEXT I` (missing loop variable)
2. **Line 220**: `TRACE=>100` → `TRACE>=100` (wrong operator)
3. **Lines 340-360**: Token generation is hard-coded instead of derived from node coordinates

### Optimal Solution

The perfect solution requires only 2 edits:
1. Fix line 190: `190 NEXT I`
2. Fix line 220: `220 IF TRACE>=100 THEN GOTO 260`

The token generation bug (lines 340-360) can be ignored if players just want to extract *a* token. For a truly optimal solution, players would need to fix it to generate the correct token from coordinates.

### Scoring System

```
Score = Edit Score + Time Score

Edit Score (0-50 points):
- 2 edits: 50 points
- 3 edits: 40 points
- 4 edits: 30 points
- 5+ edits: 20 points

Time Score (0-50 points):
- Under 2 min: 50 points
- 2-4 min: 40 points
- 4-6 min: 30 points
- 6-8 min: 20 points
- Over 8 min: 10 points
```

## UI/UX Integration Tips

### Visual Consistency

The game uses a cyan-on-black aesthetic matching the BBS. Colors used:
- **CYAN** (#00FFFF): Primary UI elements
- **DARK_CYAN** (#00B4B4): Secondary text
- **GREEN** (#00FF00): Code/output
- **RED** (#FF6464): Errors
- **YELLOW** (#FFFF64): Status messages

### Window Handling

The game opens in a separate pygame window (1200x700). Consider:

1. **Pause BBS rendering** while game is active
2. **Center the game window** on screen
3. **Restore focus** to BBS when game closes

### Loading Screen

Show a transition when launching:

```
╔═══════════════════════════════════════════╗
║  LOADING DEBUGGER.BAS...                 ║
║                                           ║
║  [████████████████░░░░░░░░░░] 75%        ║
║                                           ║
║  INITIALIZING BASIC INTERPRETER           ║
║  LOADING CORRUPTED CODE                   ║
║  STAND BY...                              ║
╚═══════════════════════════════════════════╝
```

## Leaderboard Implementation

### Data Structure

Store completion records:

```python
{
    'username': 'player_name',
    'score': 87,
    'time': 263.5,
    'edits': 4,
    'timestamp': '1989-11-07 14:23:45',
    'token': 'GPGLPH'
}
```

### Display Format

```
╔═══════════════════════════════════════════════════════════╗
║ DEBUGGER.BAS - GLOBAL LEADERBOARD                        ║
╠═══════════════════════════════════════════════════════════╣
║                                                           ║
║  RANK | PLAYER          | SCORE | TIME  | EDITS         ║
║  ───────────────────────────────────────────────────     ║
║   1   | RAIN            |  100  | 02:31 |   2           ║
║   2   | JAXKANDO        |   94  | 03:08 |   3           ║
║   3   | PHANTOM_ZERO    |   94  | 03:45 |   3           ║
║   4   | CIPHER_KNIGHT   |   91  | 03:22 |   3           ║
║   5   | GHOST_WIRE      |   87  | 04:11 |   4           ║
║  ...                                                      ║
║  23   | [YOUR_USERNAME] |   87  | 04:23 |   4           ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
```

## Advanced: Multiple Difficulty Levels

You can create variations:

### Easy Mode
- Fewer bugs (only syntax errors)
- Longer time limits
- Hints available

### Hard Mode
- More subtle bugs
- Optimization required
- Tighter time limits

### Expert Mode
- Multiple logic errors
- Require correct token generation
- Leaderboard separate from normal mode

## Troubleshooting

### Game Window Doesn't Appear

Check:
1. Pygame is installed: `pip install pygame`
2. Display environment variables are set
3. No other modal dialogs blocking

### Game Crashes on Launch

Common issues:
1. Missing imports
2. Font loading failures (fallback to default font)
3. Resolution/scaling issues

### Controls Not Working

Verify:
- Pygame event loop is running
- Window has focus
- No key mapping conflicts

## Testing Checklist

Before deployment:

- [ ] Game launches from BBS menu
- [ ] Code editor displays properly
- [ ] Can edit lines and save changes
- [ ] RUN command executes program
- [ ] Bugs are detectable (syntax errors shown)
- [ ] Fixed program runs successfully
- [ ] Token is extracted and returned
- [ ] Results are saved correctly
- [ ] Post-game email is sent
- [ ] Leaderboard updates
- [ ] Can return to BBS seamlessly

## Performance Notes

- **Memory**: ~50MB with pygame loaded
- **CPU**: Minimal (only during animation)
- **Startup**: <1 second to load
- **Average playtime**: 3-7 minutes

## Future Enhancements

Ideas for expansion:

1. **Daily Challenges**: New buggy code each day
2. **Custom Levels**: Let players create their own buggy code
3. **Co-op Mode**: Two players fix code together
4. **Time Attack**: Speed-run mode with simplified bugs
5. **Code Golf**: Minimize edits AND lines of code
6. **Themed Variations**: Different visualizations (not just networks)

## Support

For questions or issues, refer to:
- Main documentation: `DEBUGGER.BAS` docstring
- Test suite: `test_debugger.py`
- Diagnostic tools: `test_diagnostic.py`

---

**Remember**: This game is a test. Glyphis is watching. The player's performance here determines their access level in the BBS. Make it feel consequential.
