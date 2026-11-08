from machine import Pin, PWM, SoftI2C
from time import sleep, ticks_ms, ticks_diff
import onewire
import ds18x20
import dht
import ssd1306
import struct
import math
import json
import gc
import network

from wifi_config import WIFI_SSID, WIFI_PASSWORD, BACKEND_URL, DEVICE_TOKEN
from telemetry_upload import send_report


# ==========================================
# UN1C0RN^2 - INFRASTRUCTURE MONITORING SYSTEM
# Raspberry Pi Pico 2 W
# ==========================================

DEVICE_ID = "SENTINEL-01"


# ==========================================
# CONFIGURABLE THRESHOLDS
# ==========================================

# Temperature (Fahrenheit)
TEMP_WARNING = 74.0
TEMP_CRITICAL = 76.0

# Vibration (g)
VIBRATION_WARNING = 0.20
VIBRATION_CRITICAL = 0.50

# Update intervals (milliseconds)
TEMP_INTERVAL_MS = 3000
HUMIDITY_INTERVAL_MS = 3000
DISPLAY_INTERVAL_MS = 1000
REPORT_INTERVAL_MS = 3000

# These are demonstration thresholds.


# ==========================================
# WIFI CONNECTION
# ==========================================

wifi = network.WLAN(network.STA_IF)
wifi.active(True)


def connect_wifi():

    if wifi.isconnected():
        print("Wi-Fi already connected!")
        print("IP Address:", wifi.ifconfig()[0])
        return True

    print("Connecting UN1C0RN^2 to Wi-Fi...")

    try:
        wifi.connect(WIFI_SSID, WIFI_PASSWORD)

        for attempt in range(15):

            if wifi.isconnected():
                print("UN1C0RN^2 WIFI CONNECTED!")
                print("IP Address:", wifi.ifconfig()[0])
                return True

            sleep(1)

    except Exception as e:
        print("Wi-Fi error:", e)

    print("Wi-Fi connection failed!")
    return False


# ==========================================
# GPIO CONFIGURATION
# ==========================================

# Status LEDs
green_led = Pin(0, Pin.OUT)
yellow_led = Pin(1, Pin.OUT)
red_led = Pin(2, Pin.OUT)

green_led.off()
yellow_led.off()
red_led.off()

# PWM cooling fan
fan = PWM(Pin(17))
fan.freq(1000)
fan.duty_u16(0)

fan_active = False
fan_speed = 0

# Buzzer
buzzer = PWM(Pin(14))
buzzer.freq(2000)
buzzer.duty_u16(0)


# ==========================================
# TEMPERATURE SENSOR - DS18B20
# ==========================================

temp_sensor = ds18x20.DS18X20(
    onewire.OneWire(Pin(15))
)

temp_devices = temp_sensor.scan()
temperature_f = None

if temp_devices:
    print("DS18B20 connected")
else:
    print("WARNING: DS18B20 not detected")


# ==========================================
# HUMIDITY SENSOR - DHT11
# ==========================================

humidity_sensor = dht.DHT11(Pin(16))
humidity = None

print("DHT11 initialized")


# ==========================================
# I2C BUS
# ==========================================

i2c = SoftI2C(
    sda=Pin(4),
    scl=Pin(5),
    freq=10000
)

try:
    addresses = i2c.scan()
    print("I2C devices:", [hex(a) for a in addresses])

except Exception as e:
    print("I2C scan error:", e)


# ==========================================
# OLED DISPLAY
# ==========================================

oled = None

try:
    oled = ssd1306.SSD1306_I2C(
        128,
        64,
        i2c,
        addr=0x3C
    )

    oled.fill(0)
    oled.text("UN1C0RN^2", 32, 10)
    oled.text("Starting...", 20, 30)
    oled.show()

    print("OLED connected")

except Exception as e:
    print("OLED initialization error:", e)


# ==========================================
# MPU6500 VIBRATION SENSOR
# ==========================================

MPU_ADDR = 0x68
mpu_ready = False

try:
    # Wake sensor
    i2c.writeto_mem(MPU_ADDR, 0x6B, b'\x00')

    # Set accelerometer range to +/-2g
    i2c.writeto_mem(MPU_ADDR, 0x1C, b'\x00')

    sleep(0.1)

    who_am_i = i2c.readfrom_mem(
        MPU_ADDR,
        0x75,
        1
    )[0]

    print("MPU WHO_AM_I:", hex(who_am_i))

    if who_am_i == 0x70:
        mpu_ready = True
        print("MPU6500 connected")
    else:
        print("Unexpected MPU device ID")

except Exception as e:
    print("MPU6500 initialization error:", e)


# ==========================================
# SENSOR STATE
# ==========================================

vibration_g = None
previous_magnitude = None
vibration_peak = 0.0

last_temp_read = ticks_ms() - TEMP_INTERVAL_MS
last_humidity_read = ticks_ms() - HUMIDITY_INTERVAL_MS
last_display = ticks_ms() - DISPLAY_INTERVAL_MS
last_report = ticks_ms() - REPORT_INTERVAL_MS

last_buzzer_beep = ticks_ms() - 2000

