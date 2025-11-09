from typing import Optional
import logging
from random import choices
from string import ascii_letters
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from bleak import BleakClient, BleakScanner

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

DEVICE_NAME = "Hue ambiance lamp"
LIGHT_UUID = "932c32bd-0002-47a2-835a-a8d455b859dd"
BRIGHTNESS_UUID = "932c32bd-0003-47a2-835a-a8d455b859dd"
TEMPERATURE_UUID = "932c32bd-0004-47a2-835a-a8d455b859dd"

_is_on = True
_brightness = 0
_temp = 0
client: Optional[BleakClient] = None


async def get_client():
    global client
    if client is None or not client.is_connected:
        devices = await BleakScanner.discover()
        device = next((d for d in devices if d.name == DEVICE_NAME), None)
        if device:
            client = BleakClient(device, timeout=10)
            await client.connect()
    return client


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup: Connect once on startup
    await get_client()
    yield
    # Shutdown: Disconnect if connected
    if client and client.is_connected:
        await client.disconnect()


app = FastAPI(lifespan=lifespan)


@app.get("/favicon.svg")
async def favicon():
    from fastapi.responses import Response

    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
<circle cx="50" cy="50" r="48" fill="#ffd700"/>
<path d="M50 20 C35 20 25 30 25 45 C25 55 30 62 35 68 L35 75 C35 78 37 80 40 80 L60 80 C63 80 65 78 65 75 L65 68 C70 62 75 55 75 45 C75 30 65 20 50 20 Z" fill="#fff"/>
<rect x="42" y="78" width="16" height="4" fill="#e0e0e0" rx="1"/>
<circle cx="50" cy="50" r="8" fill="#ffd700"/>
</svg>"""
    return Response(content=svg, media_type="image/svg+xml")


@app.get("/favicon.ico")
async def favicon_ico():
    from fastapi.responses import Response
    import base64

    # Simple PNG light bulb icon (32x32, base64 encoded)
    png_data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAAXNSR0IArs4c6QAAAjRJREFU"
        "WEftlk1IVFEUx3/3vTfOjDpqZqKkRBkRFLVo0aKgRS1atCmSIKJFixZ9QNSiRYGbWkSbIIii"
        "RYQRRVAURbXoAxoqK6w+TNMxZ+bN+7jn3TczbzJn3vONKbqLYbjn3N/5n3Pu5T4hNvmTTY5H"
        "FgHbHWA7AxbBxnZggwxwzu0AepVS/Y2u3SgB3y0GxoA9xpirxphrwBFgDDjcKIkGGXgOXAAu"
        "Aa+MMf3Ap5znXL0k6ibgnLsEnDXGnAA+A4+BM8aYPuAL0FsviboIOOd6gNPGmB7gI/AQOGaM"
        "6QU+AD31kqhZwDl3ADhljDkOfADuA0eNMT3Ae+BEPSRqFnDOdQNHjTFdwDvgLtBtjOkB3gJH"
        "6yFRk4BzbifQZYzZC7wB7gA7jDHdwGvgWK0kaiFwCOgyxhwAXgG3gf3GmC7gJXC8FhK1CNgD"
        "dBpj9gMvgFvAPmNMJ/AcOFELidUEbMe/ZYzZC4wCt4C9xpgO4CnQWwuJ1QSccy3AEWPMHmAE"
        "uAnsNsZ0AE+Ak6uRWEnAAh3GmN3ACHAd2GWMaQceAX21kFhJwLYDHcaYXcBzYBjYaYxpBx4A"
        "p1YjsZyABdqMMTuAYeA6sN0Y0wbcB06vRmI5AdtuG2O2Ac+Aa8A2Y0wrcA84txqJpQRs+xBw"
        "0BizFXgKXAW2GGNagbvAQC0klhLI/wX0G2O2AE+AIWCzMaYFGATO10JiKYH8X0C/MaYJeAwM"
        "AZuMMc3AEDC4Gol/CcwCA8aYJmAQGAQ2GmOagUFgoBYS/xL4DgyYfwH/APQykR83Ie4fAAAA"
        "AElFTkSuQmCC"
    )
    return Response(content=png_data, media_type="image/x-icon")


@app.get("/", response_class=HTMLResponse)
async def index():
    return """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="icon" type="image/x-icon" href="/favicon.ico">
    <link rel="icon" type="image/svg+xml" href="/favicon.svg">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            max-width: 400px;
            margin: 0 auto;
            padding: 40px 20px;
            background: #282c34;
            min-height: 100vh;
        }
        h1 {
            color: #abb2bf;
            text-align: center;
            margin-bottom: 30px;
            font-size: 28px;
        }
        button {
            width: 100%;
            padding: 15px;
            font-size: 18px;
            margin: 10px 0;
            background: #3e4451;
            color: #abb2bf;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 500;
            transition: background 0.2s;
        }
        button:hover {
            background: #4b5263;
        }
        button:active {
            background: #2c313c;
        }
        .slider-container {
            background: #2c313c;
            padding: 20px;
            border-radius: 8px;
            margin: 15px 0;
        }
        label {
            display: block;
            margin-bottom: 10px;
            font-weight: 500;
            color: #abb2bf;
        }
        input[type="range"] {
            width: 100%;
            height: 6px;
            -webkit-appearance: none;
            appearance: none;
            background: #4b5263;
            border-radius: 3px;
            outline: none;
        }
        input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            appearance: none;
            width: 20px;
            height: 20px;
            background: #abb2bf;
            border-radius: 50%;
            cursor: pointer;
        }
        input[type="range"]::-moz-range-thumb {
            width: 20px;
            height: 20px;
            background: #abb2bf;
            border-radius: 50%;
            cursor: pointer;
            border: none;
        }
    </style>
