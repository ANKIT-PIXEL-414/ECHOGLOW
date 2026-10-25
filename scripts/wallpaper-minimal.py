import hashlib
import io
import os
import re
import json
import time
import sys
import textwrap
import unicodedata
import subprocess
from datetime import datetime

import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps


# =====================================================
# ECHOGLOW CONFIG
# =====================================================

TARGET_PACKAGE = "echo.music.iad1tya"
BASE_DIR = os.path.abspath(os.path.expanduser(os.environ.get("ECHOGLOW_HOME", "~/music-wallpaper")))
CACHE_DIR = os.path.join(BASE_DIR, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)
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

os.makedirs(BASE_DIR, exist_ok=True)

session = requests.Session()
last_track = None
last_attempt_track = None
last_attempt_time = 0


# =====================================================
# NEON COLOURS
# =====================================================

USE_COLOUR = (
    sys.stdout.isatty()
    and os.environ.get("TERM", "dumb") != "dumb"
)


class C:
    RESET = "\033[0m" if USE_COLOUR else ""
    BOLD = "\033[1m" if USE_COLOUR else ""
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


def terminal_width():
    try:
        return max(40, min(os.get_terminal_size().columns, 72))
    except OSError:
        return 48


def clip(text, width):
    text = str(text or "")
    if len(text) <= width:
        return text
    if width <= 3:
        return text[:width]
    return text[:width - 3] + "..."


# =====================================================
# LIVE DASHBOARD
# =====================================================

dashboard = {
    "track": "Waiting for music...",
    "artist": "—",
    "phase": "STARTING",
    "detail": "Initialising EchoGlow",
    "artwork": "Not searched",
    "wallpaper": "Waiting",
    "last_update": "—",
    "error": "None",
}


def dashboard_line(label, value, label_colour=C.CYAN,
                   value_colour=C.WHITE):
    inner = max(24, terminal_width() - 4)
    label_width = 11
    value_width = max(8, inner - label_width)

    label_text = f"{label:<{label_width}}"
    value_text = clip(value, value_width)

    padding = max(
        0,
        inner - len(label_text) - len(value_text)
    )

    return (
        paint("│ ", C.PURPLE)
        + paint(label_text, label_colour + C.BOLD)
        + paint(value_text, value_colour)
        + " " * padding
        + paint(" │", C.PURPLE)
    )


def render_dashboard():
    """Redraw the same screen instead of accumulating song logs."""

    if not USE_COLOUR:
        # Plain-text fallback for non-interactive terminals.
        print(
            f"[{timestamp()}] {dashboard['phase']}: "
            f"{dashboard['track']} — {dashboard['artist']} | "
            f"{dashboard['detail']}",
            flush=True,
        )
        return

    width = terminal_width()
    inner = width - 4

    top = "╭" + "─" * (inner + 2) + "╮"
    separator = "├" + "─" * (inner + 2) + "┤"
    bottom = "╰" + "─" * (inner + 2) + "╯"

    # Clear terminal and redraw the dashboard at the top.
    sys.stdout.write("\033[2J\033[H")

    print(paint(top, C.PURPLE + C.BOLD))

    title = "✦  E C H O G L O W  ✦".center(inner + 2)
    subtitle = "LIVE MUSIC WALLPAPER ENGINE".center(inner + 2)

    print(
        paint("│", C.PURPLE + C.BOLD)
        + paint(title, C.CYAN + C.BOLD)
        + paint("│", C.PURPLE + C.BOLD)
    )

    print(
        paint("│", C.PURPLE + C.BOLD)
        + paint(subtitle, C.MAGENTA + C.BOLD)
        + paint("│", C.PURPLE + C.BOLD)
    )

    print(paint(separator, C.PURPLE + C.BOLD))

    rows = [
        ("USER", "Aki@termux", C.GREEN, C.GREEN),
        ("MODE", "LIVE DASHBOARD", C.BLUE, C.BLUE),
        ("TRACK", dashboard["track"], C.MAGENTA, C.WHITE),
        ("ARTIST", dashboard["artist"], C.BLUE, C.WHITE),
        ("PHASE", dashboard["phase"], C.CYAN, C.CYAN),
        ("DETAIL", dashboard["detail"], C.GREY, C.WHITE),
        ("ARTWORK", dashboard["artwork"], C.PURPLE, C.WHITE),
        ("WALLPAPER", dashboard["wallpaper"], C.GREEN, C.WHITE),
        ("UPDATED", dashboard["last_update"], C.GREY, C.WHITE),
        ("ERROR", dashboard["error"], C.RED, C.WHITE),
    ]

    for label, value, lc, vc in rows:
        print(dashboard_line(label, value, lc, vc))

    print(paint(separator, C.PURPLE + C.BOLD))

    footer = (
        f"Poll {POLL_INTERVAL}s | Retry {RETRY_INTERVAL}s "
        "| Ctrl+C to stop"
    )

    footer = clip(footer, inner + 2).center(inner + 2)

    print(
        paint("│", C.PURPLE + C.BOLD)
        + paint(footer, C.GREY)
        + paint("│", C.PURPLE + C.BOLD)
    )

    print(paint(bottom, C.PURPLE + C.BOLD), flush=True)


