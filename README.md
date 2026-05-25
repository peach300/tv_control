# LG TV Remote
A small LG WebOS TV control project using [bscpylgtv](https://github.com/chros73/bscpylgtv/) with a Flask API server and a custom Unified Remote.

## Features

- Connects to an LG WebOS TV over the network.
- Exposes a local HTTP API for TV commands.
- Supports:
  - power/screen toggle
  - screensaver toggle
  - volume up/down
  - mute toggle
  - input selection
  - generic button presses
  - app launching

## Setup

Update the TV IP address, connection parameters, and server port in config.yaml

## Unified Remote

The `unified_remote/` folder contains a custom remote for [Unified Remote](https://www.unifiedremote.com/). 

Copy these files into a new directory in `%PROGRAMDATA%\Unified Remote\Remotes\Custom\LG TV`, then restart your Unified Remote server.

Requires luasocket module
`luarocks install luasocket`

Icon from
<a href="https://www.flaticon.com/free-icons/remote-control" title="remote control icons">Remote control icons created by Freepik - Flaticon</a>

## License

MIT
