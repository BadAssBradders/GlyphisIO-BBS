---
name: dotsonic-player
description: A specialized guide for the dotSONIC media player on the Bradsonic 69000 OS. Use when the user needs help obtaining, installing, or operating the dotSONIC media player. Covers the Echo Chamber BBS workflow, region unlocking, and media player UI/controls.
---

# dotSONIC Player

## Overview

The **dotSONIC Media Player** is a retro-styled desktop application for the Bradsonic 69000 OS, primarily used for playing `.sonic` audio files and virtual tracks from various BBS systems. This skill provides detailed workflows for obtaining the player from the Echo Chamber BBS and mastering its interface.

## Quick Reference

- **Installer File:** `DOTSONIC_INSTALL.BINST` (Echo Chamber BBS)
- **Deployment Path:** `C:\BRADSONIC\DOTSONIC\DOTSONIC.BRX`
- **Required Locale:** American Mainland (Region 1)
- **Primary Function:** High-fidelity media playback with audio-reactive visualizers.

## Guides

- **[Installation Workflow](references/installation.md):** Step-by-step guide for bypassing the Pacifica region lock, downloading the installer from Echo Chamber, and deploying it in OS Mode.
- **[Technical Specification](references/technical_spec.md):** Detailed breakdown of the player's UI, controls (buttons/sliders), and audio-reactive features (spectrum analyzer and oscilloscope).

## Troubleshooting

- **"Transfers Restricted":** Ensure the machine region is set to **American Mainland**. Transfers are blocked in the default **American Pacifica Isles** locale.
- **Icon Not Visible:** Confirm the `DOTSONIC` token has been granted (via installer completion) and the machine is NOT in the Pacifica locale.
