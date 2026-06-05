import asyncio
import threading
import subprocess
import logging
import winreg
import ctypes
import yaml
import os
from flask import Flask, jsonify, request
from bscpylgtv import WebOsClient
from PIL import Image, ImageDraw
import pystray

with open('config.yaml') as f:
    cfg = yaml.safe_load(f)

TV_IP               = cfg['tv']['ip']
TV_DEFAULT_INPUT    = cfg['tv']['default_input']
TV_PC_INPUT         = cfg['tv']['pc_input']
TV_AUDIO_SOURCE     = cfg['tv']['audio_source']
TV_RESOLUTION_SCALE = cfg['tv'].get('resolution_scale', 125)

PC_MONITOR_INDEX    = cfg['pc']['monitor_index']
PC_AUDIO_SOURCE     = cfg['pc']['audio_source']
PC_RESOLUTION_SCALE = cfg['pc'].get('resolution_scale', 100)

COMMAND_TIMEOUT     = cfg['connection']['command_timeout']
RECONNECT_DELAY     = cfg['connection']['reconnect_delay']
PING_INTERVAL       = cfg['connection']['ping_interval']
PORT                = cfg['server']['port']

IDLE_TIMEOUT        = cfg['idle']['timeout_seconds']  # 0 = disabled
IDLE_IGNORE_TV_MEDIA = cfg['idle']['ignore_if_tv_media_playing']
IDLE_TV_MEDIA_APPS  = cfg['idle']['tv_media_apps']
IDLE_PC_MEDIA_CHECK = cfg['idle']['pc_media_check_cmd']

INPUT_MAP = {
    'HDMI_1': 'com.webos.app.hdmi1',
    'HDMI_2': 'com.webos.app.hdmi2',
    'HDMI_3': 'com.webos.app.hdmi3',
    'HDMI_4': 'com.webos.app.hdmi4'
}

import time

# ── Mode tracking ─────────────────────────────────────────────────────────────
# 'tv' = TV screen on, TV audio, TV scale
# 'pc' = TV screen off, PC audio, PC scale
_current_mode    = 'pc'
_last_activity   = time.monotonic()

def record_activity():
    global _last_activity
    _last_activity = time.monotonic()

logging.basicConfig(level=logging.INFO)
log = logging.getLogger('tv')

app = Flask(__name__)

@app.after_request
def _stamp_activity(response):
    """Any successful TV command resets the idle clock."""
    if request.path.startswith('/tv/') and response.status_code == 200:
        record_activity()
    return response

