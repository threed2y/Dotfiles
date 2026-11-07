import fcntl
import os
import queue
import signal
import subprocess
import sys
import threading
import time
import traceback
from collections import namedtuple

RUNTIME = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
PIDFILE = os.path.join(RUNTIME, "mpris-popup.pid")
DEBUG = bool(os.environ.get("MPRIS_POPUP_DEBUG"))


def claim_or_toggle():
    """Single instance toggle: if another popup holds the lock, ask it to
    close (SIGTERM) and exit; otherwise take the lock and record our pid.

    Runs before the heavy gi imports so a quick double click can't start two
    popups. Returns the lock fd, which must stay open for our whole lifetime
    (Python fds are non-inheritable, so playerctl children never keep it)."""
    try:
        fd = os.open(PIDFILE, os.O_RDWR | os.O_CREAT, 0o600)
    except OSError:
        return None
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        try:
            pid = int(os.pread(fd, 32, 0).decode().strip() or 0)
        except (OSError, ValueError):
            pid = 0
        if pid > 0 and pid != os.getpid():
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
        sys.exit(0)
    except OSError:
        return fd  # locking unsupported here: run anyway, just without toggle
    os.ftruncate(fd, 0)
    os.pwrite(fd, str(os.getpid()).encode(), 0)
    return fd


_LOCK_FD = claim_or_toggle() if __name__ == "__main__" else None

import gi  # noqa: E402

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk  # noqa: E402

import warnings  # noqa: E402

_signal_add = None
try:
    gi.require_version("GLibUnix", "2.0")
    from gi.repository import GLibUnix
    _signal_add = (getattr(GLibUnix, "signal_add", None)
                   or getattr(GLibUnix, "signal_add_full", None))
except (ValueError, ImportError):
    pass
if _signal_add is None:  # older GLib: the old call, minus its deprecation noise
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", message=".*unix_signal_add.*")
    _signal_add = GLib.unix_signal_add

try:
    gi.require_version("GtkLayerShell", "0.1")
    from gi.repository import GtkLayerShell
except (ValueError, ImportError):
    GtkLayerShell = None

# ── Layout: keep in step with your waybar config ─────────────────────────────
BAR_MARGIN_TOP = 6      # waybar "margin-top"
BAR_HEIGHT = 32         # waybar "height"
GAP = 6                 # space between pill and dropdown
LEFT = 12               # waybar "margin-left"
WIDTH = 350
MIN_HEIGHT = 240        # window height floor; raised to the card's real height if taller
ART = 88                # cover size in px
SLIDE_MS = 300
IDLE_CLOSE_MS = 1400    # close this long after the pointer leaves
FIRST_CLOSE_MS = 3500   # close if the pointer never enters

# ── Timing ───────────────────────────────────────────────────────────────────
POLL_MS = 1000          # re-read player/track/status/position this often
TICK_MS = 50            # progress bar extrapolation between polls
FADE_ART_MS = 220       # cover art fades in when it (re)loads
CMD_POLL_DELAY_MS = 150  # poll this long after a button press / seek
SEEK_DEBOUNCE_MS = 150  # keyboard / wheel seeks are committed after this pause
SHOW_WAIT_MS = 400      # show anyway if the first poll hasn't answered by then
WATCHDOG_MS = 800       # slack after SLIDE_MS before a stuck close is forced
PC_TIMEOUT = 2          # seconds for one playerctl call
ART_TIMEOUT = 8         # seconds for the cover-art script
ART_RETRY_S = 1.0       # one retry: artUrl can lag behind the title change

HERE = os.path.dirname(os.path.abspath(__file__))
ART_SCRIPT = os.path.join(HERE, "mpris-art.sh")
COLORS = os.path.expanduser("~/.config/waybar/colors.css")

SEP = "\x1f"
# NB: position is deliberately not in here; it is read with `playerctl position`.
FMT = SEP.join(["{{status}}", "{{title}}", "{{artist}}", "{{album}}",
                "{{mpris:length}}", "{{mpris:artUrl}}"])

# Nerd Font (Material Design) glyphs, as escapes so they can't get lost
ICON_PREV = chr(0xF04AE)
ICON_NEXT = chr(0xF04AD)
ICON_PLAY = chr(0xF040A)
ICON_PAUSE = chr(0xF03E4)

