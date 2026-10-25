#!/data/data/com.termux/files/usr/bin/bash

set -u

# ---------- GITHUB BOOTSTRAP ----------
# If only install.sh was downloaded, fetch the required project files.
if [ "${ECHOGLOW_BOOTSTRAPPED:-0}" != "1" ]; then
    LOCAL_READY=1
    for required in \
        scripts/wallpaper.py \
        scripts/wallpaper-minimal.py \
        scripts/wallpaper-color.py \
        requirements.txt \
        fonts/static/SpaceGrotesk-Regular.ttf \
        fonts/static/SpaceGrotesk-Medium.ttf \
        fonts/static/SpaceGrotesk-Bold.ttf \
        fonts/static/SpaceGrotesk-Light.ttf \
        fonts/static/SpaceGrotesk-SemiBold.ttf
    do
        [ -s "$(dirname "${BASH_SOURCE[0]}")/$required" ] || LOCAL_READY=0
    done

    if [ "$LOCAL_READY" -eq 0 ]; then
        REPO_URL="https://raw.githubusercontent.com/ANKIT-PIXEL-414/ECHOGLOW/main"
        BOOT_DIR="$(mktemp -d "${TMPDIR:-$HOME}/echoglow-bootstrap.XXXXXX")" || exit 1

        download_file() {
            url="$1"
            destination="$2"
            if command -v curl >/dev/null 2>&1; then
                curl -fLsS --retry 2 "$url" -o "$destination"
            elif command -v wget >/dev/null 2>&1; then
                wget -q "$url" -O "$destination"
            else
                printf '\nERROR: Install curl first: pkg install curl\n' >&2
                return 1
            fi
            [ -s "$destination" ]
        }

        printf '\n\033[96m ECHOGLOW: downloading setup files from GitHub...\033[0m\n'

        mkdir -p "$BOOT_DIR/scripts" "$BOOT_DIR/fonts/static" || exit 1
        cp "${BASH_SOURCE[0]}" "$BOOT_DIR/install.sh" || exit 1

        files=(
            "scripts/wallpaper.py"
            "scripts/wallpaper-minimal.py"
            "scripts/wallpaper-color.py"
            "requirements.txt"
            "fonts/static/SpaceGrotesk-Regular.ttf"
            "fonts/static/SpaceGrotesk-Medium.ttf"
            "fonts/static/SpaceGrotesk-Bold.ttf"
            "fonts/static/SpaceGrotesk-Light.ttf"
            "fonts/static/SpaceGrotesk-SemiBold.ttf"
        )

        for file in "${files[@]}"; do
            printf '  Downloading %s...\n' "$file"
            if ! download_file "$REPO_URL/$file" "$BOOT_DIR/$file"; then
                printf '\nERROR: Download failed: %s\n' "$file" >&2
                printf 'No installation was started. Check your connection and retry.\n' >&2
                rm -rf "$BOOT_DIR"
                exit 1
            fi
        done

        printf '\n\033[92m Downloads complete. Launching ECHOGLOW setup...\033[0m\n'
        ECHOGLOW_BOOTSTRAPPED=1 bash "$BOOT_DIR/install.sh"
        result=$?
        rm -rf "$BOOT_DIR"
        exit "$result"
    fi
fi
# ---------- END BOOTSTRAP ----------

REPO_URL="https://github.com/ANKIT-PIXEL-414/ECHOGLOW"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="$HOME/music-wallpaper"
SCRIPT_SOURCE="$REPO_DIR/scripts"
FONT_SOURCE="$REPO_DIR/fonts/static"
REQUIREMENTS="$REPO_DIR/requirements.txt"

# Neon palette
if [ -t 1 ]; then
    RESET=$'\033[0m'
    BOLD=$'\033[1m'
    DIM=$'\033[2m'
    CYAN=$'\033[96m'
    PURPLE=$'\033[95m'
    GREEN=$'\033[92m'
    YELLOW=$'\033[93m'
    RED=$'\033[91m'
    WHITE=$'\033[97m'
else
    RESET='' BOLD='' DIM=''
    CYAN='' PURPLE='' GREEN=''
    YELLOW='' RED='' WHITE=''
