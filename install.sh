#!/data/data/com.termux/files/usr/bin/bash

set -u

REPO="https://raw.githubusercontent.com/ANKIT-PIXEL-414/ECHOGLOW/main"
HOME_DIR="$HOME"
DEFAULT_TARGET="$HOME/music-wallpaper"

CYAN='\033[96m'
GREEN='\033[92m'
YELLOW='\033[93m'
RED='\033[91m'
RESET='\033[0m'

header() {
    clear 2>/dev/null || true
    printf "${CYAN}========================================\n"
    printf "             E C H O G L O W\n"
    printf "       MUSIC-REACTIVE WALLPAPER ENGINE\n"
    printf "========================================${RESET}\n\n"
}

fail() {
    printf "${RED}[ERROR] %s${RESET}\n" "$*" >&2
    exit 1
}

# Read user input from terminal even if piped (e.g. curl ... | bash)
read_tty() {
    local prompt="$1"
    local var_name="$2"
    if [[ -n "${FORCE_STDIN:-}" ]]; then
        read -r -p "$prompt" "$var_name" || return 1
    elif [[ -t 0 ]]; then
        read -r -p "$prompt" "$var_name" || return 1
    elif [[ -e /dev/tty ]]; then
        read -r -p "$prompt" "$var_name" < /dev/tty || return 1
    else
        fail "Interactive terminal (/dev/tty) is required for installation."
    fi
}

# 1. Choose engine
header
printf "Which engine do you want to install?\n\n"
printf "  1) Standard Engine (Cyber logs)\n"
printf "  2) Minimal Engine (Live Dashboard)\n"
printf "  3) Dynamic Color Engine (Accent Sync + Shizuku)\n"
printf "  4) All Three Engines\n"
printf "  Q) Quit\n\n"

while true; do
    read_tty "Select engine [1-4/Q] > " choice || exit 0
    case "$choice" in
        1)
            ENGINES=("wallpaper.py")
            DEFAULT_ENGINE="wallpaper.py"
            break
            ;;
        2)
            ENGINES=("wallpaper-minimal.py")
            DEFAULT_ENGINE="wallpaper-minimal.py"
            break
            ;;
        3)
            ENGINES=("wallpaper-color.py")
            DEFAULT_ENGINE="wallpaper-color.py"
            break
            ;;
        4)
            ENGINES=("wallpaper.py" "wallpaper-minimal.py" "wallpaper-color.py")
            DEFAULT_ENGINE="wallpaper.py"
            break
            ;;
        [Qq]) exit 0 ;;
        *) printf "Please choose 1, 2, 3, 4, or Q.\n" ;;
    esac
done

if ((${#ENGINES[@]} > 1)); then
    printf "\nWhich engine should be launched by default when running 'echoglow'?\n"
    printf "  1) Standard Engine\n"
    printf "  2) Minimal Engine\n"
    printf "  3) Dynamic Color Engine\n"
    while true; do
        read_tty "Default engine [1-3, default: 1] > " def_choice || exit 0
        case "$def_choice" in
            1|"") DEFAULT_ENGINE="wallpaper.py"; break ;;
            2) DEFAULT_ENGINE="wallpaper-minimal.py"; break ;;
            3) DEFAULT_ENGINE="wallpaper-color.py"; break ;;
            *) printf "Please choose 1, 2, or 3.\n" ;;
        esac
    done
fi

# 2. Destination selection
header
printf "INSTALLATION DESTINATION\n\n"
printf "Default destination: %s\n\n" "$DEFAULT_TARGET"
printf "  1) Use default destination (%s)\n" "$DEFAULT_TARGET"
printf "  2) Custom destination (File-manager picker / custom path)\n"
printf "  Q) Quit\n\n"

USE_PICKER=0
TARGET=""

while true; do
    read_tty "Choose option [1-2/Q, default: 1] > " dest_choice || exit 0
    case "$dest_choice" in
        1|"")
            TARGET="$DEFAULT_TARGET"
            break
            ;;
        2)
            USE_PICKER=1
            break
            ;;
        [Qq]) exit 0 ;;
        *) printf "Please choose 1, 2, or Q.\n" ;;
    esac
done

