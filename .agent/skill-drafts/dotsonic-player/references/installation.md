# dotSONIC Installation Workflow

The dotSONIC media player is a "cracked" mainland application found on the Echo Chamber BBS. It requires bypassing the Pacifica Isles region lock on the Bradsonic 69000.

## 1. Prerequisites: Bypassing the Pacifica Lock

By default, the Bradsonic 69000 is set to the **American Pacifica Isles** locale (Region 3). This region restricts file transfers from outside BBSs.

**Workflow to Unlock:**
- Access the Bradsonic 69000 OS.
- Go to the system configuration/region settings.
- Change the region to **American Mainland** (Region 1).
- **CRITICAL:** Do NOT factory reset the machine; only change the region.

## 2. Obtaining the Installer

- Dial into the **Echo Chamber BBS** (discovered via radio or terminal hints).
- Navigate to the **Darknet** or **Filez** section.
- Locate the package: `DOTSONIC_INSTALL.BINST`.
- Transfer (Download) the file to your machine. 
  - *Note: This transfer will fail if the machine is still in the Pacifica locale.*

## 3. Installation in OS Mode

- Return to the **Bradsonic 69000 Desktop**.
- Open the `DOWNLOADS` folder (or where the file was saved).
- Double-click/Open `DOTSONIC_INSTALL.BINST`.
- A simulated terminal installation will begin.
- **Path:** The installer deploys `DOTSONIC.BRX` to `C:\BRADSONIC\DOTSONIC`.
- **Outcome:** The `DOTSONIC` token is granted to the player.

## 4. Launching

- Once installed, a new icon `sonic-icon.png` (labeled "dotSONIC") appears on the desktop.
- Double-click the icon to launch the `DotSonicMediaPlayer`.
