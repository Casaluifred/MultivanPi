import asyncio
from bleak import BleakScanner
async def run():
    devices = await BleakScanner.discover(timeout=10.0)
    for d in devices: print(f"{d.address} | {d.name} | {d.rssi} dBm")
if __name__ == "__main__": asyncio.run(run())