FALLBACK_COLORS = """
@define-color background #11140f;
@define-color foreground #e0e4da;
@define-color primary #a4d397;
@define-color on-primary #0f380d;
@define-color on-surface-variant #c2c8bc;
@define-color outline #8c9387;
"""

CSS = """
* { font-family: "JetBrainsMono Nerd Font", monospace; font-size: 13px; }
window#popup { background: transparent; }
#card {
    background: alpha(@background, 0.6);
    border: 1px solid alpha(@foreground, 0.14);
    border-radius: 4px;
    padding: 14px;
}
#art { background: alpha(@foreground, 0.08); border-radius: 3px; }
#title { font-weight: bold; color: @foreground; }
#artist { color: @on-surface-variant; }
#album, #time { color: alpha(@foreground, 0.55); font-size: 11px; }
scale trough { min-height: 4px; background: alpha(@foreground, 0.15); border-radius: 2px; }
scale highlight { background: @primary; border-radius: 2px; }
scale slider { min-width: 10px; min-height: 10px; margin: -4px; border-radius: 5px;
               background: @primary; border: none; }
button { background: transparent; color: @foreground; border: none; box-shadow: none;
         border-radius: 4px; padding: 2px 16px; font-size: 18px;
         transition: background 160ms ease-out, color 160ms ease-out; }
button:hover { background: alpha(@primary, 0.18); }
button:active { background: alpha(@primary, 0.30); transition-duration: 60ms; }
button#play { background: @primary; color: @on-primary; }
button#play:hover { background: alpha(@primary, 0.85); }
button#play:active { background: alpha(@primary, 0.70); }
scale highlight, scale slider { transition: background 160ms ease-out; }
"""


# ── playerctl helpers (only ever called from worker threads) ─────────────────
class PlayerctlError(Exception):
    """playerctl timed out or could not be started (transient/system level)."""


def pc(*args):
    """Run playerctl. Returns stdout, or None if it exited non-zero (no such
    player / no players). Raises PlayerctlError on timeout or missing binary,
    so a slow call is never mistaken for "nothing is playing"."""
    try:
        r = subprocess.run(["playerctl", *args], capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           stdin=subprocess.DEVNULL, timeout=PC_TIMEOUT)
    except (OSError, subprocess.SubprocessError) as e:
        raise PlayerctlError(str(e))
    return r.stdout if r.returncode == 0 else None


Info = namedtuple("Info", "name status title artist album length art_url")


