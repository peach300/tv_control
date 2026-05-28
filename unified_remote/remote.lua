local base_url = settings.server_url
local http = require("http")

local function call(path)
    http.get(base_url .. path)
end

actions.vol_up = function()
    call("tv/volume-up")
end
actions.vol_down = function()
    call("tv/volume-down")
end
actions.toggle_mute = function()
    call("tv/toggle-mute")
end
actions.toggle_screen = function()
    call("tv/toggle-screen")
end
actions.toggle_screensaver = function()
    call("tv/toggle-screensaver")
end

actions.media_play = function()
    call("tv/button/PLAY")
end
actions.media_pause = function()
    call("tv/button/PAUSE")
end
actions.media_rewind = function()
    call("tv/button/REWIND")
end
actions.media_fast_forward = function()
    call("tv/button/FAST_FORWARD")
end

actions.nav_up = function()
    call("tv/button/UP")
end
actions.nav_down = function()
    call("tv/button/DOWN")
end
actions.nav_left = function()
    call("tv/button/LEFT")
end
actions.nav_right = function()
    call("tv/button/RIGHT")
end
actions.nav_ok = function()
    call("tv/button/ENTER")
end
actions.nav_back = function()
    call("tv/button/BACK")
end
actions.nav_home = function()
    call("tv/button/HOME")
end
actions.nav_settings = function()
    call("tv/button/ADVANCE_SETTING")
end

actions.input_hdmi1 = function()
    call("tv/input/HDMI_1")
end
actions.input_hdmi2 = function()
    call("tv/input/HDMI_2")
end
actions.input_hdmi3 = function()
    call("tv/input/HDMI_3")
end
actions.input_hdmi4 = function()
    call("tv/input/HDMI_4")
end

actions.audio_tv = function()
    call("audio/set-device/TV")
end
actions.audio_speakers = function()
    call("audio/set-device/Speakers")
end

actions.quick_toggle = function()
    call("tv/quick-toggle")
end

actions.display_scale_tv = function()
    call("display/set-scale/200")
end
actions.display_scale_pc = function()
    call("display/set-scale/100")
end

actions.numpad_0 = function()
    call("tv/button/0")
end
actions.numpad_1 = function()
    call("tv/button/1")
end
actions.numpad_2 = function()
    call("tv/button/2")
end
actions.numpad_3 = function()
    call("tv/button/3")
end
actions.numpad_4 = function()
    call("tv/button/4")
end
actions.numpad_5 = function()
    call("tv/button/5")
end
actions.numpad_6 = function()
    call("tv/button/6")
end
actions.numpad_7 = function()
    call("tv/button/7")
end
actions.numpad_8 = function()
    call("tv/button/8")
end
actions.numpad_9 = function()
    call("tv/button/9")
end

actions.launch_youtube = function()
    call("tv/launch-app/youtube.leanback.v4")
end
actions.launch_spotify = function()
    call("tv/launch-app/spotify-beehive")
end
actions.launch_netflix = function()
    call("tv/launch-app/netflix")
end
actions.launch_disney_plus = function()
    call("tv/launch-app/com.disney.disneyplus-prod")
end
actions.launch_hulu = function()
    call("tv/launch-app/hulu")
end
actions.launch_prime = function()
    call("tv/launch-app/amazon")
end
actions.launch_tubi = function()
    call("tv/launch-app/tubi")
end
actions.launch_sling_tv = function()
    call("tv/launch-app/com.movenetworks.app.sling-tv-sling-production")
end
actions.launch_apple_tv = function()
    call("tv/launch-app/com.apple.appletv")
end
actions.launch_hbo_max = function()
    call("tv/launch-app/com.hbo.hbomax")
end
actions.launch_peacock = function()
    call("tv/launch-app/com.peacock.tv")
end
actions.launch_paramount_plus = function()
    call("tv/launch-app/com.cbs-all-access.webapp.prod")
end
actions.launch_youtube_tv = function()
    call("tv/launch-app/youtube.leanback.ytv.v1")
end
