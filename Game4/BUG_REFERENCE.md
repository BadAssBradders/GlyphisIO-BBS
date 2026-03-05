# DEBUGGER.BAS - Bug Reference Card

## Quick Reference for Players

### The Three Bugs

#### Bug #1: Missing Loop Variable (Line 190)
**Error**: `NEXT without FOR`

**Current Code**:
```basic
170 FOR I=1 TO 9
180   LINE NODE(I,0),NODE(I,1),NODE(I+1,0),NODE(I+1,1),1
190 NEXT          ← BUG: Missing variable
```

**Fix**:
```basic
190 NEXT I
```

---

#### Bug #2: Wrong Comparison Operator (Line 220)
**Error**: Infinite loop (trace never completes)

**Current Code**:
```basic
220 IF TRACE=>100 THEN GOTO 260    ← BUG: => should be >=
```

**Fix**:
```basic
220 IF TRACE>=100 THEN GOTO 260
```

**Explanation**: `=>` is not a valid BASIC operator. The correct operator is `>=` for "greater than or equal to".

---

#### Bug #3: Token Generation (Lines 340-360)
**Error**: Token is hard-coded instead of derived from data

**Current Code**:
```basic
330 PRINT "ACCESS TOKEN: ";
340 LET C1=CHR$(71)     ← BUG: Hard-coded values
350 LET C2=CHR$(80)     ← BUG: Should derive from X,Y
360 PRINT C1;C2;"GLPH"
```

**Advanced Fix** (optional for optimal score):
```basic
340 LET C1=CHR$((NODE(5,0)/5)+65)
350 LET C2=CHR$((NODE(5,1)/5)+65)
360 PRINT C1;C2;"GLPH"
```

**Note**: This bug is optional to fix. The program will run with the hard-coded token, but fixing it properly demonstrates deeper understanding.

---

## Minimal Solution (2 Edits)

To complete the game, you only need to fix:
1. Line 190: `190 NEXT I`
2. Line 220: `220 IF TRACE>=100 THEN GOTO 260`

## Commands

| Command | Action |
|---------|--------|
| `RUN` | Execute the program |
| `EDIT <n>` | Edit line number n |
| `LIST` | Show full program |
| `HELP` | Toggle help screen |
| `QUIT` | Exit game |

## How to Edit

1. Type `EDIT 190`
2. The line appears for editing
3. Type the corrected code (without line number)
4. Press ENTER to save
5. Press ESC to cancel

## What the Program Does

When fixed, the program should:
1. Initialize 10 network nodes at random positions
2. Draw nodes as cyan circles
3. Connect nodes with lines
4. Animate a trace progress bar from 0% to 100%
5. Display coordinates of node 5
6. Generate and display an access token
7. Token format: `[2 chars]GLPH`

## Scoring

**Perfect Score (100 points)**:
- 2 edits
- Under 2 minutes
- Clean execution

**Your Score Factors**:
- Fewer edits = higher score
- Faster time = higher score
- No failed runs = bonus

## Tips

1. **Read the error messages carefully** - They tell you exactly what's wrong
2. **Test after each fix** - Run the program to see if you fixed that bug
3. **The HELP screen has syntax reminders** - Use it!
4. **Watch the output panel** - The visualization shows when things work
5. **Don't overthink it** - The bugs are straightforward syntax errors

## Common Mistakes

❌ Typing `NEXT` without the variable name  
❌ Using `=>` instead of `>=`  
❌ Not running the program after edits  
❌ Editing the wrong line number  
❌ Forgetting to press ENTER to save edits  

## Expected Output

When successful:
```
TRACE COMPLETE
TARGET LOCATED
COORDS: <X>,<Y>
ACCESS TOKEN: <XX>GLPH
```

The token will be added to your BBS inventory automatically.

---

## For Developers: Implementation Notes

### Bug Detection

The BASIC interpreter will catch:
- **Syntax errors** (NEXT without FOR)
- **Invalid operators** (=> returns False in condition)
- **Logic errors** (silent - program runs but gives wrong output)

### Token Validation

Any output containing "GLPH" is considered a token. The game extracts it and returns to main BBS with the token string.

### Replay Value

Each run generates different node positions (random), so the network topology and coordinates vary. However, the same bugs need fixing every time.

---

**Remember**: Glyphis designed this test. Your performance determines your standing in the BBS hierarchy. Rain, Jaxkando, and uncle-am are watching the leaderboard. 

Make them proud.