if [[ "$USE_PICKER" -eq 1 ]]; then
    CURRENT="$HOME_DIR"
    while true; do
        CURRENT="${CURRENT%/}"
        [[ -z "$CURRENT" ]] && CURRENT="/"

        header
        printf "FILE MANAGER DESTINATION PICKER\n\n"
        printf "Current folder:\n%s\n\n" "$CURRENT"
        if [[ "$CURRENT" != "/" ]]; then
            printf "  [0] 📁 ..  Go to parent folder\n"
        fi

        dirs=()
        shopt -s nullglob
        if [[ -r "$CURRENT" && -x "$CURRENT" ]]; then
            for entry in "$CURRENT"/*; do
                [[ -d "$entry" ]] || continue
                [[ "${entry##*/}" == ".git" ]] && continue
                [[ -x "$entry" ]] || continue
                dirs+=("$entry")
            done
        fi
        shopt -u nullglob

        if ((${#dirs[@]} > 0)); then
            for i in "${!dirs[@]}"; do
                printf "  [%d] 📁 %s/\n" "$((i + 1))" "${dirs[$i]##*/}"
            done
        else
            printf "  (No accessible subfolders)\n"
        fi

        printf "\n"
        printf "  [U] Use current folder\n"
        printf "  [N] Create new subfolder inside current folder\n"
        printf "  [P] Type custom path manually\n"
        printf "  [H] Go to Home directory\n"
        printf "  [D] Use Default (%s)\n" "$DEFAULT_TARGET"
        printf "  [Q] Cancel / Quit\n\n"

        read_tty "Select option / folder number > " pick || exit 0
        pick="$(printf '%s' "$pick" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')"

        case "$pick" in
            q) exit 0 ;;
            h) CURRENT="$HOME_DIR" ;;
            d) TARGET="$DEFAULT_TARGET"; break ;;
            u)
                if [[ "$CURRENT" == "$HOME_DIR" || "$CURRENT" == "/" ]]; then
                    printf "\nInstalling directly into %s root is not recommended.\n" "$CURRENT"
                    read_tty "Enter subfolder name (or press Enter to cancel): " sub_name || true
                    sub_name="$(printf '%s' "$sub_name" | tr -d '\r\n')"
                    if [[ -n "$sub_name" ]]; then
                        TARGET="$CURRENT/$sub_name"
                        break
                    fi
                else
                    TARGET="$CURRENT"
                    break
                fi
                ;;
            n)
                printf "\nCreate new subfolder inside:\n%s\n" "$CURRENT"
                read_tty "Subfolder name > " new_sub || true
                new_sub="$(printf '%s' "$new_sub" | tr -d '\r\n')"
                if [[ -n "$new_sub" ]]; then
                    TARGET="$CURRENT/$new_sub"
                    break
                fi
                ;;
            p)
                printf "\nEnter destination path (e.g. ~/music-wallpaper or /sdcard/wallpapers):\n"
                read_tty "Path > " custom_path || true
                custom_path="$(printf '%s' "$custom_path" | tr -d '\r\n')"
                if [[ -n "$custom_path" ]]; then
                    TARGET="$custom_path"
                    break
                fi
                ;;
            0)
                if [[ "$CURRENT" != "/" ]]; then
                    CURRENT="$(dirname "$CURRENT")"
                fi
                ;;
            ''|*[!0-9]*)
                printf "Invalid choice. Please select from the menu.\n"
                sleep 1
                ;;
            *)
                index=$((10#$pick))
                if (( index >= 1 && index <= ${#dirs[@]} )); then
                    CURRENT="${dirs[$((index - 1))]}"
                else
                    printf "Invalid folder number.\n"
                    sleep 1
                fi
                ;;
        esac
    done
fi

# Destination validation
TARGET="${TARGET/#\~/$HOME_DIR}"
TARGET="${TARGET%/}"
[[ -z "$TARGET" ]] && TARGET="/"

if [[ ! -d "$TARGET" ]]; then
    mkdir -p "$TARGET" || fail "Cannot create destination directory: $TARGET"
fi

canonical_target="$(cd "$TARGET" 2>/dev/null && pwd -P)" ||
    fail "Cannot access destination directory: $TARGET"
canonical_home="$(cd "$HOME_DIR" 2>/dev/null && pwd -P)"

if [[ "$canonical_target" == "$canonical_home" || "$canonical_target" == "/" ]]; then
    fail "Please choose a dedicated subfolder, not Termux HOME root or filesystem root."
fi

valid_dest=0
case "$canonical_target/" in
    "$canonical_home/"*|/storage/*|/sdcard/*) valid_dest=1 ;;
esac

if [[ "$valid_dest" -ne 1 ]]; then
    fail "Destination must be inside Termux HOME or storage ($TARGET)."
fi

# 3. Confirm
header
printf "INSTALLATION SUMMARY\n\n"
printf "Engines:     "
for eng in "${ENGINES[@]}"; do
    printf "%s " "$eng"
done
printf "\n"
printf "Default:     %s\n" "$DEFAULT_ENGINE"
printf "Destination: %s\n\n" "$TARGET"

read_tty "Continue? [y/N] " confirm || exit 0
case "$confirm" in
    y|Y|yes|YES) ;;
    *) printf "Installation cancelled.\n"; exit 0 ;;
esac

# 4. Check & Install required Termux packages
header
printf "Checking required packages...\n"

command -v pkg >/dev/null 2>&1 ||
    fail "Run this installer inside Termux."

missing_pkgs=()
command -v python >/dev/null 2>&1 || missing_pkgs+=(python)
command -v curl >/dev/null 2>&1 || missing_pkgs+=(curl)
command -v termux-wallpaper >/dev/null 2>&1 || missing_pkgs+=(termux-api)

if ((${#missing_pkgs[@]} > 0)); then
    printf "Installing required Termux packages: %s...\n" "${missing_pkgs[*]}"
    pkg install -y "${missing_pkgs[@]}" || fail "Could not install required Termux packages."
else
    printf "${GREEN}[OK]${RESET} All required Termux packages are installed.\n"
fi

if ! python -c "import requests, PIL" >/dev/null 2>&1; then
    printf "Installing required Python libraries (requests, Pillow)...\n"
    python -m pip install --upgrade --no-warn-script-location requests Pillow ||
        fail "Could not install Python libraries."
else
    printf "${GREEN}[OK]${RESET} Python libraries (requests, Pillow) are installed.\n"
fi

# 5. Determine Source: Local repository or GitHub download
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
IS_LOCAL_REPO=0
if [[ -f "$SCRIPT_DIR/scripts/wallpaper.py" && \
      -f "$SCRIPT_DIR/scripts/wallpaper-minimal.py" && \
      -f "$SCRIPT_DIR/scripts/wallpaper-color.py" && \
      -d "$SCRIPT_DIR/fonts/static" ]]; then
    IS_LOCAL_REPO=1
fi

TMP=""
cleanup() {
    if [[ -n "$TMP" && -d "$TMP" ]]; then
        rm -rf "$TMP"
    fi
}
trap cleanup EXIT INT TERM

download_file() {
    local remote="$1"
    local output="$2"

    printf "  Downloading %s...\n" "$remote"
    curl -fLsS --retry 2 "$REPO/$remote" -o "$output" ||
        fail "Download failed: $remote"

    [[ -s "$output" ]] || fail "Downloaded file is empty: $remote"
}

mkdir -p "$TARGET/cache" "$TARGET/fonts/static" ||
    fail "Cannot create destination structure."

if [[ "$IS_LOCAL_REPO" -eq 1 ]]; then
    printf "\nInstalling from local repository files...\n"

    for eng in "${ENGINES[@]}"; do
        if [[ -e "$TARGET/$eng" ]]; then
            read_tty "$eng already exists in destination. Overwrite? [y/N] " overwrite || exit 0
            case "$overwrite" in
                y|Y|yes|YES) ;;
                *) printf "Skipping %s\n" "$eng"; continue ;;
            esac
        fi
        cp "$SCRIPT_DIR/scripts/$eng" "$TARGET/$eng" || fail "Could not copy $eng"
        printf "  ${GREEN}[OK]${RESET} Installed %s\n" "$eng"
    done

    for font in "$SCRIPT_DIR"/fonts/static/*.ttf; do
        [[ -f "$font" ]] || continue
        dest="$TARGET/fonts/static/$(basename "$font")"
        if [[ ! -e "$dest" ]]; then
            cp "$font" "$dest" || fail "Could not copy font: $(basename "$font")"
        fi
    done

    if printf '%s\n' "${ENGINES[@]}" | grep -q "wallpaper-color.py"; then
        if [[ -d "$SCRIPT_DIR/shizuku" ]]; then
            mkdir -p "$TARGET/shizuku"
            cp "$SCRIPT_DIR/shizuku/rish" "$TARGET/shizuku/rish" 2>/dev/null || true
            cp "$SCRIPT_DIR/shizuku/rish_shizuku.dex" "$TARGET/shizuku/rish_shizuku.dex" 2>/dev/null || true
            [[ -f "$TARGET/shizuku/rish" ]] && chmod +x "$TARGET/shizuku/rish"
        fi
    fi

else
    printf "\nDownloading components from GitHub...\n"
    TMP="$(mktemp -d)" || fail "Cannot create temporary directory."
    mkdir -p "$TMP/scripts" "$TMP/fonts/static" "$TMP/shizuku"

    for eng in "${ENGINES[@]}"; do
        download_file "scripts/$eng" "$TMP/scripts/$eng"
        if [[ -e "$TARGET/$eng" ]]; then
            read_tty "$eng already exists in destination. Overwrite? [y/N] " overwrite || exit 0
            case "$overwrite" in
                y|Y|yes|YES) ;;
                *) printf "Skipping %s\n" "$eng"; continue ;;
            esac
        fi
        cp "$TMP/scripts/$eng" "$TARGET/$eng" || fail "Could not copy $eng"
        printf "  ${GREEN}[OK]${RESET} Installed %s\n" "$eng"
    done

    for font in \
        SpaceGrotesk-Regular.ttf \
        SpaceGrotesk-Medium.ttf \
        SpaceGrotesk-Bold.ttf \
        SpaceGrotesk-Light.ttf \
        SpaceGrotesk-SemiBold.ttf
    do
        dest="$TARGET/fonts/static/$font"
        if [[ ! -e "$dest" ]]; then
            download_file "fonts/static/$font" "$TMP/fonts/static/$font"
            cp "$TMP/fonts/static/$font" "$dest" || fail "Could not copy font: $font"
        fi
    done

    if printf '%s\n' "${ENGINES[@]}" | grep -q "wallpaper-color.py"; then
        mkdir -p "$TARGET/shizuku"
        download_file "shizuku/rish" "$TMP/shizuku/rish"
        download_file "shizuku/rish_shizuku.dex" "$TMP/shizuku/rish_shizuku.dex"
        cp "$TMP/shizuku/rish" "$TARGET/shizuku/rish"
        cp "$TMP/shizuku/rish_shizuku.dex" "$TARGET/shizuku/rish_shizuku.dex"
        chmod +x "$TARGET/shizuku/rish"
    fi
fi

# 6. Install launcher script ('echoglow')
LAUNCHER_CONTENT='#!/data/data/com.termux/files/usr/bin/bash
# ECHOGLOW Launcher
set -e

ECHOGLOW_HOME="@@TARGET@@"
DEFAULT_ENGINE="@@DEFAULT_ENGINE@@"
export ECHOGLOW_HOME

show_help() {
    printf "ECHOGLOW Wallpaper Engine Launcher\n\n"
    printf "Usage: echoglow [OPTION]\n\n"
    printf "Options:\n"
    printf "  -s, --standard    Launch Standard wallpaper engine (Cyber logs)\n"
    printf "  -m, --minimal     Launch Minimal wallpaper engine (Live Dashboard)\n"
    printf "  -c, --color       Launch Dynamic Color wallpaper engine (Accent sync)\n"
    printf "  -h, --help        Show this help message\n\n"
}

SELECTED_ENGINE=""
case "${1:-}" in
    -s|--standard) SELECTED_ENGINE="wallpaper.py" ;;
    -m|--minimal)  SELECTED_ENGINE="wallpaper-minimal.py" ;;
    -c|--color)    SELECTED_ENGINE="wallpaper-color.py" ;;
    -h|--help)     show_help; exit 0 ;;
    "")            SELECTED_ENGINE="$DEFAULT_ENGINE" ;;
    *)
        printf "Unknown option: %s\n" "$1" >&2
        show_help
        exit 1
        ;;
esac

if [[ ! -f "$ECHOGLOW_HOME/$SELECTED_ENGINE" ]]; then
    available=()
    [[ -f "$ECHOGLOW_HOME/wallpaper.py" ]] && available+=("wallpaper.py")
    [[ -f "$ECHOGLOW_HOME/wallpaper-minimal.py" ]] && available+=("wallpaper-minimal.py")
    [[ -f "$ECHOGLOW_HOME/wallpaper-color.py" ]] && available+=("wallpaper-color.py")

    if ((${#available[@]} == 1)); then
        SELECTED_ENGINE="${available[0]}"
    elif ((${#available[@]} > 1)); then
        printf "Requested engine (%s) is not installed.\n" "$SELECTED_ENGINE"
        printf "Available engines in %s:\n" "$ECHOGLOW_HOME"
        for i in "${!available[@]}"; do
            printf "  [%d] %s\n" "$((i + 1))" "${available[$i]}"
        done
        read -r -p "Select engine to run > " pick
        idx=$((10#$pick - 1))
        if (( idx >= 0 && idx < ${#available[@]} )); then
            SELECTED_ENGINE="${available[$idx]}"
        else
            printf "Invalid choice.\n" >&2
            exit 1
        fi
    else
        printf "Error: No ECHOGLOW engines found in %s\n" "$ECHOGLOW_HOME" >&2
        exit 1
    fi
fi

if ! command -v python >/dev/null 2>&1; then
    printf "Error: python is not installed. Run: pkg install python\n" >&2
    exit 1
fi

if ! command -v termux-wallpaper >/dev/null 2>&1; then
    printf "Warning: termux-wallpaper command not found. Ensure Termux:API is installed.\n" >&2
fi

exec python "$ECHOGLOW_HOME/$SELECTED_ENGINE" "$@"
'

LAUNCHER_SCRIPT="${LAUNCHER_CONTENT//@@TARGET@@/$TARGET}"
LAUNCHER_SCRIPT="${LAUNCHER_SCRIPT//@@DEFAULT_ENGINE@@/$DEFAULT_ENGINE}"

# Save launcher in target directory
printf '%s\n' "$LAUNCHER_SCRIPT" > "$TARGET/echoglow"
chmod +x "$TARGET/echoglow"

# Install in Termux bin ($PREFIX/bin) if writable so command is globally available
LAUNCHER_INSTALLED_IN_PATH=0
if [[ -w "${PREFIX:-/data/data/com.termux/files/usr}/bin" ]]; then
    printf '%s\n' "$LAUNCHER_SCRIPT" > "${PREFIX:-/data/data/com.termux/files/usr}/bin/echoglow"
    chmod +x "${PREFIX:-/data/data/com.termux/files/usr}/bin/echoglow"
    LAUNCHER_INSTALLED_IN_PATH=1
fi

# 7. Finish
header
printf "${GREEN}ECHOGLOW INSTALLED SUCCESSFULLY!${RESET}\n\n"
printf "Location: %s\n" "$TARGET"
printf "Engines:  "
for eng in "${ENGINES[@]}"; do
    printf "%s " "$eng"
done
printf "\nDefault:  %s\n\n" "$DEFAULT_ENGINE"

printf "To start ECHOGLOW, simply run:\n\n"
if [[ "$LAUNCHER_INSTALLED_IN_PATH" -eq 1 ]]; then
    printf "  ${CYAN}echoglow${RESET}\n\n"
else
    printf "  ${CYAN}%s/echoglow${RESET}\n\n" "$TARGET"
fi

if ((${#ENGINES[@]} > 1)); then
    printf "You can also switch engines anytime using:\n"
    printf "  echoglow --standard\n"
    printf "  echoglow --minimal\n"
    printf "  echoglow --color\n\n"
fi

printf "${YELLOW}[NOTE]${RESET} Wallpaper updates require the Termux:API Android app with Notification Access.\n"
if printf '%s\n' "${ENGINES[@]}" | grep -q "wallpaper-color.py"; then
    printf "${YELLOW}[NOTE]${RESET} Dynamic Color engine requires Shizuku running and authorized.\n"
fi
printf "\nGitHub: https://github.com/ANKIT-PIXEL-414/ECHOGLOW\n"
