local base = "http://127.0.0.1:8765/tv/"

local function call(path)
  http.request(base .. path)
end

actions.vol_up      = function() call("volume-up")      end
actions.vol_down    = function() call("volume-down")    end
actions.mute        = function() call("mute")           end
actions.nav_up      = function() call("button/UP")      end
actions.nav_down    = function() call("button/DOWN")    end
actions.nav_left    = function() call("button/LEFT")    end
actions.nav_right   = function() call("button/RIGHT")   end
actions.nav_ok      = function() call("button/ENTER")   end
actions.nav_back    = function() call("button/BACK")    end
actions.nav_home    = function() call("button/HOME")    end
actions.input_hdmi1 = function() call("input/HDMI_1")   end
actions.input_hdmi2 = function() call("input/HDMI_2")   end
actions.standby     = function() call("standby")        end