class TVConnection:
    def __init__(self, ip):
        self.ip             = ip
        self.screensaver_on = False
        self._client        = None
        self._connected     = False
        self._reconnecting  = False
        self._loop          = asyncio.new_event_loop()
        self._thread        = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        asyncio.run_coroutine_threadsafe(self._connect(), self._loop)

    def _run(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    async def _connect(self):
        if self._reconnecting:
            return # already trying, don't stack attempts
        self._reconnecting = True
        self._connected    = False
        while True:
            try:
                log.info('Connecting to TV...')
                self._client = await WebOsClient.create(
                    self.ip,
                    ping_interval=PING_INTERVAL,
                )
                # uncomment to listen for state
                # await self._client.register_state_update_callback(self.log_state)
                await self._client.connect()
                self.list_apps();
                self._connected    = True
                # start a keepalive task to detect silent disconnects
                try:
                    asyncio.create_task(self._keepalive(self._client))
                except Exception:
                    log.debug('Failed to start keepalive task')
                self._reconnecting = False
                log.info('Connected')
                return
            except Exception as e:
                log.warning(f'Connection failed: {e} — retrying in {RECONNECT_DELAY}s')
                await asyncio.sleep(RECONNECT_DELAY)

    async def _keepalive(self, client):
        """Periodically perform a lightweight call to detect disconnects.
        If the call fails, mark disconnected and trigger reconnect.
        """
        while True:
            await asyncio.sleep(PING_INTERVAL)
            try:
                # lightweight status fetch to surface connection errors
                await client.get_input()
            except Exception as e:
                log.warning(f'Keepalive detected disconnect: {e}')
                self._connected = False
                # fire reconnect, don't block
                try:
                    asyncio.create_task(self._connect())
                except Exception:
                    log.debug('Failed to schedule reconnect from keepalive')
                return

    async def _exec(self, cmd):
        if not self._connected:
            raise ConnectionError('TV not connected')
        try:
            return await cmd(self._client)
        except Exception as e:
            self._connected = False
            asyncio.create_task(self._connect()) # fire reconnect, don't block
            raise

    async def log_state(self, client):
        print('* State Changed')
        print(f'  power_state:   {client.power_state}')
        print(f'  current_appId: {client.current_appId}')
        print(f'  muted:         {client.muted}')
        print(f'  volume:        {client.volume}')

    def list_apps(self):
        print('* Installed Apps:')
        result = {v["title"]: v["id"] for v in self._client.apps.values()}
        print(result)

    def run(self, cmd):
        '''Synchronous bridge for Flask routes.'''
        fut = asyncio.run_coroutine_threadsafe(self._exec(cmd), self._loop)
        try:
            fut.result(timeout=COMMAND_TIMEOUT)
            return True, None
        except TimeoutError:
            return False, 'timeout'
        except Exception as e:
            return False, str(e)

tv = TVConnection(TV_IP)

# response helper
def respond(ok, err=None):
    if ok:
        return jsonify(ok=True)
    return jsonify(ok=False, error=err), 503

# routes
@app.route('/tv/status')
def status():
    return jsonify(connected=tv._connected, reconnecting=tv._reconnecting)

@app.route('/tv/toggle-screen')
def toggle_screen_on():
    return respond(*tv.run(lambda c: 
        c.turn_screen_off() if c.power_state['state'] == 'Active' else c.turn_screen_on()))

@app.route('/tv/toggle-screensaver')
def toggle_screensaver():
    app_name = 'com.webos.app.screensaver'
    tv.screensaver_on = not tv.screensaver_on
    return respond(*tv.run(lambda c:               
        c.close_app(app_name) if tv.screensaver_on else c.launch_app(app_name)))

@app.route('/tv/volume-up')
def vol_up():
    return respond(*tv.run(lambda c: c.volume_up()))

@app.route('/tv/volume-down')
def vol_down():
    return respond(*tv.run(lambda c: c.volume_down()))

@app.route('/tv/toggle-mute')
def toggle_mute():
    return respond(*tv.run(lambda c: c.set_mute(not c.muted)))

@app.route('/tv/input/<name>')
def set_input(name):
    return respond(*tv.run(lambda c: c.set_input(name)))

@app.route('/tv/button/<key>')
def button(key):
    return respond(*tv.run(lambda c: c.button(key)))

@app.route('/tv/launch-app/<app_id>')
def launch_app(app_id):
    return respond(*tv.run(lambda c: c.launch_app(app_id)))

@app.route('/audio/set-device/<device_name>')
def set_audio_device(device_name):
    switch_audio(device_name)
    return respond(True, None)

@app.route('/display/set-scale/<percent>')
def set_display_scale(percent):
    set_scale(percent)
    return respond(True, None)

@app.route('/tv/quick-toggle')
def quick_toggle():
    global _current_mode
    async def toggle(c):
        global _current_mode
        curr_input  = await c.get_input()
        mapped_input = INPUT_MAP.get(TV_PC_INPUT)
        power_state  = c.power_state['state']

        print(f'Current TV input: {curr_input} (mapped: {mapped_input}), power state: {power_state}')

        # PC is not active on TV, switch
        if curr_input != mapped_input or power_state != 'Active': 
            if (curr_input != mapped_input):
                print('Switching TV input to PC...')
                await c.set_input(TV_PC_INPUT)
            if (power_state != 'Active'):
                print('Turning TV screen on...')
                await c.turn_screen_on()
            switch_audio(TV_AUDIO_SOURCE)
            set_scale(TV_RESOLUTION_SCALE)
            _current_mode = 'tv'
            record_activity()
        # PC is active, switch back
        else:
            if (power_state != 'Screen Off'):
                print('Turning TV screen off...')
                await c.turn_screen_off()
            switch_audio(PC_AUDIO_SOURCE)
            set_scale(PC_RESOLUTION_SCALE)
            _current_mode = 'pc'
    return respond(*tv.run(toggle))


def _revert_to_pc():
    global _current_mode
    log.info('Idle timeout — reverting to PC mode')
    # If configured, skip revert when media is playing on TV or PC
    try:
        if IDLE_IGNORE_TV_MEDIA and tv._connected and tv._client is not None:
            try:
                current_app = getattr(tv._client, 'current_appId', None)
            except Exception:
                current_app = None
            if current_app and current_app in IDLE_TV_MEDIA_APPS:
                log.info(f'Idle abort: TV app {current_app} considered media-playing')
                return
    except Exception:
        log.debug('Error while checking TV media state; proceeding with revert')

    if IDLE_PC_MEDIA_CHECK:
        try:
            # command returns 0 when media is playing (user-configurable)
            res = subprocess.run(IDLE_PC_MEDIA_CHECK, shell=True)
            if res.returncode == 0:
                log.info('Idle abort: PC media check reported active playback')
                return
        except Exception as e:
            log.debug(f'PC media check failed: {e}')
    async def _do(c):
        if c.power_state.get('state') != 'Screen Off':
            await c.turn_screen_off()
    tv.run(_do)
    switch_audio(PC_AUDIO_SOURCE)
    set_scale(PC_RESOLUTION_SCALE)
    _current_mode = 'pc'


def _idle_watchdog():
    while True:
        time.sleep(30)
        if IDLE_TIMEOUT <= 0 or _current_mode != 'tv':
            continue
        elapsed = time.monotonic() - _last_activity
        if elapsed >= IDLE_TIMEOUT:
            _revert_to_pc()

def _start_sleep_watcher():
    """Hidden Win32 message window that forces a reconnect on system resume from sleep."""
    from ctypes import wintypes

    WM_POWERBROADCAST      = 0x0218
    PBT_APMRESUMEAUTOMATIC = 0x0012

    user32   = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    WNDPROCTYPE = ctypes.WINFUNCTYPE(
        ctypes.c_long, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
    )

    class WNDCLASSW(ctypes.Structure):
        _fields_ = [
            ('style',         ctypes.c_uint),
            ('lpfnWndProc',   WNDPROCTYPE),
            ('cbClsExtra',    ctypes.c_int),
            ('cbWndExtra',    ctypes.c_int),
            ('hInstance',     wintypes.HANDLE),
            ('hIcon',         wintypes.HANDLE),
            ('hCursor',       wintypes.HANDLE),
            ('hbrBackground', wintypes.HANDLE),
            ('lpszMenuName',  wintypes.LPCWSTR),
            ('lpszClassName', wintypes.LPCWSTR),
        ]

    def wnd_proc(hwnd, msg, wparam, lparam):
        if msg == WM_POWERBROADCAST and wparam == PBT_APMRESUMEAUTOMATIC:
            log.info('System resumed from sleep — forcing TV reconnect')
            # Reset both flags so _connect() isn't blocked by a stale reconnect loop
            tv._reconnecting = False
            tv._connected    = False
            asyncio.run_coroutine_threadsafe(tv._connect(), tv._loop)
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    proc = WNDPROCTYPE(wnd_proc)

    wc               = WNDCLASSW()
    wc.lpfnWndProc   = proc
    wc.hInstance     = kernel32.GetModuleHandleW(None)
    wc.lpszClassName = 'TVSleepWatcher'

    if not user32.RegisterClassW(ctypes.byref(wc)):
        log.warning('Sleep watcher: RegisterClassW failed — sleep detection disabled')
        return

    hwnd = user32.CreateWindowExW(
        0, 'TVSleepWatcher', None, 0,
        0, 0, 0, 0,
        -3,  # HWND_MESSAGE — message-only window, no visible UI
        None, wc.hInstance, None,
    )
    if not hwnd:
        log.warning('Sleep watcher: CreateWindowExW failed — sleep detection disabled')
        return

    log.info('Sleep watcher active')
    msg = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))

