import asyncio
import threading
import subprocess
import logging
import winreg
import ctypes
import yaml
import os
from flask import Flask, jsonify
from bscpylgtv import WebOsClient
from PIL import Image, ImageDraw
import pystray

with open('config.yaml') as f:
    cfg = yaml.safe_load(f)

TV_IP               = cfg['tv']['ip']
TV_DEFAULT_INPUT    = cfg['tv']['default_input']
TV_PC_INPUT         = cfg['tv']['pc_input']
TV_AUDIO_SOURCE     = cfg['tv']['audio_source']
TV_RESOLUTION_SCALE = cfg['tv']['resolution_scale']

PC_MONITOR_INDEX    = cfg['pc']['monitor_index']
PC_AUDIO_SOURCE     = cfg['pc']['audio_source']
PC_RESOLUTION_SCALE = cfg['pc']['resolution_scale']

COMMAND_TIMEOUT = cfg['connection']['command_timeout']
RECONNECT_DELAY = cfg['connection']['reconnect_delay']
PING_INTERVAL   = cfg['connection']['ping_interval']
PORT            = cfg['server']['port']

INPUT_MAP = {
    'HDMI_1': 'com.webos.app.hdmi1',
    'HDMI_2': 'com.webos.app.hdmi2',
    'HDMI_3': 'com.webos.app.hdmi3',
    'HDMI_4': 'com.webos.app.hdmi4'
}

logging.basicConfig(level=logging.INFO)
log = logging.getLogger('tv')

app = Flask(__name__)

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
                self._connected    = True
                self._reconnecting = False
                log.info('Connected')
                return
            except Exception as e:
                log.warning(f'Connection failed: {e} — retrying in {RECONNECT_DELAY}s')
                await asyncio.sleep(RECONNECT_DELAY)

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
    async def toggle(c):
        curr_input = await c.get_input()
        mapped_input = INPUT_MAP.get(TV_PC_INPUT)
        power_state = c.power_state['state']

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
        # PC is active, switch back
        else:
            if (power_state != 'Screen Off'):
                print('Turning TV screen off...')
                await c.turn_screen_off()
            switch_audio(PC_AUDIO_SOURCE)
            set_scale(PC_RESOLUTION_SCALE)
    return respond(*tv.run(toggle))

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
        """Pulse icon color to reflect connection state."""
        import time
        while True:
            icon.icon  = current_icon()
            icon.title = "LG TV Remote — " + current_status_label(None)
            time.sleep(3)

    icon = pystray.Icon(
        name  = "LG TV Remote",
        icon  = ICON_YELLOW,
        title = "LG TV Remote",
        menu  = pystray.Menu(
            pystray.MenuItem(current_status_label, action=None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", quit_app),
        )
    )

    threading.Thread(target=refresh, args=(icon,), daemon=True).start()
    icon.run()  # blocks — must be main thr ad

# entry
if __name__ == '__main__':
    flask_thread = threading.Thread(
        target=lambda: app.run(port=PORT, use_reloader=False),
        daemon=True
    )
    flask_thread.start()
    run_tray()