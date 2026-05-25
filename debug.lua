local base_url = 'http://127.0.0.1:8765/tv/' --settings.server_url
local http = require('socket.http')

local function call(path)
    http.request(base_url .. path)
end

call('volume-up')

-- actions.vol_up = function()
    -- call('volume-up')
-- end
-- actions.vol_down = function()
    -- call('volume-down')
-- end
-- actions.toggle_mute = function()
    -- call('toggle-mute')
-- end
-- actions.toggle_screen = function()
    -- call('toggle-screen')
-- end
-- actions.toggle_screensaver = function()
    -- call('toggle-screensaver')
-- end

-- actions.nav_up = function()
    -- call('button/UP')
-- end
-- actions.nav_down = function()
    -- call('button/DOWN')
-- end
-- actions.nav_left = function()
    -- call('button/LEFT')
-- end
-- actions.nav_right = function()
    -- call('button/RIGHT')
-- end
-- actions.nav_ok = function()
    -- call('button/ENTER')
-- end
-- actions.nav_back = function()
    -- call('button/BACK')
-- end
-- actions.nav_home = function()
    -- call('button/HOME')
-- end

-- actions.input_hdmi1 = function()
    -- call('input/HDMI_1')
-- end
-- actions.input_hdmi2 = function()
    -- call('input/HDMI_2')
-- end
-- actions.input_hdmi3 = function()
    -- call('input/HDMI_3')
-- end
-- actions.input_hdmi4 = function()
    -- call('input/HDMI_4')
-- end

-- actions.launch_youtube = function()
    -- call('launch-app/youtube.leanback.v4')
-- end
-- actions.launch_spotify = function()
    -- call('launch-app/spotify-beehive')
-- end
-- actions.launch_netflix = function()
    -- call('launch-app/netflix')
-- end
-- actions.launch_disney_plus = function()
    -- call('launch-app/com.disney.disneyplus-prod')
-- end
-- actions.launch_hulu = function()
    -- call('launch-app/hulu')
-- end
-- actions.launch_prime = function()
    -- call('launch-app/amazon')
-- end
-- actions.launch_tubi = function()
    -- call('launch-app/tubi')
-- end
-- actions.launch_sling_tv = function()
    -- call('launch-app/com.movenetworks.app.sling-tv-sling-production')
-- end
-- actions.launch_apple_tv = function()
    -- call('launch-app/com.apple.appletv')
-- end
-- actions.launch_hbo_max = function()
    -- call('launch-app/com.hbo.hbomax')
-- end
-- actions.launch_peacock = function()
    -- call('launch-app/com.peacock.tv')
-- end
-- actions.launch_paramount_plus = function()
    -- call('launch-app/com.cbs-all-access.webapp.prod')
-- end
-- actions.launch_youtube_tv = function()
    -- call('launch-app/youtube.leanback.ytv.v1')
-- end