# audio
def switch_audio(device_name):
    subprocess.run(["nircmd.exe", "setdefaultsounddevice", device_name])

def set_scale(percent):
    subprocess.run(["SetDpi.exe", str(percent), str(PC_MONITOR_INDEX)])

# tray
def make_icon(color):
    """Draw a simple tray icon showing status."""
    size = 64
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    detail = (20, 20, 20, 220)   # dark detail color for buttons/accents

    # ── body ──────────────────────────────────────────────────────────────────
    draw.rounded_rectangle([14, 2, 50, 62], radius=9, fill=color)

    # ── power button (top) ────────────────────────────────────────────────────
    draw.ellipse([27, 7, 37, 17], fill=detail)
    draw.arc([29, 9, 35, 15], start=0, end=360, fill=(255, 255, 255, 160), width=1)

    # ── d-pad (middle) ────────────────────────────────────────────────────────
    cx, cy = 32, 36
    draw.rectangle([cx - 8, cy - 2, cx + 8, cy + 2], fill=detail)  # horizontal
    draw.rectangle([cx - 2, cy - 8, cx + 2, cy + 8], fill=detail)  # vertical
    draw.ellipse  ([cx - 3, cy - 3, cx + 3, cy + 3], fill=detail)  # center cap

    # ── two small buttons (bottom) ────────────────────────────────────────────
    draw.ellipse([22, 50, 29, 57], fill=detail)
    draw.ellipse([35, 50, 42, 57], fill=detail)

    return img