def to_int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def fmt_time(us):
    s = max(0, int(us // 1_000_000))
    return "%d:%02d" % (s // 60, s % 60)


def parse_meta(out):
    """Split one FMT line. Only newlines are trimmed: str.strip() would also
    eat the \\x1f separators, which Python counts as whitespace."""
    parts = out.strip("\n").split(SEP)
    parts += [""] * (6 - len(parts))
    status, title, artist, album, length, art_url = (
        p.replace("\n", " ").strip() for p in parts[:6])
    return status, title, artist, album, max(0, to_int(length)), art_url


def choose_player(infos, prefer):
    """Pick the player to show. Playing beats everything; otherwise stay on the
    current player if it still exists (no flip-flopping between idle players),
    preferring ones that are paused over ones that are stopped."""
    if not infos:
        return None
    playing = [i for i in infos if i.status == "Playing"]
    if playing:
        return next((i for i in playing if i.name == prefer), playing[0])
    paused = [i for i in infos if i.status == "Paused"]
    if paused:
        return next((i for i in paused if i.name == prefer), paused[0])
    return next((i for i in infos if i.name == prefer), infos[0])


def parse_position_us(out):
    """`playerctl position` prints seconds as a float."""
    try:
        return max(0, int(float(out.strip()) * 1_000_000))
    except (AttributeError, ValueError):
        return None


class Worker:
    """One daemon thread that runs queued callables in order."""

    def __init__(self, name):
        self._q = queue.SimpleQueue()
        threading.Thread(target=self._run, name=name, daemon=True).start()

    def submit(self, fn, *args):
        self._q.put((fn, args))

    def _run(self):
        while True:
            fn, args = self._q.get()
            try:
                fn(*args)
            except Exception:
                if DEBUG:
                    traceback.print_exc()


def set_text(label, text):
    if label.get_text() != text:
        label.set_text(text)


class Fader:
    """Animates a widget's opacity on GTK's frame clock.

    Using the frame clock (not a timeout) keeps the fade in step with the
    Revealer's slide and with the compositor's frames, and it costs nothing
    while idle: the tick callback only exists while a fade is running."""

    def __init__(self, widget):
        self.w = widget
        self.tick = None
        self.a = self.b = widget.get_opacity()
        self.ms = 1
        self.t0 = None

    def to(self, target, ms, start=None):
        if start is not None:
            self.w.set_opacity(start)
        self.a, self.b = self.w.get_opacity(), target
        self.ms, self.t0 = max(1, ms), None
        if self.a == self.b:
            self.stop()
        elif self.tick is None:
            self.tick = self.w.add_tick_callback(self._step)

    def _step(self, widget, clock):
        now = clock.get_frame_time()          # microseconds
        if self.t0 is None:
            self.t0 = now
        t = min(1.0, (now - self.t0) / (self.ms * 1000.0))
        # ease-out when appearing, ease-in when leaving
        e = 1.0 - (1.0 - t) ** 3 if self.b > self.a else t * t
        widget.set_opacity(self.a + (self.b - self.a) * e)
        if t >= 1.0:
            self.tick = None
            return GLib.SOURCE_REMOVE
        return GLib.SOURCE_CONTINUE

    def stop(self):
        if self.tick is not None:
            self.w.remove_tick_callback(self.tick)
            self.tick = None


class Popup:
    def __init__(self, on_quit):
        self.on_quit = on_quit

        # what the UI currently believes about the player
        self.player = None
        self.status = "Stopped"
        self.length = 0               # µs
        self.base_pos = 0             # µs, as of base_t
        self.base_t = time.monotonic()
        self.track_key = None
        self.art_gen = 0              # bumped on every track change; guards async art

        # seeking
        self.seeking = False          # primary button held on the slider
        self.seek_target = None       # 0..1, not yet sent to the player
        self.seek_timer = None
        self.seek_serial = 0          # polls issued before a seek are stale

        # lifecycle
        self.pointer_inside = False
        self.shown = False
        self.reveal_started = False
        self.closing = False
        self.finished = False
        self.idle_src = self.poll_src = self.tick_src = self.watchdog_src = None

        # background work
        self.polls_queued = 0
        self._cmd_inflight = 0
        self._cmd_lock = threading.Lock()
        self.worker = Worker("playerctl")
        self.art_worker = Worker("cover-art")

        win = self.win = Gtk.Window()
        win.set_name("popup")
        win.set_title("mpris-popup")
        win.set_app_paintable(True)
        vis = win.get_screen().get_rgba_visual()
        if vis:
            win.set_visual(vis)
        win.set_resizable(False)
        win.set_decorated(False)

        if GtkLayerShell and GtkLayerShell.is_supported():
            GtkLayerShell.init_for_window(win)
            GtkLayerShell.set_namespace(win, "mpris-popup")
            GtkLayerShell.set_layer(win, GtkLayerShell.Layer.TOP)
            GtkLayerShell.set_anchor(win, GtkLayerShell.Edge.TOP, True)
            GtkLayerShell.set_anchor(win, GtkLayerShell.Edge.LEFT, True)
            GtkLayerShell.set_margin(win, GtkLayerShell.Edge.TOP,
                                     BAR_MARGIN_TOP + BAR_HEIGHT + GAP)
            GtkLayerShell.set_margin(win, GtkLayerShell.Edge.LEFT, LEFT)
            # -1 = ignore waybar's reserved strip, so the margins above are
            # measured from the screen edge and the card sits right under the pill
            GtkLayerShell.set_exclusive_zone(win, -1)
            GtkLayerShell.set_keyboard_mode(
                win, GtkLayerShell.KeyboardMode.ON_DEMAND)

        card = self.card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card.set_name("card")
        card.set_size_request(WIDTH, -1)
        card.set_opacity(0.0)                  # fades in together with the slide
        self.card_fade = Fader(card)

        top = Gtk.Box(spacing=14)
        self.art = Gtk.Image()
        self.art.set_name("art")
        self.art.set_size_request(ART, ART)
        self.art.set_valign(Gtk.Align.CENTER)
        self.art_fade = Fader(self.art)
        top.pack_start(self.art, False, False, 0)

        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info.set_valign(Gtk.Align.CENTER)
        self.title = self._label("title", 20)
        self.artist = self._label("artist", 22)
        self.album = self._label("album", 26)
        for w in (self.title, self.artist, self.album):
            info.pack_start(w, False, False, 0)
        top.pack_start(info, True, True, 0)
        card.pack_start(top, False, False, 0)

        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, 0.001)
        self.scale.set_draw_value(False)
        self.scale.set_can_focus(False)
        self.scale.connect("change-value", self.on_seek)
        self.scale.connect("button-press-event", self.on_scale_press)
        self.scale.connect("button-release-event", self.on_scale_release)
        card.pack_start(self.scale, False, False, 0)

        times = Gtk.Box()
        self.t_now = Gtk.Label(label="0:00", xalign=0)
        self.t_len = Gtk.Label(label="0:00", xalign=1)
        for w in (self.t_now, self.t_len):
            w.set_name("time")
        times.pack_start(self.t_now, True, True, 0)
        times.pack_start(self.t_len, True, True, 0)
        card.pack_start(times, False, False, 0)

        controls = Gtk.Box(spacing=8)
        controls.set_halign(Gtk.Align.CENTER)
        self.btn_prev = self._button(ICON_PREV, "prev", "previous")
        self.btn_play = self._button(ICON_PLAY, "play", "play-pause")
        self.btn_next = self._button(ICON_NEXT, "next", "next")
        for b in (self.btn_prev, self.btn_play, self.btn_next):
            controls.pack_start(b, False, False, 0)
        card.pack_start(controls, False, False, 0)

        self.rev = Gtk.Revealer()
        self.rev.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self.rev.set_transition_duration(SLIDE_MS)
        self.rev.add(card)
        self.rev.connect("notify::child-revealed", self.on_reveal_done)
        win.add(self.rev)

        win.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK |
                       Gdk.EventMask.LEAVE_NOTIFY_MASK)
        win.connect("enter-notify-event", self.on_enter)
        win.connect("leave-notify-event", self.on_leave)
        win.connect("key-press-event", self.on_key)

        self.load_css()

        # A Revealer shrinks the window's minimum height to 0 while collapsed, so
        # the surface size is whatever we request here. Fix it once, from the
        # card's real height (never smaller than before), so the layer-shell
        # surface is never resized while the slide animation runs.
        try:
            nat = card.get_preferred_height_for_width(WIDTH)[1]
        except Exception:
            nat = 0
        height = max(MIN_HEIGHT, nat)
        win.set_size_request(WIDTH, height)
        win.set_default_size(WIDTH, height)

        # Ask for data now; the window appears with it (or after SHOW_WAIT_MS).
        set_text(self.title, "Nothing playing")
        self.request_poll()
        GLib.timeout_add(SHOW_WAIT_MS, self.show_now)

    # ── helpers ──────────────────────────────────────────────────────────
    def _label(self, name, chars):
        l = Gtk.Label(xalign=0)
        l.set_name(name)
        l.set_ellipsize(3)  # Pango.EllipsizeMode.END
        l.set_max_width_chars(chars)
        return l

    def _button(self, glyph, name, action):
        b = Gtk.Button(label=glyph)
        b.set_name(name)
        b.set_can_focus(False)
        b.set_relief(Gtk.ReliefStyle.NONE)
        b.connect("clicked", lambda *_: self.act(action))
        return b

    def load_css(self):
        try:
            with open(COLORS) as f:
                colors = f.read()
        except OSError:
            colors = FALLBACK_COLORS
        prov = Gtk.CssProvider()
        try:
            prov.load_from_data((colors + CSS).encode())
        except GLib.Error:
            prov.load_from_data((FALLBACK_COLORS + CSS).encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), prov, Gtk.STYLE_PROVIDER_PRIORITY_USER)

    def _drop(self, attr):
        sid = getattr(self, attr)
        if sid:
            GLib.source_remove(sid)
            setattr(self, attr, None)

    # ── polling (worker thread -> idle_add -> apply) ─────────────────────
    def request_poll(self):
        # at most one running + one queued, so a slow playerctl can't pile up
        if self.closing or self.polls_queued >= 2:
            return
        self.polls_queued += 1
        self.worker.submit(self._poll_job, self.player, self.seek_serial)

    def _poll_job(self, prefer, serial):
        try:
            res = self._poll(prefer, serial)
        except Exception:  # playerctl timeout etc.: keep what's on screen
            if DEBUG:
                traceback.print_exc()
            res = None
        GLib.idle_add(self._on_poll, res)

    def _poll(self, prefer, serial):
        listing = pc("-l") or ""   # rc != 0 just means "no players"
        infos = []
        for name in (n.strip() for n in listing.splitlines()):
            if not name:
                continue
            out = pc("-p", name, "metadata", "--format", FMT)
            if out is None:        # vanished between -l and now
                continue
            infos.append(Info(name, *parse_meta(out)))
        chosen = choose_player(infos, prefer)
        res = {"player": None, "status": "Stopped", "title": "", "artist": "",
               "album": "", "length": 0, "art_url": "", "position": None,
               "sampled": time.monotonic(), "seek_serial": serial}
        if chosen:
            res.update(player=chosen.name, status=chosen.status or "Stopped",
                       title=chosen.title, artist=chosen.artist,
                       album=chosen.album, length=chosen.length,
                       art_url=chosen.art_url)
            if res["status"] != "Stopped":
                out = pc("-p", chosen.name, "position")
                res["sampled"] = time.monotonic()
                res["position"] = parse_position_us(out) if out else None
        return res

    def _on_poll(self, res):
        self.polls_queued = max(0, self.polls_queued - 1)
        if res is not None and not self.closing:
            self.apply(res)
        return False

    def apply(self, r):
        if not self.shown:
            self.show_now()
        self.player = r["player"]
        if r["player"] is None or (r["status"] == "Stopped" and not r["title"]):
            self._show_nothing()
            return

        key = (r["player"], r["title"], r["artist"], r["album"], r["art_url"])
        self.status = r["status"]
        self.length = r["length"]
        set_text(self.title, r["title"] or "Unknown title")
        set_text(self.artist, r["artist"])
        set_text(self.album, r["album"])
        set_text(self.t_len, fmt_time(self.length))
        glyph = ICON_PAUSE if self.status == "Playing" else ICON_PLAY
        if self.btn_play.get_label() != glyph:
            self.btn_play.set_label(glyph)

        changed = key != self.track_key
        pos = r["position"]
        if pos is not None:
            # ignore positions sampled before our last seek, or while the user
            # is still moving the slider
            if (r["seek_serial"] == self.seek_serial and not self.seeking
                    and self.seek_timer is None):
                self.base_pos, self.base_t = pos, r["sampled"]
        elif changed:
            self.base_pos, self.base_t = 0, time.monotonic()
        if changed:
            self._track_changed(key)

    def _show_nothing(self):
        self.status = "Stopped"
        self.length = 0
        self.base_pos, self.base_t = 0, time.monotonic()
        set_text(self.title, "Nothing playing")
        set_text(self.artist, "")
        set_text(self.album, "")
        set_text(self.t_now, "0:00")
        set_text(self.t_len, "0:00")
        if self.btn_play.get_label() != ICON_PLAY:
            self.btn_play.set_label(ICON_PLAY)
        if not self.seeking:
            self.scale.set_value(0)
        if self.track_key is not None:
            self.track_key = None
            self.art_gen += 1      # any art still loading is now stale
            self.art.clear()

    def position_now(self):
        pos = self.base_pos
        if self.status == "Playing":
            pos += int((time.monotonic() - self.base_t) * 1_000_000)
        if self.length:
            pos = min(pos, self.length)
        return max(0, pos)

    def tick(self):
        if self.closing:
            self.tick_src = None
            return False
        if not self.seeking and self.seek_target is None:
            pos = self.position_now()
            frac = pos / self.length if self.length else 0.0
            if abs(frac - self.scale.get_value()) > 0.0002:
                self.scale.set_value(frac)
            set_text(self.t_now, fmt_time(pos))
        return True

    def on_poll_timer(self):
        if self.closing:
            self.poll_src = None
            return False
        self.request_poll()
        return True

    # ── cover art (own thread; result applied only if still current) ─────
    def _track_changed(self, key):
        old, self.track_key = self.track_key, key
        self.art_gen += 1
        if old is None or (old[0], old[2], old[3]) != (key[0], key[2], key[3]):
            self.art.clear()       # different album: don't show the wrong cover
        self.art_worker.submit(self._art_job, self.art_gen)

    def _art_job(self, gen):
        pixbuf = None
        for attempt in range(2):
            if gen != self.art_gen or self.closing:
                return             # superseded while queued/running
            pixbuf = self._load_art(self._run_art_script(gen))
            if pixbuf is not None:
                break
            if attempt == 0:
                # wait before retrying, but give up the moment we're superseded
                end = time.monotonic() + ART_RETRY_S
                while time.monotonic() < end:
                    if gen != self.art_gen or self.closing:
                        return
                    time.sleep(0.05)
        GLib.idle_add(self._set_art, gen, pixbuf)

    def _run_art_script(self, gen):
        """Run mpris-art.sh and return the path it prints. A script that is
        slow for a track we've already skipped is killed, so it can't hold up
        the cover of the track that is current now."""
        try:
            p = subprocess.Popen(["sh", ART_SCRIPT], stdout=subprocess.PIPE,
                                 stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
                                 text=True, encoding="utf-8", errors="replace",
                                 start_new_session=True)
        except OSError:
            return ""
        deadline = time.monotonic() + ART_TIMEOUT
        while True:
            try:
                out, _ = p.communicate(timeout=0.15)
                break
            except subprocess.TimeoutExpired:
                if gen != self.art_gen or self.closing or time.monotonic() > deadline:
                    try:
                        os.killpg(p.pid, signal.SIGKILL)  # script + anything it spawned
                    except OSError:
                        p.kill()
                    p.communicate()
                    return ""
        lines = out.strip().splitlines()
        return lines[0].strip() if lines else ""

    @staticmethod
    def _load_art(path):
        if not path:
            return None
        try:
            return GdkPixbuf.Pixbuf.new_from_file_at_scale(path, ART, ART, True)
        except GLib.Error:
            return None

    def _set_art(self, gen, pixbuf):
        if gen == self.art_gen and not self.closing:
            if pixbuf is not None:
                # fade in from nothing; if replacing a cover, only dip a little
                dip = 0.0 if self.art.get_pixbuf() is None else 0.55
                self.art.set_from_pixbuf(pixbuf)
                self.art_fade.to(1.0, FADE_ART_MS, start=dip)
            else:
                self.art_fade.stop()
                self.art.set_opacity(1.0)
                self.art.clear()
        return False

    # ── controls ─────────────────────────────────────────────────────────
    def act(self, action):
        player = self.player
        if player and not self.closing:
            self.cmd(lambda: pc("-p", player, action))

    def cmd(self, fn):
        with self._cmd_lock:
            self._cmd_inflight += 1
        self.worker.submit(self._cmd_job, fn)

    def _cmd_job(self, fn):
        try:
            fn()
        finally:
            with self._cmd_lock:
                self._cmd_inflight -= 1
            GLib.idle_add(self._after_cmd)

    def _after_cmd(self):
        if not self.closing:
            GLib.timeout_add(CMD_POLL_DELAY_MS, self._delayed_poll)
        return False

    def _delayed_poll(self):
        self.request_poll()
        return False

    # ── seeking ──────────────────────────────────────────────────────────
    def on_scale_press(self, _w, ev):
        if ev.button in (1, 2):
            self.seeking = True
            self.cancel_idle()
        return False

    def on_scale_release(self, _w, _ev):
        self.end_seek()
        return False

    def end_seek(self):
        if not self.seeking:
            return
        self.seeking = False
        self.commit_seek()
        if not self.pointer_inside and not self.closing:
            self.arm_idle(IDLE_CLOSE_MS)

    def on_seek(self, _scale, _scroll, value):
        if not (self.player and self.length):
            return True            # nothing to seek in: keep the slider put
        value = min(max(value, 0.0), 1.0)
        self.seek_target = value
        set_text(self.t_now, fmt_time(value * self.length))
        if not self.seeking:       # keyboard/wheel: no press..release to wait for
            self._drop("seek_timer")
            self.seek_timer = GLib.timeout_add(SEEK_DEBOUNCE_MS, self._seek_timer_fired)
        return False               # let GTK move the slider

    def _seek_timer_fired(self):
        self.seek_timer = None
        self.commit_seek()
        return False

    def commit_seek(self):
        """Send the pending seek once. Position only changes on the player side
        here; the bar is moved optimistically so it doesn't jump back."""
        self._drop("seek_timer")
        frac, self.seek_target = self.seek_target, None
        if frac is None or not self.player or not self.length:
            return
        pos = int(frac * self.length)
        self.seek_serial += 1
        self.base_pos, self.base_t = pos, time.monotonic()
        player = self.player
        self.cmd(lambda: pc("-p", player, "position", "%.3f" % (pos / 1e6)))

    # ── open / close behaviour ───────────────────────────────────────────
    def show_now(self):
        if self.shown or self.closing:
            return False
        self.shown = True
        self.win.show_all()
        # reveal only once the window is mapped, otherwise GtkRevealer jumps
        # straight to the end state instead of animating
        GLib.idle_add(self.start_reveal)
        self.poll_src = GLib.timeout_add(POLL_MS, self.on_poll_timer)
        self.tick_src = GLib.timeout_add(TICK_MS, self.tick)
        self.arm_idle(FIRST_CLOSE_MS)
        return False

    def start_reveal(self):
        if not self.closing:
            self.reveal_started = True
            self.rev.set_reveal_child(True)
            self.card_fade.to(1.0, SLIDE_MS)
        return False

    def arm_idle(self, ms):
        self.cancel_idle()
        if not self.closing:
            self.idle_src = GLib.timeout_add(ms, self._idle_fired)

    def cancel_idle(self):
        self._drop("idle_src")

    def _idle_fired(self):
        self.idle_src = None
        self.close()
        return False

    def on_enter(self, _w, ev):
        if ev.detail == Gdk.NotifyType.INFERIOR:
            return False
        self.pointer_inside = True
        if self.seeking and not (ev.state & Gdk.ModifierType.BUTTON1_MASK):
            self.end_seek()        # missed the release; don't stay "seeking"
        self.cancel_idle()
        return False

    def on_leave(self, _w, ev):
        if ev.detail == Gdk.NotifyType.INFERIOR:
            return False
        self.pointer_inside = False
        if self.seeking and not (ev.state & Gdk.ModifierType.BUTTON1_MASK):
            self.end_seek()
        if not self.seeking:       # dragging the slider outside is not "leaving"
            self.arm_idle(IDLE_CLOSE_MS)
        return False

    def on_key(self, _w, ev):
        if ev.keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False

    def on_reveal_done(self, _revealer, _pspec):
        # Emitted when a transition reaches its target. child-revealed is False
        # at the end of a slide-out and True at the end of a slide-in, so this
        # only fires finish() when the closing animation has really completed.
        if self.closing and not self.rev.get_child_revealed():
            self.finish()

    def close(self, *_):
        if self.closing:
            return False
        self.closing = True
        self.cancel_idle()
        self._drop("poll_src")
        self._drop("tick_src")
        if self.seek_target is not None:
            self.commit_seek()
        self._drop("seek_timer")
        if not self.reveal_started:
            # Never began to slide in: set_reveal_child(False) would be a no-op
            # and emit no notify, so there is nothing to wait for.
            self.finish()
            return False
        self.watchdog_src = GLib.timeout_add(SLIDE_MS + WATCHDOG_MS, self._watchdog)
        self.card_fade.to(0.0, SLIDE_MS)   # fade out while it slides away
        self.rev.set_reveal_child(False)   # on_reveal_done() quits when it ends
        return False

    def _watchdog(self):
        self.watchdog_src = None
        self.finish()
        return False

    def finish(self):
        if self.finished:
            return False
        self.finished = True
        self.closing = True
        self.cancel_idle()
        for attr in ("poll_src", "tick_src", "seek_timer", "watchdog_src"):
            self._drop(attr)
        self.card_fade.stop()
        self.art_fade.stop()
        if self.shown:
            self.win.hide()        # slide-out is done; free the screen first
        # then let an already-sent command (play/pause, seek...) reach playerctl
        deadline = time.monotonic() + 1.5
        while self._cmd_inflight and time.monotonic() < deadline:
            time.sleep(0.01)
        self.on_quit()
        return False


def main():
    holder = {}

    def on_signal(*_):
        # keep this source alive (return True): a second click while the popup
        # is already sliding out must be ignored, not kill it mid-animation
        popup = holder.get("popup")
        if popup is not None:
            popup.close()
        return GLib.SOURCE_CONTINUE

    _signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, on_signal)
    _signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, on_signal)
    holder["popup"] = Popup(Gtk.main_quit)
    Gtk.main()


if __name__ == "__main__":
    try:
        main()
    finally:
        # worker threads are daemons and may be inside a subprocess call: leave
        # immediately so the process (and its toggle lock) never lingers
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(0)