system_status = "STARTING"


# ==========================================
# READ TEMPERATURE
# ==========================================

def read_temperature():

    global temp_devices

    if not temp_devices:
        temp_devices = temp_sensor.scan()

        if not temp_devices:
            return None

    try:
        temp_sensor.convert_temp()
        sleep(0.8)

        temp_c = temp_sensor.read_temp(
            temp_devices[0]
        )

        if temp_c is None or temp_c == 85:
            return None

        if temp_c < -55 or temp_c > 125:
            return None

        return (temp_c * 9 / 5) + 32

    except Exception as e:
        print("Temperature error:", e)
        return None


# ==========================================
# READ HUMIDITY
# ==========================================

def read_humidity():

    try:
        humidity_sensor.measure()

        value = humidity_sensor.humidity()

        if value < 0 or value > 100:
            return None

        return value

    except Exception as e:
        print("Humidity error:", e)
        return None


# ==========================================
# READ VIBRATION
# ==========================================

def read_vibration():

    global previous_magnitude

    if not mpu_ready:
        return None

    try:
        data = i2c.readfrom_mem(
            MPU_ADDR,
            0x3B,
            6
        )

        x, y, z = struct.unpack(">hhh", data)

        x = x / 16384.0
        y = y / 16384.0
        z = z / 16384.0

        magnitude = math.sqrt(
            x*x + y*y + z*z
        )

        if previous_magnitude is None:
            previous_magnitude = magnitude
            return 0.0

        change = abs(
            magnitude - previous_magnitude
        )

        previous_magnitude = magnitude

        return change

    except Exception as e:
        print("Vibration error:", e)
        return None


# ==========================================
# CLASSIFY SYSTEM STATUS
# Temperature and vibration ONLY
# ==========================================

def classify_status(temp, vib):

    # Humidity does not affect system status

    if temp is None or vib is None:
        return "SENSOR ERROR"

    # Critical conditions
    if temp >= TEMP_CRITICAL:
        return "CRITICAL"

    if vib >= VIBRATION_CRITICAL:
        return "CRITICAL"

    # Warning conditions
    if temp >= TEMP_WARNING:
        return "WARNING"

    if vib >= VIBRATION_WARNING:
        return "WARNING"

    return "NORMAL"


# ==========================================
# IDENTIFY EXACT ALERT CAUSES
# ==========================================

def get_alert_reasons(temp, vib):

    reasons = []

    # Temperature
    if temp is None:
        reasons.append("Temperature sensor error")

    elif temp >= TEMP_CRITICAL:
        reasons.append(
            "Temperature CRITICAL: {:.1f} F".format(temp)
        )

    elif temp >= TEMP_WARNING:
        reasons.append(
            "Temperature WARNING: {:.1f} F".format(temp)
        )

    # Vibration
    if vib is None:
        reasons.append("Vibration sensor error")

    elif vib >= VIBRATION_CRITICAL:
        reasons.append(
            "Vibration CRITICAL: {:.3f}g".format(vib)
        )

    elif vib >= VIBRATION_WARNING:
        reasons.append(
            "Vibration WARNING: {:.3f}g".format(vib)
        )

    return reasons


# ==========================================
# STATUS LED CONTROL
# ==========================================

def update_leds(status):

    green_led.off()
    yellow_led.off()
    red_led.off()

    if status == "NORMAL":
        green_led.on()

    elif status == "WARNING":
        yellow_led.on()

    elif status == "CRITICAL":
        red_led.on()

    elif status == "SENSOR ERROR":
        yellow_led.on()


# ==========================================
# AUTOMATIC FAN CONTROL
# Temperature ONLY
# ==========================================

def update_fan(temp):

    global fan_active, fan_speed

    if temp is None:
        # Fail-safe cooling if temperature is unavailable
        fan_speed = 100

    elif temp >= TEMP_CRITICAL:
        fan_speed = 100

    elif temp >= TEMP_WARNING:
        fan_speed = 60

    else:
        fan_speed = 0

    duty = int(fan_speed * 65535 / 100)

    fan.duty_u16(duty)

    fan_active = fan_speed > 0


# ==========================================
# BUZZER CONTROL
# ==========================================

def update_buzzer(status, now):

    global last_buzzer_beep

    if status in ("CRITICAL", "SENSOR ERROR"):

        if ticks_diff(
            now,
            last_buzzer_beep
        ) >= 2000:

            buzzer.duty_u16(32768)
            sleep(0.15)
            buzzer.duty_u16(0)

            last_buzzer_beep = ticks_ms()

    else:
        buzzer.duty_u16(0)


# ==========================================
# OLED DISPLAY
# ==========================================

