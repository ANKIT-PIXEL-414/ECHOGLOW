import io
import os
import re
import json
import time
import sys
import hashlib
import textwrap
import unicodedata
import subprocess
import shlex
import shutil
import colorsys
from datetime import datetime

import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps


# =====================================================
# ECHOGLOW • CYBER TERMINAL CONFIG
# =====================================================

TARGET_PACKAGE = "echo.music.iad1tya"
BASE_DIR = os.path.abspath(os.path.expanduser(os.environ.get("ECHOGLOW_HOME", "~/music-wallpaper")))
CACHE_DIR = os.path.join(BASE_DIR, "cache")
HOME_OUT = os.path.join(BASE_DIR, "home.jpg")
LOCK_OUT = os.path.join(BASE_DIR, "lock.jpg")

W, H = 1080, 2400
POLL_INTERVAL = 6
RETRY_INTERVAL = 60
CORNER_RADIUS = 35
ART_SIZE = 850
BLUR_RADIUS = 65
BACKGROUND_TINT = (8, 8, 16)
TINT_STRENGTH = 0.38

# Android dynamic accent-colour sync (optional; requires running Shizuku).
RISH_CANDIDATES = (os.path.expanduser("~/rish"), shutil.which("rish"))
THEME_SETTING = "theme_customization_overlay_packages"
THEME_BACKUP_DIR = os.path.join(BASE_DIR, "backups")
THEME_SETTING_KEY = "secure"
last_synced_accent = None
theme_backup_for_this_run = None

