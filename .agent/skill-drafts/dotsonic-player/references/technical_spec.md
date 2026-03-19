# dotSONIC Media Player Technical Specification

The dotSONIC Media Player is a retro-styled desktop application for the Bradsonic 69000 OS.

## 1. Aesthetic and UI

- **Color Scheme:** Dark blue-black background (`8, 12, 32`), cyan (`0, 255, 255`) and magenta (`180, 50, 150`) highlights.
- **CRT CRT Simulation:** Features scanlines, vignettes, and glow effects.
- **Dynamic Backdrops:** The interface uses different background images based on the active state (Playing, Paused, Stopped).
- **Invisible Hit Areas:** Buttons are "hotspots" that trigger actions. Labels are baked into the backdrop images.

## 2. Audio-Reactive Visualizers

- **Spectrum Analyzer (EQ Display):** 32-bar segmented gradient visualizer. Bars rise quickly and fall slowly, similar to hardware EQ units.
- **Oscilloscope:** Phosphor green waveform visualizer showing the raw audio signal.
- **Analysis:** Uses background FFT (Fast Fourier Transform) via NumPy (if available) to analyze tracks for instant, accurate visualization.

## 3. Controls and Features

| Button | ID | Function |
|--------|----|----------|
| **LOAD** | `load` | Opens the OS file browser to add `.sonic` files to the playlist. |
| **PREV** | `prev` | Jumps to the previous track in the playlist. |
| **REW** | `rewind` | Seeks backward or skips to the previous track. |
| **PLAY** | `play` | Toggles between playback and pause. |
| **FFWD** | `ffwd` | Seeks forward or skips to the next track. |
| **NEXT** | `next` | Jumps to the next track in the playlist. |
| **STOP** | `stop` | Halts playback and resets the current track. |

- **Sliders:** 
  - **VOL (Volume):** Vertical slider for master output.
  - **BAL (Balance):** Vertical slider (Top = Left, Bottom = Right, Middle = 50/50).
- **Playlist:** A scrollable list of tracks (shows up to 10 at a time). Current playing track is highlighted in cyan.

## 4. File Resolution

- **Supported Format:** `.sonic` files.
- **Virtual Tracks:** Supports "virtual" tracks (`__sonic__{title}`) found in BBS music archives (e.g., MiaZuki Audio Matrix on Paper Crane BBS, or Fugamatchi tracks on Never Again BBS).
- **Playlist Behavior:** When a track finishes, it is removed from the playlist, and the next track automatically starts.