def update_dashboard(**changes):
    dashboard.update(changes)
    render_dashboard()


# =====================================================
# TEXT NORMALISATION
# =====================================================

def normalize(text):
    text = unicodedata.normalize(
        "NFKC", str(text)
    ).casefold()

    return re.sub(r"[^\w]", "", text, flags=re.UNICODE)


def clean_metadata(text):
    text = str(text or "").strip()

    text = re.sub(
        r"[\(\[].*?[\)\]]",
        " ",
        text,
    )

    text = re.sub(
        r"\b(feat\.?|ft\.?)\b.*",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(r"\s+", " ", text)

    return text.strip(" -–—")


# =====================================================
# ECHO MUSIC NOTIFICATIONS
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
        update_dashboard(
            phase="MISSING DEPENDENCY",
            detail="Install Termux:API and the termux-api package",
            error="termux-notification-list not found",
        )
        return []

    except Exception as error:
        update_dashboard(
            phase="NOTIFICATION ERROR",
            detail="Unable to read music notifications",
            error=str(error),
        )
        return []


def find_track():
    for notification in get_notifications():
        if notification.get("packageName") != TARGET_PACKAGE:
            continue

        title = (
            notification.get("title") or ""
        ).strip()

        artist = (
            notification.get("content") or ""
        ).strip()

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
# SHARED ARTWORK CACHE
# =====================================================

def get_cache_filename(title, artist):
    norm_artist = normalize(artist) or "unknown_artist"
    norm_title = normalize(title) or "unknown_title"
    filename = f"{norm_artist}_{norm_title}.jpg"
    if len(filename.encode("utf-8")) > 220:
        suffix = hashlib.sha256(
            f"{norm_artist}_{norm_title}".encode("utf-8")
        ).hexdigest()[:12]
        filename = f"{norm_artist[:40]}_{norm_title[:40]}_{suffix}.jpg"
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


def fetch_and_cache_artwork(art_url, cache_path):
    response = session.get(art_url, timeout=25)
    response.raise_for_status()
    with Image.open(io.BytesIO(response.content)) as img:
        cover = img.convert("RGB")
    try:
        cover.save(cache_path, format="JPEG", quality=95)
    except Exception as error:
        update_dashboard(
            phase="CACHE WARNING",
            detail="Artwork loaded but cache save failed",
            error=str(error),
        )
    return cover

# =====================================================
# ARTWORK SEARCH
# =====================================================

def find_artwork(title, artist):
    cache_path = get_cache_path(title, artist)
    cached = get_cached_artwork(cache_path)
    if cached is not None:
        cached.close()
        update_dashboard(
            phase="ARTWORK CACHED",
            detail=f"Shared cache hit: {os.path.basename(cache_path)}",
            artwork="Cache hit",
        )
        return "cache://" + cache_path

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

    for index, (term, country) in enumerate(
        queries, start=1
    ):
        if not term:
            continue

        update_dashboard(
            phase="SEARCHING ARTWORK",
            detail=(
                f"Catalog {index}/{len(queries)} "
                f"| {country.upper()} | {term}"
            ),
            artwork=f"Searching {index}/{len(queries)}",
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
                key = (
                    item.get("trackId")
                    or item.get("trackViewUrl")
                )

                if key and key in seen:
                    continue

                if key:
                    seen.add(key)

                results.append(item)

        except requests.RequestException as error:
            update_dashboard(
                phase="SEARCH WARNING",
                detail=f"Catalog request failed ({country.upper()})",
                error=str(error),
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
        update_dashboard(
            phase="ARTWORK NOT FOUND",
            detail="No catalog artwork matched this track",
            artwork="Unavailable; retry scheduled",
        )
        return None

    candidates.sort(
        key=lambda pair: pair[0],
        reverse=True,
    )

    best_score, best_item = candidates[0]

    if best_score < 50:
        update_dashboard(
            phase="ARTWORK NOT FOUND",
            detail=f"No reliable match (score {best_score})",
            artwork="Unavailable; retry scheduled",
        )
        return None

    art_url = best_item.get("artworkUrl100", "")

    if not art_url:
        return None

    update_dashboard(
        phase="ARTWORK FOUND",
        detail=(
            f"Matched {best_item.get('trackName', 'Unknown')} "
            f"(score {best_score})"
        ),
        artwork=f"Matched | score {best_score}",
    )

    art_url = re.sub(
        r"\d+x\d+bb",
        "1200x1200bb",
        art_url,
    )
    try:
        fetch_and_cache_artwork(art_url, cache_path)
    except Exception as error:
        update_dashboard(
            phase="CACHE WARNING",
            detail="Artwork found; cache download failed",
            error=str(error),
        )
    return art_url


# =====================================================
# IMAGE HELPERS
# =====================================================

def load_font(size):
    paths = [
        os.path.join(
            BASE_DIR, "fonts", "static",
            "SpaceGrotesk-Bold.ttf",
        ),
        os.path.join(
            BASE_DIR, "fonts", "static",
            "SpaceGrotesk-Medium.ttf",
        ),
    ]

    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass

    return ImageFont.load_default()


def draw_centered(draw, text, y, font, fill):
    bounds = draw.textbbox(
        (0, 0), text, font=font
    )

    text_width = bounds[2] - bounds[0]

    draw.text(
        ((W - text_width) // 2, y),
        text,
        font=font,
        fill=fill,
    )


def paste_rounded_cover(background, cover):
    art = ImageOps.fit(
        cover, (ART_SIZE, ART_SIZE)
    ).convert("RGBA")

    mask = Image.new(
        "L", (ART_SIZE, ART_SIZE), 0
    )

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
# GENERATE WALLPAPERS
# =====================================================

def make_wallpapers(art_url, title, artist):
    update_dashboard(
        phase="DOWNLOADING ARTWORK",
        detail="Fetching high-resolution album artwork",
        wallpaper="Preparing",
    )

    if art_url.startswith("cache://"):
        cache_path = art_url[len("cache://"):]
        cover = get_cached_artwork(cache_path)
        if cover is None:
            raise RuntimeError("Cached artwork is unreadable")
    else:
        response = session.get(art_url, timeout=25)
        response.raise_for_status()
        cover = Image.open(
            io.BytesIO(response.content)
        ).convert("RGB")
        try:
            cover.save(
                get_cache_path(title, artist),
                format="JPEG",
                quality=95,
            )
        except Exception as error:
            update_dashboard(
                phase="CACHE WARNING",
                detail="Artwork loaded but cache save failed",
                error=str(error),
            )

    update_dashboard(
        phase="RENDERING",
        detail=f"Source artwork: {cover.width} × {cover.height}",
    )

    background = ImageOps.fit(cover, (W, H))

    background = background.filter(
        ImageFilter.GaussianBlur(
            radius=BLUR_RADIUS
        )
    )

    background = Image.blend(
        background,
        Image.new("RGB", (W, H), BACKGROUND_TINT),
        TINT_STRENGTH,
    )

    update_dashboard(
        phase="RENDERING",
        detail="Placing rounded album cover",
    )

    base_wallpaper = paste_rounded_cover(
        background, cover
    )

    base_wallpaper.save(
        HOME_OUT, quality=95
    )

    update_dashboard(
        phase="RENDERING",
        detail="Home saved; creating lock wallpaper",
        wallpaper="Home saved; lock rendering",
    )

    lock_wallpaper = base_wallpaper.copy()
    draw = ImageDraw.Draw(lock_wallpaper)

    title_font = load_font(58)
    artist_font = load_font(36)

    display_title = (
        title if len(title) <= 35
        else title[:32] + "..."
    )

    display_artist = (
        artist if len(artist) <= 45
        else artist[:42] + "..."
    )

    draw_centered(
        draw, display_title, 1510,
        title_font, "white",
    )

    draw_centered(
        draw, display_artist, 1590,
        artist_font, (220, 220, 230),
    )

    lock_wallpaper.save(
        LOCK_OUT, quality=95
    )

    update_dashboard(
        phase="WALLPAPERS READY",
        detail="Home and lock images generated",
        wallpaper="Both images saved",
    )


# =====================================================
# APPLY WALLPAPERS
# =====================================================

def set_wallpaper():
    update_dashboard(
        phase="APPLYING WALLPAPERS",
        detail="Applying home screen wallpaper",
        wallpaper="Applying home...",
    )

    subprocess.run(
        ["termux-wallpaper", "-f", HOME_OUT],
        check=True,
        timeout=30,
        stdout=subprocess.DEVNULL,
    )

    update_dashboard(
        detail="Home applied; applying lock screen",
        wallpaper="Home applied; applying lock",
    )

    subprocess.run(
        ["termux-wallpaper", "-l", "-f", LOCK_OUT],
        check=True,
        timeout=30,
        stdout=subprocess.DEVNULL,
    )

    update_dashboard(
        phase="PLAYING",
        detail="Both wallpapers applied successfully",
        wallpaper="Home + lock applied",
        last_update=timestamp(),
        error="None",
    )


# =====================================================
# MAIN MONITOR
# =====================================================

def main():
    global last_track
    global last_attempt_track
    global last_attempt_time

    render_dashboard()

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
                        update_dashboard(
                            track=title,
                            artist=artist or "Unknown artist",
                            phase="NEW TRACK",
                            detail="Looking up album artwork",
                            artwork="Searching...",
                            wallpaper="Waiting for artwork",
                            error="None",
                        )

                        last_attempt_track = signature
                        last_attempt_time = now

                        try:
                            art_url = find_artwork(
                                title, artist
                            )

                            if art_url:
                                make_wallpapers(
                                    art_url, title, artist
                                )

                                set_wallpaper()
                                last_track = signature

                                update_dashboard(
                                    phase="PLAYING",
                                    detail="Both wallpapers updated successfully",
                                    artwork="Matched",
                                    wallpaper="Home + lock applied",
                                    last_update=timestamp(),
                                    error="None",
                                )

                            else:
                                update_dashboard(
                                    phase="WAITING TO RETRY",
                                    detail=(
                                        f"No artwork; retry in "
                                        f"{RETRY_INTERVAL}s"
                                    ),
                                    artwork="Unavailable",
                                    wallpaper="Unchanged",
                                )

                        except Exception as error:
                            update_dashboard(
                                phase="UPDATE FAILED",
                                detail="Wallpaper update encountered an error",
                                error=str(error),
                            )

            else:
                if dashboard["phase"] in {
                    "STARTING",
                    "PLAYING",
                    "WAITING TO RETRY",
                }:
                    update_dashboard(
                        phase="WAITING FOR MUSIC",
                        detail="Waiting for Echo Music notifications",
                    )

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            if USE_COLOUR:
                sys.stdout.write("\033[2J\033[H")

            print(
                paint(
                    "■ EchoGlow stopped. Stay neon, Aki.",
                    C.MAGENTA + C.BOLD,
                ),
                flush=True,
            )
            break

        except Exception as error:
            update_dashboard(
                phase="MONITOR ERROR",
                detail="Notification monitoring encountered an error",
                error=str(error),
            )
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