fi

declare -A SELECTED
SELECTED[1]=0
SELECTED[2]=0
SELECTED[3]=0

line() {
    printf '%b\n' "${DIM}--------------------------------------${RESET}"
}

header() {
    clear 2>/dev/null || true
    printf '\n'
    printf '%b\n' "${CYAN}${BOLD}  E C H O G L O W${RESET}"
    printf '%b\n' "${PURPLE}  MUSIC-REACTIVE WALLPAPER ENGINE${RESET}"
    line
    printf '%b\n' "${DIM}  GitHub: ${REPO_URL}${RESET}"
    printf '\n'
}

ok()   { printf '  %b %s\n' "${GREEN}[OK]${RESET}" "$*"; }
info() { printf '  %b %s\n' "${CYAN}[i]${RESET}" "$*"; }
warn() { printf '  %b %s\n' "${YELLOW}[!]${RESET}" "$*"; }
fail() { printf '  %b %s\n' "${RED}[X]${RESET}" "$*" >&2; }

pause_exit() {
    printf '\n'
    read -r -p "  Press Enter to exit..." _
    exit "${1:-0}"
}

draw_menu() {
    header
    printf '%b\n\n' "${WHITE}${BOLD}  SELECT ENGINES${RESET}"

    for id in 1 2 3; do
        case "$id" in
            1) name="STANDARD ENGINE"; color="$CYAN" ;;
            2) name="MINIMAL ENGINE"; color="$PURPLE" ;;
            3) name="DYNAMIC COLOR ENGINE"; color="$YELLOW" ;;
        esac

        if [ "${SELECTED[$id]}" -eq 1 ]; then
            status="${GREEN}[x] SELECTED${RESET}"
        else
            status="${DIM}[ ] NOT SELECTED${RESET}"
        fi

        printf '  %b %s\n' "${color}[$id]${RESET}" "$name"
        printf '      %b\n\n' "$status"
    done

    line
    printf '  %b Toggle   %b All   %b None\n' \
        "${CYAN}1/2/3${RESET}" "${PURPLE}A${RESET}" "${YELLOW}N${RESET}"
    printf '  %b Install   %b Quit\n\n' \
        "${GREEN}D${RESET}" "${RED}Q${RESET}"
}

# Pre-flight checks
if ! command -v pkg >/dev/null 2>&1; then
    fail "Run this installer inside Termux."
    exit 1
fi

if [ ! -f "$REQUIREMENTS" ] || [ ! -d "$SCRIPT_SOURCE" ]; then
    fail "Project files are missing."
    info "Expected scripts/ and requirements.txt beside install.sh."
    exit 1
fi

for script in wallpaper.py wallpaper-minimal.py wallpaper-color.py; do
    if [ ! -f "$SCRIPT_SOURCE/$script" ]; then
        fail "Missing scripts/$script"
        exit 1
    fi
done

# Engine selection
while true; do
    draw_menu
    choice=""

    if ! read -r -p "  ECHOGLOW > " choice; then
        printf '\n'
        exit 0
    fi

    choice="$(printf '%s' "$choice" | tr '[:lower:]' '[:upper:]' | tr -d '[:space:]')"

    case "$choice" in
        1|2|3)
            if [ "${SELECTED[$choice]}" -eq 1 ]; then
                SELECTED[$choice]=0
            else
                SELECTED[$choice]=1
            fi
            ;;
        A)
            SELECTED[1]=1
            SELECTED[2]=1
            SELECTED[3]=1
            ;;
        N)
            SELECTED[1]=0
            SELECTED[2]=0
            SELECTED[3]=0
            ;;
        D)
            break
            ;;
        Q)
            warn "Installation cancelled."
            exit 0
            ;;
        *)
            warn "Enter 1, 2, 3, A, N, D or Q."
            sleep 1
            ;;
    esac
done

chosen=()
[ "${SELECTED[1]}" -eq 1 ] && chosen+=("wallpaper.py")
[ "${SELECTED[2]}" -eq 1 ] && chosen+=("wallpaper-minimal.py")
[ "${SELECTED[3]}" -eq 1 ] && chosen+=("wallpaper-color.py")

