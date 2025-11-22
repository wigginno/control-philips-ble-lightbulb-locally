from typing import Optional
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi_utils.tasks import repeat_every
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
_brightness = 130
_temp = 130
_new_is_on = _is_on
_new_brightness = _brightness
_new_temp = _temp
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
    global _is_on, _brightness, _temp, _new_is_on, _new_brightness, _new_temp

    # Startup
    # Connect to the bulb
    c = await get_client()

    if c is not None:
        try:
            # Read current state from bulb
            light_state = await c.read_gatt_char(LIGHT_UUID)
            brightness_state = await c.read_gatt_char(BRIGHTNESS_UUID)
            temp_state = await c.read_gatt_char(TEMPERATURE_UUID)

            # Debug: Log raw byte values
            logger.info(f"Raw values - Light: {light_state.hex()}, Brightness: {brightness_state.hex()}, Temp: {temp_state.hex()}")

            # Parse the values (0x01 = on, 0x00 = off when reading from bulb)
            # Note: Write logic is inverted (we write 0x00 to turn on, 0x01 to turn off)
            _is_on = light_state[0] == 0x01
            _brightness = brightness_state[0]
            _temp = temp_state[0]

            # Initialize the new values (used for periodic updates) to match current state
            _new_is_on = _is_on
            _new_brightness = _brightness
            _new_temp = _temp

            logger.info(f"Initial bulb state - On: {_is_on}, Brightness: {_brightness}, Temp: {_temp}")
        except Exception as e:
            logger.error(f"Failed to read initial bulb state: {e}")
            logger.info("Using default values: On=True, Brightness=130, Temp=130")

    # Start repeated task to update on/off/brightness/temp every 0.25s
    await update_bulb()
    yield
    # Shutdown: Disconnect from bulb
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
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.2s;
        }
        button.on {
            background: #98c379;
            color: #282c34;
        }
        button.on:hover {
            background: #a8d389;
        }
        button.off {
            background: #3e4451;
            color: #abb2bf;
        }
        button.off:hover {
            background: #4b5263;
        }
        button:active {
            transform: scale(0.98);
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
    <button id="toggle-btn" onclick="toggle()">Loading...</button>

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
        let currentState = null;

        async function loadState() {
            try {
                const response = await fetch('/status');
                const data = await response.json();
                currentState = data.is_on;

                // Update button
                updateToggleButton(currentState);

                // Update sliders
                document.getElementById('brightness').value = data.brightness;
                document.getElementById('bri-val').textContent = data.brightness;
                lastBrightness = data.brightness;

                document.getElementById('temperature').value = data.temperature;
                document.getElementById('temp-val').textContent = data.temperature;
                lastTemperature = data.temperature;
            } catch (error) {
                console.error('Failed to load state:', error);
            }
        }

        function updateToggleButton(isOn) {
            const btn = document.getElementById('toggle-btn');
            btn.textContent = 'Toggle On/Off';
            btn.className = isOn ? 'on' : 'off';
        }

        async function toggle() {
            try {
                const response = await fetch('/toggle');
                const data = await response.json();
                currentState = data.state;
                updateToggleButton(currentState);
            } catch (error) {
                console.error('Failed to toggle:', error);
            }
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

        // Load initial state on page load
        loadState();
    </script>
</body>
</html>
    """


@repeat_every(seconds=0.25)
async def update_bulb():
    global _is_on, _brightness, _temp, _new_is_on, _new_brightness, _new_temp
    c = await get_client()
    if c is None:
        logger.error("Failed to establish client connection")
    elif _is_on != _new_is_on:
        signal = 0x01 if _new_is_on else 0x00
        await c.write_gatt_char(LIGHT_UUID, bytearray([signal]))
        logger.info(f"Toggled on/off state: {_is_on} -> {_new_is_on}")
        _is_on = _new_is_on
    elif _brightness != _new_brightness:
        await c.write_gatt_char(BRIGHTNESS_UUID, bytearray([_new_brightness]))
        logger.info(f"Brightness {_brightness} -> {_new_brightness}")
        _brightness = _new_brightness
    elif _temp != _new_temp:
        await c.write_gatt_char(TEMPERATURE_UUID, bytearray([_new_temp, 0x01]))
        logger.info(f"Changed temperature from {_temp} to {_new_temp}")
        _temp = _new_temp


@app.get("/status")
async def status():
    return {
        "is_on": _new_is_on,
        "brightness": _new_brightness,
        "temperature": _new_temp,
    }


@app.get("/toggle")
async def toggle():
    global _new_is_on
    _new_is_on = not _new_is_on
    return {"state": _new_is_on}


@app.get("/brightness")
async def brightness(value: int):
    global _new_brightness
    _new_brightness = value
    return {"brightness": _new_brightness}


@app.get("/temperature")
async def temperature(value: int):
    global _new_temp
    _new_temp = value
    return {"temperature": _new_temp}
