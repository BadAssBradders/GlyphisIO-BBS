# DEBUGGER.BAS - Retro BASIC Debugging Game

## 🎮 What Is This?

A fully functional hacking puzzle game where players must debug corrupted BASIC code to extract an access token. Built for the GlyphisIO BBS narrative game as the player's first technical challenge from Glyphis.

## ✨ Features

- **Real BASIC Interpreter**: Execute and debug actual BASIC programs
- **Visual Output**: Animated network trace graphics when code is fixed
- **Progressive Challenge**: Syntax errors → Logic bugs → Optimization
- **Leaderboard Ready**: Scored on time, efficiency, and edit count
- **Perfect BBS Integration**: Matches cyan-on-black retro aesthetic

## 🎯 How It Works

Players receive a corrupted BASIC program that simulates a network trace. The program has bugs that prevent it from running correctly. Players must:

1. **Identify bugs** through error messages and testing
2. **Edit the code** to fix syntax and logic errors
3. **Run the program** until it completes successfully
4. **Extract the token** that proves their technical competence

## 🐛 The Bugs

Three bugs are hidden in the code:

1. **Line 190**: Missing loop variable (`NEXT` should be `NEXT I`)
2. **Line 220**: Wrong operator (`=>` should be `>=`)
3. **Lines 340-360**: Hard-coded token (optional advanced fix)

## 📁 Files Included

- **`debugger_game.py`** - Complete game implementation (750+ lines)
- **`INTEGRATION_GUIDE.md`** - How to add this to your BBS
- **`BUG_REFERENCE.md`** - Quick reference for players and developers
- **`test_debugger.py`** - Test suite (optional, for verification)

## 🚀 Quick Start

### For BBS Developers

1. Copy `debugger_game.py` to your project directory
2. Import it: `import debugger_game`
3. Call it when player selects the game: `result = debugger_game.run_debugger_game()`
4. Handle the returned result dict (token, score, time, edits)

### For Testing

```bash
python3 debugger_game.py
```

This runs the game standalone for testing.

## 🎨 Screenshots (ASCII Preview)

```
╔═══════════════════════════════════════════════════════════╗
║  DEBUGGER.BAS - EDIT MODE     │ PROGRAM OUTPUT           ║
╠═══════════════════════════════════════════════════════════╣
║ 10 REM NETWORK TRACE SIMULATOR│                          ║
║ 20 REM BY: GLYPHIS            │    ●────●        ●       ║
║ ...                            │    │     \      /        ║
║ 190 NEXT          ← BUG!       │    │      ●────●         ║
║ ...                            │    │       \  /          ║
║ 220 IF TRACE=>100 ← BUG!       │    ●────────●●           ║
║ ...                            │                          ║
║                                │  [TRACE: ████░ 45%]      ║
╠═══════════════════════════════════════════════════════════╣
║ > RUN_                                                    ║
║ ERROR: Line 190: NEXT without FOR                        ║
╚═══════════════════════════════════════════════════════════╝
```

## 🏆 Scoring System

- **Edit Score** (0-50): Fewer edits = higher score
- **Time Score** (0-50): Faster completion = higher score
- **Perfect**: 2 edits in under 2 minutes = 100 points

## 🎓 What Makes This Special

Unlike typical "hacking games" that simulate hacking with unrelated puzzles, **DEBUGGER.BAS makes you do the real thing**:

- ✅ Read actual code
- ✅ Understand program logic
- ✅ Fix syntax errors
- ✅ Debug output problems
- ✅ Optimize for efficiency

It's inspired by **Uplink** (tension), **Hacknet** (authenticity), **Zachtronics** (optimization), and **Quadrilateral Cowboy** (tangibility).

## 📚 Documentation

- **For BBS Integration**: See `INTEGRATION_GUIDE.md`
- **For Bug Solutions**: See `BUG_REFERENCE.md`
- **For Testing**: Run `python3 test_debugger.py`

## 🔧 Technical Details

**Language**: Python 3.x  
**Dependencies**: pygame  
**Window Size**: 1200x700  
**Platform**: Cross-platform (Windows, Linux, macOS)  

### BASIC Commands Supported

The interpreter handles:
- `REM` - Comments
- `DIM` - Array dimensions
- `LET` - Variable assignment
- `FOR`/`NEXT` - Loops
- `IF`/`THEN`/`GOTO` - Conditionals
- `PRINT` - Output
- `CLS` - Clear screen
- `CIRCLE`, `LINE` - Graphics
- `CHR$()`, `RND()`, `INT()` - Functions

## 🎯 Integration Example

```python
# In your BBS main.py:
import debugger_game

def handle_game_selection(self):
    if selected_game == "DEBUGGER.BAS":
        result = debugger_game.run_debugger_game()
        
        if result['completed']:
            # Grant token to player
            self.grant_token('debugger_complete')
            
            # Send congratulations email from Glyphis
            self.send_email_from_glyphis(result)
            
            # Update leaderboard
            self.update_leaderboard('debugger', result)
```

## 🎮 Player Experience

**Before fixing bugs:**
```
> RUN
ERROR: Line 190: NEXT without FOR
```

**After fixing bugs:**
```
> RUN
[Network visualization animates]
TRACE: ████████████ 100%
TRACE COMPLETE
TARGET LOCATED
COORDS: 145,182
ACCESS TOKEN: GPGLPH
```

**Token extracted!** → BBS content unlocked → Glyphis congratulates player → Story progresses

## 🛠️ Customization

Want to make it harder or easier?

- Add more bugs
- Change time limits
- Modify scoring weights
- Create difficulty levels
- Add different visualizations

All easily configurable in `debugger_game.py`.

## 🧪 Testing

Comprehensive test suite included:

```bash
python3 test_debugger.py     # Full test suite
python3 test_diagnostic.py   # Debug specific issues
```

Tests cover:
- BASIC interpreter correctness
- FOR/NEXT loops
- Array handling
- Bug detection
- Graphics rendering

## 📝 License & Credits

**Created by**: Claude (Anthropic AI)  
**For**: GlyphisIO BBS narrative game  
**Inspired by**: Uplink, Hacknet, Zachtronics games  

Free to use, modify, and integrate into your project.

## 🤝 Support

Need help integrating or customizing?

1. Check `INTEGRATION_GUIDE.md` for detailed instructions
2. Review `BUG_REFERENCE.md` for quick solutions
3. Run the test suite to verify your setup
4. Read the code comments (heavily documented)

## 🎬 Next Steps

1. **Test it**: Run `python3 debugger_game.py` to see it in action
2. **Read the guide**: Check out `INTEGRATION_GUIDE.md`
3. **Integrate it**: Add to your BBS using the examples
4. **Customize it**: Make it your own!

---

**Remember**: This isn't just a game. It's a test. Glyphis is watching. Your performance determines your place in the digital underground.

*"Code doesn't lie. But it can be wrong."* - Glyphis