if [ "${#chosen[@]}" -eq 0 ]; then
    fail "No engines selected."
    pause_exit 1
fi

header
printf '%b\n' "${WHITE}${BOLD}  INSTALLATION SUMMARY${RESET}"
printf '\n'
for script in "${chosen[@]}"; do
    ok "$script"
done

if [ "${SELECTED[3]}" -eq 1 ]; then
    printf '\n'
    warn "Dynamic accent sync needs working Shizuku + Rish."
fi

printf '\n'
info "Destination: $TARGET"
printf '\n'
read -r -p "  Continue with installation? [y/N] " confirm
case "$confirm" in
    y|Y|yes|YES) ;;
    *) warn "Installation cancelled."; exit 0 ;;
esac

header
printf '%b\n' "${WHITE}${BOLD}  [1/4] INSTALLING DEPENDENCIES${RESET}"
line

pkg update -y || {
    fail "Package update failed."
    pause_exit 1
}

pkg install -y python python-pillow python-requests termux-api git || {
    fail "Dependency installation failed."
    pause_exit 1
}

if ! python -c 'import requests; from PIL import Image' >/dev/null 2>&1; then
    python -m pip install -r "$REQUIREMENTS" || {
        fail "Python dependency installation failed."
        pause_exit 1
    }
fi
ok "Dependencies ready"

printf '\n%b\n' "${WHITE}${BOLD}  [2/4] PREPARING DESTINATION${RESET}"
line

mkdir -p "$TARGET/cache" "$TARGET/fonts/static" || {
    fail "Could not create destination folders."
    pause_exit 1
}
ok "$TARGET"

printf '\n%b\n' "${WHITE}${BOLD}  [3/4] INSTALLING ENGINES${RESET}"
line

installed=0
skipped=0

for script in "${chosen[@]}"; do
    src="$SCRIPT_SOURCE/$script"
    dest="$TARGET/$script"

    if [ -e "$dest" ]; then
        printf '\n'
        warn "$script already exists."
        read -r -p "  Overwrite this file? [y/N] " overwrite
        case "$overwrite" in
            y|Y|yes|YES) ;;
            *)
                warn "Skipped $script"
                skipped=$((skipped + 1))
                continue
                ;;
        esac
    fi

    if cp "$src" "$dest"; then
        ok "Installed $script"
        installed=$((installed + 1))
    else
        fail "Could not install $script"
    fi
done

if [ -d "$FONT_SOURCE" ]; then
    for font in "$FONT_SOURCE"/*.ttf; do
        [ -f "$font" ] || continue
        dest="$TARGET/fonts/static/$(basename "$font")"
        if [ ! -e "$dest" ]; then
            cp "$font" "$dest" && ok "Added $(basename "$font")"
        fi
    done
fi

printf '\n%b\n' "${WHITE}${BOLD}  [4/4] FINAL CHECK${RESET}"
line

if ! command -v termux-wallpaper >/dev/null 2>&1; then
    warn "termux-wallpaper command not found; check Termux:API setup."
else
    ok "Termux:API command found"
fi

if [ "${SELECTED[3]}" -eq 1 ]; then
    if command -v rish >/dev/null 2>&1 || [ -x "$HOME/rish" ]; then
        ok "Rish launcher detected"
    else
        warn "Rish not detected; accent sync may be unavailable."
    fi
    warn "Shizuku must also be running and authorized."
fi

printf '\n'
printf '%b\n' "${GREEN}${BOLD}  ECHOGLOW SETUP FINISHED${RESET}"
printf '  Installed: %s | Skipped: %s\n' "$installed" "$skipped"
printf '\n%b\n' "${CYAN}  RUN YOUR ENGINE${RESET}"

for script in "${chosen[@]}"; do
    printf '  %b\n' "${WHITE}python \"$TARGET/$script\"${RESET}"
done

printf '\n'
printf '%b\n' "${PURPLE}  PROJECT & SOURCE CODE${RESET}"
printf '  %s\n' "$REPO_URL"
printf '\n'
info "Termux:API Android app must be installed separately."
info "Existing files are only overwritten after your confirmation."
pause_exit 0