def update_display(temp, hum, vib, status):

    if oled is None:
        return

    try:
        oled.fill(0)

        oled.text("UN1C0RN^2", 32, 0)
        oled.hline(0, 11, 128, 1)

        if temp is None:
            temp_text = "TEMP: ERROR"
        else:
            temp_text = "TEMP: {:.1f} F".format(temp)

        if hum is None:
            hum_text = "HUM: ERROR"
        else:
            hum_text = "HUM: {}%".format(hum)

        if vib is None:
            vib_text = "VIB: ERROR"
        else:
            vib_text = "VIB: {:.2f}g".format(vib)

        oled.text(temp_text, 0, 15)
        oled.text(hum_text, 0, 25)
        oled.text(vib_text, 0, 35)

        if status == "SENSOR ERROR":
            status_text = "ERROR"
        else:
            status_text = status

        oled.text(
            "STATUS:" + status_text,
            0,
            45
        )

        oled.text(
            "FAN:" + str(fan_speed) + "%",
            0,
            55
        )

        oled.show()

    except Exception as e:
        print("OLED error:", e)


# ==========================================
# JSON DATA FOR DASHBOARD
# ==========================================

def generate_payload(temp, hum, vib, status):

    payload = {
        "device_id": DEVICE_ID,

        "temperature_f": (
            round(temp, 2)
            if temp is not None else None
        ),

        "humidity_percent": hum,

        "vibration_g": (
            round(vib, 3)
            if vib is not None else None
        ),

        "status": status,

        "fan_active": fan_active,
        "fan_speed_percent": fan_speed,

        "alert_reasons": get_alert_reasons(
            temp, vib
        )
    }

    return payload


# ==========================================
# START WIFI
# ==========================================

connect_wifi()


# ==========================================
# MAIN UN1C0RN^2 SYSTEM
# ==========================================

print("")
print("================================")
print("UN1C0RN^2 SYSTEM ONLINE")
print("================================")
print("Device:", DEVICE_ID)
print("Monitoring temperature, humidity")
print("and vibration")
print("")

try:

    while True:

        now = ticks_ms()

        # ----------------------------------
        # TEMPERATURE
        # ----------------------------------

        if ticks_diff(
            now,
            last_temp_read
        ) >= TEMP_INTERVAL_MS:

            temperature_f = read_temperature()
            last_temp_read = ticks_ms()

        # ----------------------------------
        # HUMIDITY
        # ----------------------------------

        if ticks_diff(
            now,
            last_humidity_read
        ) >= HUMIDITY_INTERVAL_MS:

            humidity = read_humidity()
            last_humidity_read = ticks_ms()

        # ----------------------------------
        # VIBRATION
        # ----------------------------------

        current_vibration = read_vibration()

        if current_vibration is not None:

            vibration_g = current_vibration

            if current_vibration > vibration_peak:
                vibration_peak = current_vibration

        else:
            vibration_g = None

        # ----------------------------------
        # SYSTEM STATUS
        # ----------------------------------

        effective_vibration = (
            vibration_peak
            if vibration_g is not None
            else None
        )

        system_status = classify_status(
            temperature_f,
            effective_vibration
        )

        # ----------------------------------
        # HARDWARE OUTPUTS
        # ----------------------------------

        # Fan responds ONLY to temperature
        update_fan(temperature_f)

        # LEDs and buzzer respond to temperature
        # and vibration, NOT humidity
        update_leds(system_status)

        update_buzzer(
            system_status,
            ticks_ms()
        )

        # ----------------------------------
        # OLED
        # ----------------------------------

        now = ticks_ms()

        if ticks_diff(
            now,
            last_display
        ) >= DISPLAY_INTERVAL_MS:

            update_display(
                temperature_f,
                humidity,
                effective_vibration,
                system_status
            )

            last_display = now

        # ----------------------------------
        # SERIAL / JSON REPORT
        # ----------------------------------

        if ticks_diff(
            now,
            last_report
        ) >= REPORT_INTERVAL_MS:

            payload = generate_payload(
                temperature_f,
                humidity,
                effective_vibration,
                system_status
            )

            print("----------------------------")
            print("UN1C0RN^2 LIVE DATA")

            print(json.dumps(payload))

            # Record the full native report in the backend over Wi-Fi.
            send_report(wifi, payload, BACKEND_URL, DEVICE_TOKEN,
                        WIFI_SSID, WIFI_PASSWORD)

            print(
                "Temperature:",
                temperature_f,
                "F"
            )

            print(
                "Humidity:",
                humidity,
                "%"
            )

            print(
                "Vibration peak:",
                effective_vibration,
                "g"
            )

            print("Status:", system_status)

            print(
                "Fan:",
                "ON" if fan_active else "OFF"
            )

            print("Fan Speed:", fan_speed, "%")

            # Exact alert causes
            alert_reasons = get_alert_reasons(
                temperature_f,
                effective_vibration
            )

            if alert_reasons:

                print("")
                print("ALERT CAUSES:")

                for reason in alert_reasons:
                    print(" -", reason)

            else:
                print(
                    "ALERT CAUSES: None - All monitored conditions normal"
                )

            # Reset vibration peak after reporting
            vibration_peak = 0.0

            last_report = now

            gc.collect()

        sleep(0.05)


except KeyboardInterrupt:

    print("UN1C0RN^2 STOPPED")


finally:

    fan.duty_u16(0)
    fan.deinit()

    green_led.off()
    yellow_led.off()
    red_led.off()

    buzzer.duty_u16(0)
    buzzer.deinit()

    print("Hardware outputs disabled")