ICON_GREEN  = make_icon("#4CAF50")
ICON_YELLOW = make_icon("#FFC107")
ICON_RED    = make_icon("#F44336")

def current_icon():
    if tv._connected:    return ICON_GREEN
    if tv._reconnecting: return ICON_YELLOW
    return ICON_RED

def current_status_label(_):
    if tv._connected:    return "Status: Connected"
    if tv._reconnecting: return "Status: Reconnecting..."
    return "Status: Disconnected"

def quit_app(icon, _):
    icon.stop()
    os._exit(0)

def run_tray():
    def refresh(icon):
        import time as _t
        while True:
            icon.icon  = current_icon()
            icon.title = "LG TV Remote — " + current_status_label(None)
            icon.update_menu()
            _t.sleep(3)

    # ── Menu item callbacks ────────────────────────────────────────────────────

    def retry_connection(icon, _):
        if not tv._connected and not tv._reconnecting:
            log.info('Manual reconnect triggered from tray')
            asyncio.run_coroutine_threadsafe(tv._connect(), tv._loop)

    def toggle_mode_from_tray(icon, _):
        """Tray-triggered mode switch — same logic as /tv/quick-toggle."""
        import urllib.request as _req
        try:
            _req.urlopen(f'http://127.0.0.1:{PORT}/tv/quick-toggle', timeout=COMMAND_TIMEOUT + 2)
        except Exception as e:
            log.warning(f'Tray mode toggle failed: {e}')

    def switch_to_tv(icon, _):
        if _current_mode != 'tv':
            toggle_mode_from_tray(icon, _)

    def switch_to_pc(icon, _):
        if _current_mode != 'pc':
            toggle_mode_from_tray(icon, _)

    # ── Dynamic label helpers ──────────────────────────────────────────────────

    def retry_label(_):
        if tv._reconnecting:
            return "Retrying connection..."
        if tv._connected:
            return "Connection: OK"
        return "Retry connection"

    def retry_enabled(_):
        return not tv._connected and not tv._reconnecting

    # ── Build icon ─────────────────────────────────────────────────────────────

    icon = pystray.Icon(
        name  = "LG TV Remote",
        icon  = ICON_YELLOW,
        title = "LG TV Remote",
        menu  = pystray.Menu(
            pystray.MenuItem(current_status_label, action=None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(retry_label, retry_connection, enabled=retry_enabled),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("TV", switch_to_tv, checked=lambda _: _current_mode == 'tv'),
            pystray.MenuItem("PC", switch_to_pc, checked=lambda _: _current_mode == 'pc'),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", quit_app),
        )
    )

    threading.Thread(target=refresh, args=(icon,), daemon=True).start()
    icon.run()  # blocks — must be main thread

# entry
if __name__ == '__main__':
    flask_thread = threading.Thread(
        target=lambda: app.run(port=PORT, use_reloader=False),
        daemon=True
    )
    flask_thread.start()

    if IDLE_TIMEOUT > 0:
        log.info(f'Idle timeout enabled: {IDLE_TIMEOUT}s — will revert to PC mode after inactivity')
        threading.Thread(target=_idle_watchdog, daemon=True).start()
    else:
        log.info('Idle timeout disabled')

    threading.Thread(target=_start_sleep_watcher, daemon=True).start()

    run_tray()