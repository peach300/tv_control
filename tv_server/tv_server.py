import asyncio
from bscpylgtv import WebOsClient

TV_IP = "192.168.1.2"
TV_INPUT = "HDMI_3"

async def switch_to_pc():
    client = await WebOsClient.create(TV_IP, ping_interval=None)
    await client.connect()
    await client.set_input(TV_INPUT)
    await client.disconnect()

asyncio.run(switch_to_pc())