</head>
<body>    
    <button onclick="toggle()">Toggle On/Off</button>
    
    <div class="slider-container">
        <label>Brightness: <span id="bri-val">130</span></label>
        <input type="range" min="10" max="250" value="130" step="10" id="brightness"
               oninput="updateBrightness(this.value)">
    </div>

    <div class="slider-container">
        <label>Temp: <span id="temp-val">130</span></label>
        <input type="range" min="0" max="250" value="130" step="10" id="temperature"
               oninput="updateTemperature(this.value)">
    </div>

    <script>
        let lastBrightness = null;
        let lastTemperature = null;

        function toggle() {
            fetch('/toggle');
        }

        function updateBrightness(val) {
            document.getElementById('bri-val').textContent = val;
            const rounded = Math.round(val / 10) * 10;
            if (rounded !== lastBrightness) {
                lastBrightness = rounded;
                fetch('/brightness?value=' + rounded);
            }
        }

        function updateTemperature(val) {
            document.getElementById('temp-val').textContent = val;
            const rounded = Math.round(val / 10) * 10;
            if (rounded !== lastTemperature) {
                lastTemperature = rounded;
                fetch('/temperature?value=' + rounded);
            }
        }
    </script>
</body>
</html>
    """


@app.get("/toggle")
async def toggle():
    global _is_on
    x = "".join(choices(ascii_letters, k=4))
    logger.info(f"{x}: toggle()")
    c = await get_client()
    if c is None:
        logger.error(f"{x}: Failed to establish client connection.")
        return {"state": _is_on}
    await c.write_gatt_char(LIGHT_UUID, bytearray([0x00 if _is_on else 0x01]))
    _is_on = not _is_on
    return {"state": _is_on}


@app.get("/brightness")
async def brightness(value: int):
    global _brightness
    x = "".join(choices(ascii_letters, k=4))
    logger.info(f"{x}: brightness({value})")
    c = await get_client()
    if c is None:
        logger.error(
            f"{x}: brightness({value}): Failed to establish client connection."
        )
        return {"brightness": _brightness}
    logger.info(f"brightness({value}): established client connection")
    await c.write_gatt_char(BRIGHTNESS_UUID, bytearray([value]))
    logger.info(f"{x}: Brightness: {_brightness} -> {value}")
    _brightness = value
    return {"brightness": _brightness}


@app.get("/temperature")
async def temperature(value: int):
    global _temp
    x = "".join(choices(ascii_letters, k=4))
    logger.info(f"{x}: temperature({value})")
    c = await get_client()
    if c is None:
        logger.error(
            f"{x}: temperature({value}): Failed to establish client connection."
        )
        return {"temperature": _temp}
    logger.info(f"{x}: temperature({value}): established client connection")
    await c.write_gatt_char(TEMPERATURE_UUID, bytearray([value, 0x01]))
    logger.info(f"{x}: Temperature: {_temp} -> {value}")
    _temp = value
    return {"temperature": _temp}
