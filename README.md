# ECHOGLOW 🐍

Music-reactive wallpapers and dynamic Android theme colors for Termux.

## Features

- Standard wallpaper engine
- Minimal wallpaper engine
- Dynamic wallpaper and Android accent-color engine
- Shared album-art cache
- Space Grotesk fonts
- Interactive installer

## Requirements

- Android with Termux
- Internet connection
- Termux:API Android app for wallpaper updates
- Shizuku and a working Rish launcher for optional system theme sync

## Installation

Install Termux packages:

    pkg update
    pkg install git python termux-api

Clone the repository:

    git clone https://github.com/ANKIT-PIXEL-414/ECHOGLOW.git
    cd ECHOGLOW

Run the installer:

    bash install.sh

Choose one, two, or all three engines when prompted.

The installer preserves existing scripts unless you explicitly approve
overwriting them.

## Important

The Dynamic Color engine's system accent sync depends on Android version,
manufacturer restrictions, Shizuku, and Rish. Wallpaper functionality
and system theme synchronization are separate features.

Install the official Termux:API Android app compatible with your Termux
installation. Installing the `termux-api` package alone is not sufficient.

## License

Choose a license before redistributing or publishing modified versions.

## 🎨 Dynamic Color Engine — Special Requirements

The `wallpaper-color.py` engine is the special ECHOGLOW engine.
In addition to generating music-reactive wallpapers, it can attempt
to synchronize Android's system accent color with the current music artwork.

**Important:** System accent-color synchronization requires:

- Shizuku installed and running on the Android device
- The Rish shell launcher (`rish`) configured and accessible to Termux
- Shizuku authorization and compatible Android system settings access

Installing ECHOGLOW does NOT install or configure Shizuku or Rish
automatically. These must be set up separately by the user.

Without a working Rish/Shizuku setup, wallpaper generation may still work,
but system accent-color synchronization will be skipped or unavailable.

Compatibility depends on the Android version and device manufacturer.