os.makedirs(BASE_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

session = requests.Session()
last_track = None
last_attempt_track = None
last_attempt_time = 0


# =====================================================
# NEON ANSI COLOURS
# =====================================================

USE_COLOUR = (
    sys.stdout.isatty()
    and os.environ.get("TERM", "dumb") != "dumb"
)


class C:
    RESET = "\033[0m" if USE_COLOUR else ""
    BOLD = "\033[1m" if USE_COLOUR else ""
    DIM = "\033[2m" if USE_COLOUR else ""
    CYAN = "\033[38;5;51m" if USE_COLOUR else ""
    BLUE = "\033[38;5;75m" if USE_COLOUR else ""
    PURPLE = "\033[38;5;141m" if USE_COLOUR else ""
    MAGENTA = "\033[38;5;201m" if USE_COLOUR else ""
    GREEN = "\033[38;5;82m" if USE_COLOUR else ""
    YELLOW = "\033[38;5;220m" if USE_COLOUR else ""
    RED = "\033[38;5;203m" if USE_COLOUR else ""
    WHITE = "\033[38;5;255m" if USE_COLOUR else ""
    GREY = "\033[38;5;245m" if USE_COLOUR else ""


def paint(text, colour):
    return f"{colour}{text}{C.RESET}"


def timestamp():
    return datetime.now().strftime("%H:%M:%S")


def clear_screen():
    """Clear old track logs when a new song starts."""
    if sys.stdout.isatty() and os.environ.get("TERM", "dumb") != "dumb":
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()


def terminal_width(default=72):
    try:
        return max(40, min(os.get_terminal_size().columns, 100))
    except OSError:
        return default


def display_path(value):
    """Shorten home-directory paths in terminal logs."""
    try:
        path = os.path.abspath(os.path.expanduser(str(value)))
        home = os.path.abspath(os.path.expanduser("~"))
        if path == home:
            return "~"
        if path.startswith(home + os.sep):
            return "~" + path[len(home):]
    except Exception:
        pass
    return str(value)


def log(level, message, colour=C.CYAN, symbol="◆"):
    """Print readable, wrapped and colourful log messages."""
    width = terminal_width()

    prefix_plain = f" {timestamp()}  {symbol} {level:<8} "
    prefix = (
        f" {paint(timestamp(), C.GREY)}  "
        f"{paint(f'{symbol} {level:<8}', colour + C.BOLD)} "
    )

    available = max(20, width - len(prefix_plain))

    lines = textwrap.wrap(
        str(message),
        width=available,
        break_long_words=True,
        break_on_hyphens=False,
    ) or [""]

    print(prefix + lines[0], flush=True)

    continuation = " " * len(prefix_plain)

    for line in lines[1:]:
        print(continuation + line, flush=True)


def section(title):
    width = min(terminal_width(), 72)
    inner = max(20, width - 4)
    label = f" {title} "

    if len(label) > inner:
        label = label[:inner]

    left = max(2, (inner - len(label)) // 2)
    right = max(2, inner - len(label) - left)

    line = "─" * left + label + "─" * right

    print(paint("╭" + "─" * (inner + 2), C.PURPLE))
    print(
        paint("│", C.PURPLE)
        + paint(line, C.CYAN + C.BOLD)
        + paint("│", C.PURPLE)
    )
    print(
        paint("╰" + "─" * (inner + 2), C.PURPLE),
        flush=True,
    )


# =====================================================
# STARTUP BANNER
# =====================================================

def show_banner():
    width = 44
    inner = width - 2

    def framed(content, colour=C.CYAN):
        content = content[:inner]
        padding = inner - len(content)

        return (
            paint("│", C.PURPLE + C.BOLD)
            + paint(content, colour)
            + (" " * padding)
            + paint("│", C.PURPLE + C.BOLD)
        )

    top = "╭" + "─" * inner + "╮"
    middle = "├" + "─" * inner + "┤"
    bottom = "╰" + "─" * inner + "╯"

    print()
    print(paint(top, C.PURPLE + C.BOLD))
    print(
        framed(
            "✦  E C H O G L O W  ✦".center(inner),
            C.CYAN + C.BOLD,
        )
    )
    print(
        framed(
            "MUSIC WALLPAPER ENGINE".center(inner),
            C.MAGENTA + C.BOLD,
        )
    )
    print(paint(middle, C.PURPLE + C.BOLD))
    print(framed("USER   Aki@termux", C.GREEN))
    print(framed("MODE   NEON / AUTO WALLPAPER", C.BLUE))
    print(paint(bottom, C.PURPLE + C.BOLD))
    print()

    log("SYSTEM", f"Music package: {TARGET_PACKAGE}", C.BLUE, "▸")
    log(
        "SYSTEM",
        f"Poll: {POLL_INTERVAL}s | Artwork retry: {RETRY_INTERVAL}s",
        C.BLUE,
        "▸",
    )
    log("SYSTEM", f"Cache dir: {display_path(CACHE_DIR)}", C.BLUE, "▸")
    log("SYSTEM", "Home: blurred background + rounded cover", C.BLUE, "▸")
    log("SYSTEM", "Lock: rounded cover + track details", C.BLUE, "▸")
    print()


# =====================================================
# TEXT NORMALIZATION
# =====================================================

def normalize(text):
    text = unicodedata.normalize(
        "NFKC", str(text)
    ).casefold()

    return re.sub(r"[^\w]", "", text, flags=re.UNICODE)


def clean_metadata(text):
    text = str(text or "").strip()

    text = re.sub(r"[\(\[].*?[\)\]]", " ", text)
    text = re.sub(
        r"\b(feat\.?|ft\.?)\b.*",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s+", " ", text)

    return text.strip(" -–—")


# =====================================================
# READ ECHO MUSIC NOTIFICATIONS
# =====================================================

def get_notifications():
    try:
        result = subprocess.run(
            ["termux-notification-list"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        return json.loads(result.stdout)

    except FileNotFoundError:
        log(
            "ERROR",
            "termux-notification-list not found. Install Termux:API "
            "and the termux-api package.",
            C.RED,
            "✖",
        )
        return []

    except Exception as error:
        log(
            "WARN",
            f"Could not read notifications: {error}",
            C.YELLOW,
            "!",
        )
        return []


def find_track():
    for notification in get_notifications():
        if notification.get("packageName") != TARGET_PACKAGE:
            continue

        title = (notification.get("title") or "").strip()
        artist = (notification.get("content") or "").strip()

        if not title:
            continue

        if title.casefold() in {
            "echo music",
            "playing music",
            "music player",
        }:
            continue

        if artist and normalize(title) == normalize(artist):
            continue

        return title, artist

    return None


# =====================================================
# FIND ALBUM ARTWORK
# =====================================================

def find_artwork(title, artist):
    clean_title = clean_metadata(title)
    clean_artist = clean_metadata(artist)

    queries = [
        (f"{clean_title} {clean_artist}".strip(), "us"),
        (f"{title} {artist}".strip(), "us"),
        (f"{clean_title} {clean_artist}".strip(), "kr"),
        (f"{clean_title} {clean_artist}".strip(), "jp"),
        (f"{clean_artist} {clean_title}".strip(), "kr"),
        (clean_title, "us"),
        (clean_title, "kr"),
    ]

    results = []
    seen = set()

    for index, (term, country) in enumerate(queries, start=1):
        if not term:
            continue

        log(
            "SEARCH",
            f"Catalog {index}/{len(queries)} · "
            f"{country.upper()} · {term}",
            C.PURPLE,
            "⌕",
        )

        try:
            response = session.get(
                "https://itunes.apple.com/search",
                params={
                    "term": term,
                    "entity": "song",
                    "limit": 25,
                    "country": country,
                },
                timeout=12,
            )
            response.raise_for_status()

            for item in response.json().get("results", []):
                key = item.get("trackId") or item.get("trackViewUrl")

                if key and key in seen:
                    continue

                if key:
                    seen.add(key)

                results.append(item)

        except requests.RequestException as error:
            log(
                "WARN",
                f"Search failed ({country.upper()}): {error}",
                C.YELLOW,
                "!",
            )

    wanted_title = normalize(clean_title or title)
    wanted_artist = normalize(clean_artist or artist)

    artist_parts = [
        normalize(part)
        for part in re.split(
            r"[,/&;]+",
            clean_artist or artist,
        )
        if normalize(part)
    ]

    candidates = []

    for item in results:
        track_name = item.get("trackName", "")
        artist_name = item.get("artistName", "")

        track = normalize(clean_metadata(track_name))
        performer = normalize(artist_name)

        if not track or not item.get("artworkUrl100"):
            continue

        score = 0

        if track == wanted_title:
            score += 100
        elif wanted_title and (
            wanted_title in track or track in wanted_title
        ):
            score += 55

        if wanted_artist and performer:
            if wanted_artist == performer:
                score += 90
            elif (
                wanted_artist in performer
                or performer in wanted_artist
            ):
                score += 50
            elif any(
                part and part in performer
                for part in artist_parts
            ):
                score += 25
            else:
                score -= 30
        else:
            score += 10

        candidates.append((score, item))

    if not candidates:
        log(
            "MISS",
            f"No catalog artwork found for {title} — {artist}",
            C.YELLOW,
            "◇",
        )
        return None

    candidates.sort(key=lambda pair: pair[0], reverse=True)
    best_score, best_item = candidates[0]

    if best_score < 50:
        log(
            "MISS",
            f"No reliable artwork match (score {best_score})",
            C.YELLOW,
            "◇",
        )
        return None

    art_url = best_item.get("artworkUrl100", "")

    if not art_url:
        return None

    log(
        "MATCH",
        f"{best_item.get('trackName', 'Unknown')} — "
        f"{best_item.get('artistName', 'Unknown')} "
        f"[score {best_score}]",
        C.GREEN,
        "✔",
    )

    return re.sub(r"\d+x\d+bb", "1200x1200bb", art_url)


# =====================================================
# ARTWORK CACHE HELPERS
# =====================================================

def get_cache_filename(title, artist):
    norm_artist = normalize(artist) or "unknown_artist"
    norm_title = normalize(title) or "unknown_title"
    filename = f"{norm_artist}_{norm_title}.jpg"

    if len(filename.encode("utf-8")) > 220:
        hash_suffix = hashlib.sha256(
            f"{norm_artist}_{norm_title}".encode("utf-8")
        ).hexdigest()[:12]
        filename = f"{norm_artist[:40]}_{norm_title[:40]}_{hash_suffix}.jpg"

    return filename


def get_cache_path(title, artist):
    return os.path.join(CACHE_DIR, get_cache_filename(title, artist))


def get_cached_artwork(cache_path):
    if not os.path.isfile(cache_path):
        return None

    try:
        if os.path.getsize(cache_path) == 0:
            return None

        with Image.open(cache_path) as img:
            img.verify()

        return Image.open(cache_path).convert("RGB")
    except Exception:
        return None



# =====================================================
# ANDROID SYSTEM ACCENT COLOUR SYNC (SHIZUKU / RISH)
# =====================================================

def find_rish():
    """Find the user's rish launcher without assuming it is on PATH."""
    for candidate in RISH_CANDIDATES:
        if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def run_rish_read(command, timeout=8):
    """Run a read-only Android shell command through rish."""
    rish_path = find_rish()
    if not rish_path:
        raise FileNotFoundError(
            "rish launcher not found at ~/rish or on PATH; accent sync skipped"
        )
    # rish is an Android-shell bridge. Quote each argument so metadata/JSON
    # cannot be interpreted as shell syntax.
    shell_command = " ".join(shlex.quote(str(part)) for part in command)
    result = subprocess.run(
        ["sh", rish_path, "-c", shell_command],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"rish command failed ({result.returncode}): {detail[:240]}")
    return result.stdout.strip()


def run_rish_write(command, timeout=10):
    """Run a write command through rish; caller verifies the result afterwards."""
    return run_rish_read(command, timeout=timeout)


def dominant_artwork_colour(image):
    """Return a vivid, readable accent derived from the album artwork.

    Ignore transparent pixels and extremes, choose a meaningful colourful
    cluster, then gently adjust lightness/saturation to avoid muddy accents.
    Returns '#RRGGBB'; the sync function adapts it to the device's stored format.
    """
    rgba = image.convert("RGBA")
    rgba.thumbnail((96, 96))
    pixels = list(rgba.get_flattened_data() if hasattr(rgba, 'get_flattened_data') else rgba.getdata())

    visible = [(r, g, b) for r, g, b, a in pixels if a >= 32]
    if not visible:
        return "#00A6A6"

    # Remove very dark and near-white pixels so borders/highlights do not dominate.
    usable = []
    for red, green, blue in visible:
        brightness = (red + green + blue) / 3
        if 24 <= brightness <= 238:
            usable.append((red, green, blue))
    if len(usable) < max(20, len(visible) // 12):
        usable = visible

    sample = Image.new("RGB", (len(usable), 1))
    sample.putdata(usable)
    quantized = sample.quantize(
        colors=min(16, len(usable)),
        method=Image.Quantize.MEDIANCUT
    )
    palette = quantized.getpalette()
    counts = quantized.getcolors(maxcolors=sample.width * sample.height) or []

    if not counts or not palette:
        rgb = tuple(
            sum(px[i] for px in usable) // len(usable) for i in range(3)
        )
    else:
        # Score clusters by population, saturation, and usable lightness.
        # Prefer colours that are noticeable but not nearly black/neon-white.
        candidates = []
        for count, palette_index in counts:
            offset = palette_index * 3
            rgb_candidate = tuple(palette[offset:offset + 3])
            r, g, b = (channel / 255.0 for channel in rgb_candidate)
            hue, lightness, saturation = colorsys.rgb_to_hls(r, g, b)
            brightness = (sum(rgb_candidate) / 3) / 255.0

            if brightness < 0.08 or brightness > 0.94:
                continue

            # Weight population strongly, with a preference for colours that
            # have some saturation and mid-range brightness.
            lightness_score = max(0.0, 1.0 - abs(lightness - 0.48) / 0.55)
            saturation_score = 0.45 + 0.75 * saturation
            score = count * saturation_score * lightness_score
            candidates.append((score, count, rgb_candidate))

        if candidates:
            candidates.sort(reverse=True)
            rgb = candidates[0][2]
        else:
            rgb = tuple(
                sum(px[i] for px in visible) // len(visible) for i in range(3)
            )

    # Smart finishing: avoid very dark/muddy or washed-out results while
    # keeping the original hue. Moderate saturation gives a richer UI accent.
    r, g, b = (channel / 255.0 for channel in rgb)
    hue, lightness, saturation = colorsys.rgb_to_hls(r, g, b)
    if saturation < 0.24:
        saturation = 0.42
    else:
        saturation = min(0.82, max(0.38, saturation * 1.12))

    lightness = min(0.66, max(0.38, lightness))
    adjusted = colorsys.hls_to_rgb(hue, lightness, saturation)
    return "#{:02X}{:02X}{:02X}".format(
        *(int(round(channel * 255)) for channel in adjusted)
    )


def read_android_theme():
    raw = run_rish_read(["settings", "get", "secure", THEME_SETTING])
    try:
        theme = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as error:
        raise ValueError(
            "Android returned an unreadable theme JSON; refusing to modify it"
        ) from error
    if not isinstance(theme, dict):
        raise ValueError("Theme setting is not a JSON object; refusing to modify it")
    return raw, theme


def backup_theme_once(raw):
    """Save an immutable, timestamped copy before this run's first palette write."""
    global theme_backup_for_this_run
    if theme_backup_for_this_run:
        return theme_backup_for_this_run

    os.makedirs(THEME_BACKUP_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = os.path.join(THEME_BACKUP_DIR, f"theme-customization-{stamp}.json")
    # Exclusive create: never overwrite an existing backup.
    suffix = 1
    candidate = path
    while True:
        try:
            with open(candidate, "x", encoding="utf-8") as handle:
                handle.write(raw)
                handle.write("\n")
            break
        except FileExistsError:
            candidate = os.path.join(
                THEME_BACKUP_DIR, f"theme-customization-{stamp}-{suffix}.json"
            )
            suffix += 1

    with open(candidate, "r", encoding="utf-8") as handle:
        saved = handle.read().strip()
    if saved != raw.strip():
        try:
            os.remove(candidate)
        except OSError:
            pass
        raise IOError("Theme backup verification failed; refusing to change palette")

    theme_backup_for_this_run = candidate
    log("THEME", f"Original theme backed up → {display_path(candidate)}", C.GREEN, "▣")
    return candidate


def terminal_colour_swatch(hex_colour):
    """Render a small true-colour swatch in compatible terminals."""
    value = str(hex_colour).strip().lstrip("#")
    if len(value) != 6:
        return "[colour]"
    try:
        r, g, b = (int(value[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return "[colour]"
    return f"\033[48;2;{r};{g};{b}m  \033[0m"


def sync_system_accent(cover):
    """Best-effort accent sync. Failures are logged but never stop wallpaper work."""
    global last_synced_accent
    try:
        colour = dominant_artwork_colour(cover)
        swatch = terminal_colour_swatch(colour)
        log("COLOUR", f"{swatch} {colour.upper()}  Artwork accent", C.CYAN, "◉")

        rish_path = find_rish()
        if not rish_path:
            log("THEME", "rish not found; skipping system colour sync", C.YELLOW, "!")
            return

        raw, theme = read_android_theme()
        current = str(theme.get("android.theme.customization.system_palette", "")).upper()
        # Preserve this Android build's existing convention: its palette value
        # may be stored with or without a leading '#'.
        desired = colour.upper() if current.startswith("#") else colour.lstrip("#").upper()
        current_accent = str(theme.get("android.theme.customization.accent_color", "")).upper()
        if current == desired and current_accent.lstrip("#") == desired.lstrip("#"):
            last_synced_accent = desired
            log("THEME", f"System palette already matches {desired}", C.GREEN, "✓")
            return
        if last_synced_accent == desired:
            return

        # Automatic theme backups disabled by user.
        updated_theme = dict(theme)
        updated_theme["android.theme.customization.system_palette"] = desired
        # Preserve the existing device convention and update this legacy field too
        # for compatibility with this Motorola build.
        updated_theme["android.theme.customization.accent_color"] = desired
        updated_theme["_applied_timestamp"] = int(time.time() * 1000)
        serialized = json.dumps(updated_theme, separators=(",", ":"), ensure_ascii=False)

        run_rish_write([
            "settings", "put", "secure", THEME_SETTING, serialized
        ], timeout=10)

        _, verified_theme = read_android_theme()
        verified = str(
            verified_theme.get("android.theme.customization.system_palette", "")
        ).upper()
        if verified.lstrip("#") != desired.lstrip("#"):
            raise RuntimeError(
                f"Android setting verification failed (reported {verified or 'no palette'})"
            )

        last_synced_accent = desired
        log("THEME", f"System palette setting updated to {desired}", C.GREEN, "✔")
        log(
            "THEME",
            "Check Quick Settings/buttons manually to confirm the UI applied it.",
            C.YELLOW,
            "!",
        )
    except Exception as error:
        log(
            "THEME",
            f"Accent sync skipped; wallpapers will continue normally: {error}",
            C.YELLOW,
            "!",
        )


def fetch_and_cache_artwork(art_url, cache_path):
    log(
        "DOWNLOAD",
        "Fetching high-resolution album artwork...",
        C.BLUE,
        "↓",
    )

    response = session.get(art_url, timeout=25)
    response.raise_for_status()

    cover = Image.open(
        io.BytesIO(response.content)
    ).convert("RGB")

    try:
        cover.save(cache_path, format="JPEG", quality=95)
        log(
            "CACHE",
            f"Saved artwork to cache → {os.path.basename(cache_path)}",
            C.GREEN,
            "✔",
        )
    except Exception as error:
        log(
            "WARN",
            f"Failed to cache artwork: {error}",
            C.YELLOW,
            "!",
        )

    return cover


# =====================================================
# FONT + DRAWING HELPERS
# =====================================================

def load_font(size):
    for path in (
        os.path.join(
            BASE_DIR, "fonts", "static",
            "SpaceGrotesk-Bold.ttf",
        ),
        os.path.join(
            BASE_DIR, "fonts", "static",
            "SpaceGrotesk-Medium.ttf",
        ),
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass

    return ImageFont.load_default()


def draw_centered(draw, text, y, font, fill):
    bounds = draw.textbbox((0, 0), text, font=font)
    text_width = bounds[2] - bounds[0]

    draw.text(
        ((W - text_width) // 2, y),
        text,
        font=font,
        fill=fill,
    )


def paste_rounded_cover(background, cover):
    art = ImageOps.fit(
        cover,
        (ART_SIZE, ART_SIZE),
    ).convert("RGBA")

    mask = Image.new("L", (ART_SIZE, ART_SIZE), 0)

    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, ART_SIZE - 1, ART_SIZE - 1),
        radius=CORNER_RADIUS,
        fill=255,
    )

    background = background.convert("RGBA")
    x = (W - ART_SIZE) // 2
    y = 590

    background.paste(art, (x, y), mask)

    return background.convert("RGB")


# =====================================================
# GENERATE BOTH WALLPAPERS
# =====================================================

def make_wallpapers(art_source, title, artist):
    section("WALLPAPER RENDER")

    if isinstance(art_source, Image.Image):
        cover = art_source
    elif isinstance(art_source, str) and (
        art_source.startswith("http://") or art_source.startswith("https://")
    ):
        log(
            "DOWNLOAD",
            "Fetching high-resolution album artwork...",
            C.BLUE,
            "↓",
        )
        response = session.get(art_source, timeout=25)
        response.raise_for_status()
        cover = Image.open(
            io.BytesIO(response.content)
        ).convert("RGB")
    elif isinstance(art_source, str) and os.path.isfile(art_source):
        cover = Image.open(art_source).convert("RGB")
    else:
        raise ValueError(f"Invalid art source: {art_source}")

    log(
        "IMAGE",
        f"Source artwork: {cover.width} × {cover.height}",
        C.CYAN,
        "▧",
    )

    log(
        "RENDER",
        "Creating blurred background...",
        C.PURPLE,
        "◌",
    )

    background = ImageOps.fit(cover, (W, H))
    background = background.filter(
        ImageFilter.GaussianBlur(radius=BLUR_RADIUS)
    )

    background = Image.blend(
        background,
        Image.new("RGB", (W, H), BACKGROUND_TINT),
        TINT_STRENGTH,
    )

    log(
        "RENDER",
        "Placing rounded album cover...",
        C.PURPLE,
        "◈",
    )

    base_wallpaper = paste_rounded_cover(background, cover)

    base_wallpaper.save(HOME_OUT, quality=95)

    log(
        "SAVED",
        f"Home wallpaper → {display_path(HOME_OUT)}",
        C.GREEN,
        "✔",
    )

    lock_wallpaper = base_wallpaper.copy()
    draw = ImageDraw.Draw(lock_wallpaper)

    title_font = load_font(58)
    artist_font = load_font(36)

    display_title = title if len(title) <= 35 else title[:32] + "..."
    display_artist = artist if len(artist) <= 45 else artist[:42] + "..."

    draw_centered(draw, display_title, 1510, title_font, "white")
    draw_centered(
        draw,
        display_artist,
        1590,
        artist_font,
        (220, 220, 230),
    )

    lock_wallpaper.save(LOCK_OUT, quality=95)

    log(
        "SAVED",
        f"Lock wallpaper → {display_path(LOCK_OUT)}",
        C.GREEN,
        "✔",
    )


# =====================================================
# APPLY BOTH WALLPAPERS
# =====================================================

def set_wallpaper():
    section("APPLY WALLPAPERS")

    subprocess.run(
        ["termux-wallpaper", "-f", HOME_OUT],
        check=True,
        timeout=30,
        stdout=subprocess.DEVNULL,
    )

    log(
        "APPLIED",
        "Home screen wallpaper updated",
        C.GREEN,
        "✔",
    )

    subprocess.run(
        ["termux-wallpaper", "-l", "-f", LOCK_OUT],
        check=True,
        timeout=30,
        stdout=subprocess.DEVNULL,
    )

    log(
        "APPLIED",
        "Lock screen wallpaper updated",
        C.GREEN,
        "✔",
    )


# =====================================================
# AUTOMATIC MUSIC MONITOR
# =====================================================

def main():
    global last_track, last_attempt_track, last_attempt_time

    show_banner()

    log(
        "READY",
        "Waiting for Echo Music notifications...",
        C.CYAN,
        "◎",
    )

    log(
        "INFO",
        "Press Ctrl+C to stop the engine.",
        C.GREY,
        "⌁",
    )

    while True:
        try:
            track_info = find_track()

            if track_info:
                title, artist = track_info
                signature = f"{title}|{artist}"
                now = time.time()

                if signature != last_track:
                    should_attempt = (
                        signature != last_attempt_track
                        or now - last_attempt_time >= RETRY_INTERVAL
                    )

                    if should_attempt:
                        # Clear old song's logs, but retain the full design.
                        clear_screen()
                        show_banner()

                        log(
                            "READY",
                            "New track detected!",
                            C.CYAN,
                            "◎",
                        )

                        section("NOW PLAYING")

                        log("TRACK", title, C.MAGENTA, "♫")
                        log(
                            "ARTIST",
                            artist or "Unknown artist",
                            C.BLUE,
                            "♪",
                        )

                        last_attempt_track = signature
                        last_attempt_time = now

                        cache_path = get_cache_path(title, artist)
                        cover = get_cached_artwork(cache_path)

                        if cover:
                            log(
                                "CACHE",
                                f"Hit → {os.path.basename(cache_path)}",
                                C.GREEN,
                                "★",
                            )
                        else:
                            log(
                                "CACHE",
                                "No cache entry found. Searching catalog...",
                                C.PURPLE,
                                "⌕",
                            )
                            art_url = find_artwork(title, artist)

                            if art_url:
                                try:
                                    cover = fetch_and_cache_artwork(
                                        art_url, cache_path
                                    )
                                except Exception as err:
                                    log(
                                        "WARN",
                                        f"Failed to download/cache artwork: {err}",
                                        C.YELLOW,
                                        "!",
                                    )
                                    cover = None

                        if cover:
                            # Best-effort system accent sync; never block wallpapers.
                            sync_system_accent(cover)

                            make_wallpapers(
                                cover,
                                title,
                                artist,
                            )

                            set_wallpaper()

                            last_track = signature

                            log(
                                "SUCCESS",
                                "Both wallpapers updated successfully!",
                                C.GREEN,
                                "★",
                            )

                            print()

                        else:
                            log(
                                "RETRY",
                                f"Artwork unavailable; retrying in "
                                f"{RETRY_INTERVAL} seconds.",
                                C.YELLOW,
                                "↻",
                            )

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print()

            log(
                "STOPPED",
                "EchoGlow engine shut down. Stay neon, Aki.",
                C.MAGENTA,
                "■",
            )

            break

        except Exception as error:
            log(
                "ERROR",
                str(error),
                C.RED,
                "✖",
            )

            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
