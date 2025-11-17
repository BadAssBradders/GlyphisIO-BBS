# Steam Playtest Upload - Quick Checklist

## Pre-Upload

- [ ] Game runs locally without errors
- [ ] Steam API initializes (check console for "Steam API initialized")
- [ ] All assets load correctly (images, videos, audio)
- [ ] Achievements can unlock (test locally)

## Build Process

- [ ] Run `build_for_steam.bat`
- [ ] Build completes successfully
- [ ] Test build with `test_build.bat`
- [ ] Verify `steam_api.dll` is in build folder
- [ ] Verify `steam_appid.txt` is in build folder
- [ ] Verify all game folders are included

## Upload to Steam

- [ ] Log into Steam Partner Portal (https://partner.steamgames.com/)
- [ ] Navigate to App ID: 4179570
- [ ] Go to "Builds" section
- [ ] Click "Upload Build"
- [ ] Upload entire `dist/GlyphisIO_BBS/` folder (or zip it first)
- [ ] Wait for upload to complete

## Set Up Playtest

- [ ] Go to "Playtest" section
- [ ] Create new playtest
- [ ] Assign uploaded build as active build
- [ ] Set visibility (private with codes recommended)
- [ ] Generate invite codes (if private)
- [ ] Save changes

## Test on Steam

- [ ] Install game via Steam client
- [ ] Launch game
- [ ] Verify Steam API works
- [ ] Test achievements
- [ ] Verify all features work

## Share with Testers

- [ ] Share invite codes (if private playtest)
- [ ] Or make playtest public
- [ ] Provide testing instructions
- [ ] Set up feedback channel (Discord/email)

---

## Quick Commands

```bash
# Build
build_for_steam.bat

# Test build locally
test_build.bat

# Upload manually via web interface
# (Go to Steam Partner Portal → Builds → Upload)
```

---

## File Locations

- **Build output:** `dist/GlyphisIO_BBS/`
- **Spec file:** `build_game.spec`
- **Steam App ID:** `4179570`
- **Steam Partner Portal:** https://partner.steamgames.com/

---

## Common Issues

**Build missing files?**
→ Check `build_game.spec` datas section

**Steam API not working?**
→ Verify `steam_api.dll` and `steam_appid.txt` in build

**Game won't launch?**
→ Test build locally first, check console output

**Upload fails?**
→ Check file size, verify Steam Partner permissions

