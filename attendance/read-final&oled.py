#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# －－－－湖南创乐博智能科技有限公司－－－－
#  文件名：35_RFID_read.py
#  版本：V2.0
#  author: zhulin
# 说明：RFID 读取数据
#####################################################
from time import sleep_ms
from machine import SoftI2C,Pin
from ssd1306 import SSD1306_I2C
from machine import Pin, SPI, SoftSPI
from mfrc522 import MFRC522
try:
    import network
except Exception:
    network = None 
try:
    import urequests as requests
except Exception:
    requests = None
try:
    from umqtt.simple import MQTTClient
except Exception:
    MQTTClient = None

# ===== Adafruit IO and Wi-Fi configuration =====
# Fill in your Wi-Fi and Adafruit IO credentials
WIFI_SSID = "checkname"
WIFI_PASSWORD = "rickroll"
AIO_USERNAME = "Lclin"
AIO_KEY = "aio_labx36im7CUNzjo7eMfoL7vFqzbW"
AIO_FEED_KEY = "attendance"  # your feed key, e.g. 'rfid-name'
AIO_MQTT_HOST = "io.adafruit.com"
AIO_MQTT_PORT = 1883  # use 1883 to avoid TLS overhead on constrained devices

i2c = SoftI2C(sda=Pin(13), scl=Pin(14))   #I2C初始化：sda--> 13, scl --> 14
oled = SSD1306_I2C(128, 64, i2c) #你的OLED分辨率，使用I2C
oled.fill(1) #清空屏幕

def _wifi_connect(max_wait_ms=15000):
    if network is None:
        return False
    try:
        wlan = network.WLAN(network.STA_IF)
        was_connected = False
        if not wlan.active():
            wlan.active(True)
        if not wlan.isconnected():
            if WIFI_SSID and WIFI_PASSWORD:
                wlan.connect(WIFI_SSID, WIFI_PASSWORD)
            waited = 0
            while not wlan.isconnected() and waited < max_wait_ms:
                sleep_ms(250)
                waited += 250
        if wlan.isconnected():
            try:
                ip = wlan.ifconfig()[0]
                print("Wi-Fi connected, IP:", ip)
            except Exception:
                pass
            # 連上 Wi-Fi 後，讓 Wi-Fi LED 亮 2 秒
            try:
                led_wifi.value(1)
                sleep_ms(2000)
                led_wifi.value(0)
                oled.show()
                oled.fill(0)
                oled.show()
                oled.text("Wi-Fi connected",0,9,1)
                oled.show()
                sleep_ms(5000)
                oled.fill(1)
                oled.show()
                oled.fill(0)
                oled.show()
                oled.text("Upload ing",0,9,1)
                oled.show()
                sleep_ms(5000)
                oled.fill(1)
            except Exception:
                pass
        return wlan.isconnected()
    except Exception as e:
        print("Wi-Fi connect error:", e)
        return False


def _aio_publish_rest(value):
    # Publishes value to Adafruit IO feed via REST API
    if requests is None:
        print("urequests not available")
        return False
    if not _wifi_connect():
        print("Wi-Fi not connected; REST publish aborted")
        oled.show()
        oled.fill(0)
        oled.show()
        oled.text("Wi-Fi no connect",0,9,1)
        oled.show()
        sleep_ms(5000)
        oled.fill(1)
        return False
    try:
        url_https = "https://io.adafruit.com/api/v2/%s/feeds/%s/data" % (AIO_USERNAME, AIO_FEED_KEY)
        headers = {"X-AIO-Key": AIO_KEY, "Content-Type": "application/json"}
        payload = '{"value":"%s"}' % (str(value).replace('"', '\\"'))
        resp = requests.post(url_https, data=payload, headers=headers)
        try:
            status_code = resp.status_code
        except Exception:
            status_code = 200
        try:
            resp.close()
        except Exception:
            pass
        ok = (200 <= status_code < 300)
        if not ok:
            print("Adafruit IO REST HTTPS failed, status:", status_code)
            oled.show()
            oled.fill(0)
            oled.show()
            oled.text("Upload failed",0,9,1)
            oled.show()
            sleep_ms(2000)
            oled.fill(1)
        else:
            print("Adafruit IO REST HTTPS OK:", status_code)
            return True
    except Exception as e:
        print("HTTPS publish exception:", e)
        # Fallback to HTTP if HTTPS fails
        try:
            url_http = "http://io.adafruit.com/api/v2/%s/feeds/%s/data" % (AIO_USERNAME, AIO_FEED_KEY)
            headers = {"X-AIO-Key": AIO_KEY, "Content-Type": "application/json"}
            payload = '{"value":"%s"}' % (str(value).replace('"', '\\"'))
            resp = requests.post(url_http, data=payload, headers=headers)
            try:
                status_code = resp.status_code
            except Exception:
                status_code = 200
            try:
                resp.close()
            except Exception:
                pass
            ok = (200 <= status_code < 300)
            if ok:
                print("Adafruit IO REST HTTP OK:", status_code)
                return True
            else:
                print("Adafruit IO REST HTTP failed, status:", status_code)
        except Exception as e2:
            print("HTTP publish exception:", e2)
    return False


def _aio_publish_mqtt(value):
    # Publishes value to Adafruit IO feed via MQTT
    if MQTTClient is None:
        print("MQTT client not available")
        return False
    if not _wifi_connect():
        print("Wi-Fi no connect; MQTT publish aborted")
        oled.text("Wi-Fi no connect",0,9,1)
        return False
    try:
        topic = b"%s/feeds/%s" % (AIO_USERNAME.encode(), AIO_FEED_KEY.encode())
        payload = str(value).encode()
        client_id = None
        try:
            import machine
            client_id = b"esp32-" + machine.unique_id()
        except Exception:
            client_id = b"esp32-client"
        c = MQTTClient(client_id=client_id,
                       server=AIO_MQTT_HOST,
                       port=AIO_MQTT_PORT,
                       user=AIO_USERNAME,
                       password=AIO_KEY,
                       keepalive=60)
        c.connect()
        c.publish(topic, payload, retain=False, qos=0)
        c.disconnect()
        print("Adafruit IO MQTT publish OK")
        return True
    except Exception as e:
        print("MQTT publish exception:", e)
        try:
            c.disconnect()
        except Exception:
            pass
        return False


def _aio_publish_resilient(value):
    # Try REST first, then MQTT
    if _aio_publish_rest(value):
        print("Adafruit IO publish succeeded via REST")
        return True
    if _aio_publish_mqtt(value):
        print("Adafruit IO publish succeeded via MQTT fallback")
        return True
    print("Adafruit IO publish failed; checking Wi-Fi status...")
    if network is not None:
        try:
            wlan = network.WLAN(network.STA_IF)
            print("Wi-Fi connected:", wlan.isconnected())
            if wlan.isconnected():
                try:
                    print("Wi-Fi IP address:", wlan.ifconfig()[0])
                except Exception:
                    pass
        except Exception as e:
            print("Unable to query Wi-Fi:", e)
    return False

# 可依實際接線修改
PIN_SCK = 18
PIN_MOSI = 23
PIN_MISO = 19
PIN_CS = 5  # MFRC522 SDA/SS 腳位
PIN_RST = None  # 若 RST 接到了某個 GPIO，填入該腳位號；若接 3.3V 則保持 None

# LED 指示腳位：檢測到卡片 → GPIO32；成功上傳 Adafruit → GPIO25；未授權卡片 → 紅色 LED
LED_DETECT_PIN = 27
LED_SENT_PIN = 4
LED_WIFI_PIN = 15
LED_REJECT_PIN = 2  # 可依實際接線指定紅色 LED 腳位，若無則設為 None
LED_ACCEPT_PIN = 25  # 綠色 LED，正確名字時點亮，若無則設為 None

# 優先使用硬體 SPI，失敗時改用 SoftSPI
USE_HARDWARE_SPI = False
SPI_ID = 2  # 在 ESP32 上 VSPI=2 對應 SCK=18 MOSI=23 MISO=19

# 將在程式中動態切換不同的波特率與模式以提升相容性
_spi_baudrates = [1000000, 400000, 100000]
_spi_ids = [2, 1]
_spi_use_hw = [True, False]
_cfg_index = 0

sck = Pin(PIN_SCK, Pin.OUT)
mosi = Pin(PIN_MOSI, Pin.OUT)
# 對 SoftSPI，MISO 應為輸入
miso = Pin(PIN_MISO, Pin.IN)
cs = Pin(PIN_CS, Pin.OUT)
cs.value(1)

if PIN_RST is not None:
    rst = Pin(PIN_RST, Pin.OUT)
    rst.value(1)
else:
    rst = None

# LED 腳位初始化並預設熄滅
led_detect = Pin(LED_DETECT_PIN, Pin.OUT)
led_sent = Pin(LED_SENT_PIN, Pin.OUT)
led_wifi = Pin(LED_WIFI_PIN, Pin.OUT)
led_detect.value(0)
led_sent.value(0)
led_wifi.value(0)
if LED_REJECT_PIN is not None:
    led_reject = Pin(LED_REJECT_PIN, Pin.OUT)
    led_reject.value(0)
else:
    led_reject = None
if LED_ACCEPT_PIN is not None:
    led_accept = Pin(LED_ACCEPT_PIN, Pin.OUT)
    led_accept.value(0)
else:
    led_accept = None

# 記錄上一次看到的卡片 UID（避免 LED1 持續常亮，僅在新卡出現時亮 2 秒）
last_seen_uid = None


def _make_spi(baud, use_hw, spi_id):
    if use_hw:
        try:
            return SPI(spi_id, baudrate=baud, polarity=0, phase=0, sck=sck, mosi=mosi, miso=miso)
        except Exception:
            pass
    return SoftSPI(baudrate=baud, polarity=0, phase=0, sck=sck, mosi=mosi, miso=miso)


def _pulse_reset():
    if rst is not None:
        rst.value(0)
        sleep_ms(5)
        rst.value(1)
        sleep_ms(5)


spi = _make_spi(_spi_baudrates[-1], USE_HARDWARE_SPI, SPI_ID)

# 可在此放入 9 個人的名字（與寫入卡片的字串相同，大小寫忽略，會自動處理填充）
PEOPLE = [
    "patrick",
    "Ryan",
    "Hayden",
     "Nathan",
     "Kenny",
    "Helios",
    "Queenie",
     "Rianna",
     "Bosco",
]


def _try_decode(data_bytes):
    try:
        return bytes(data_bytes).decode('utf-8', errors='ignore')
    except Exception:
        try:
            return bytes(data_bytes).decode('gbk', errors='ignore')
        except Exception:
            return ""


def _bytes_to_text(data_bytes):
    text = _try_decode(data_bytes)
    return text.replace('\x00', '').strip()


def _is_printable(ch):
    try:
        return ch.isprintable()
    except AttributeError:
        code = ord(ch)
        if 32 <= code <= 126:
            return True
        if ch in '\t\r\n':
            return True
        return False


def _normalize(text):
    # 僅保留可打印字元，去頭尾空白，轉小寫
    if not isinstance(text, str):
        try:
            text = str(text)
        except Exception:
            text = ""
    printable = ''.join(ch for ch in text if _is_printable(ch))
    return printable.strip().lower()


def _read_blocks(rdr, start_block, count):
    blocks = []
    for i in range(count):
        data = rdr.read(start_block + i)
        if data is None:
            return None
        blocks.extend(data)
    return blocks


def _to_hex(data_bytes):
    try:
        return ' '.join('%02X' % b for b in data_bytes)
    except Exception:
        return ''


def _read_version(rdr):
    try:
        ver = rdr._rreg(0x37)  # VersionReg
        return ver
    except Exception:
        return None


def _next_config():
    global _cfg_index
    _cfg_index = (_cfg_index + 1) % (len(_spi_baudrates) * len(_spi_ids) * len(_spi_use_hw))
    # 映射索引到 (use_hw, spi_id, baud)
    hw_idx = (_cfg_index // (len(_spi_baudrates) * len(_spi_ids))) % len(_spi_use_hw)
    id_idx = (_cfg_index // len(_spi_baudrates)) % len(_spi_ids)
    baud_idx = _cfg_index % len(_spi_baudrates)
    return _spi_use_hw[hw_idx], _spi_ids[id_idx], _spi_baudrates[baud_idx]


def _reinit_reader():
    use_hw, spi_id, baud = _next_config()
    spi_obj = _make_spi(baud, use_hw, spi_id)
    cs.value(1)
    _pulse_reset()
    print("Reinit MFRC522 with SPI baudrate=%d (HW=%s, SPI_ID=%d)" % (baud, str(use_hw), spi_id))
    rdr = MFRC522(spi_obj, cs)
    ver = _read_version(rdr)
    if ver is not None:
        print("MFRC522 VersionReg=0x%02X" % ver)
    return rdr


def _match_person(text):
    norm_text = _normalize(text)
    # 優先匹配任一候選名字作為前綴（處理填充或跨塊）
    candidates = [(_normalize(name), name) for name in PEOPLE if _normalize(name)]
    if not candidates:
        # 未設定白名單，將所有名字視為有效
        return text if norm_text else None
    for norm_name, raw_name in candidates:
        if norm_text.startswith(norm_name):
            return raw_name
    # 次選：若首塊剛好完整等長，做等長比較
    for norm_name, raw_name in candidates:
        if norm_text[:len(norm_name)] == norm_name:
            return raw_name
    # 若包含白名單字串，也視為有效（處理 "name:xxx" 等格式）
    for norm_name, raw_name in candidates:
        if norm_name and norm_name in norm_text:
            return raw_name
    return None


def _blink_led(led_obj, total_ms=3000, half_period_ms=250):
    if led_obj is None:
        return
    cycles = max(1, total_ms // (half_period_ms * 2))
    for _ in range(cycles):
        try:
            led_obj.value(1)
            sleep_ms(half_period_ms)
            led_obj.value(0)
            sleep_ms(half_period_ms)
        except Exception:
            break
    try:
        led_obj.value(0)
    except Exception:
        pass


def _whitelist_configured():
    for name in PEOPLE:
        if _normalize(name):
            return True
    return False


def _signal_reject():
    print("Unauthorized card detected")
    _blink_led(led_reject, total_ms=3000, half_period_ms=250)


def _signal_detected():
    try:
        led_detect.value(1)
        sleep_ms(2000)
        led_detect.value(0)
    except Exception:
        pass


def _signal_authorized():
    if led_accept is None:
        return
    print("Authorized card detected")
    try:
        led_accept.value(1)
        sleep_ms(3000)
    except Exception:
        pass
    try:
        led_accept.value(0)
    except Exception:
        pass


def _read_name_blocks_8_9(rdr, raw_uid, key):
    # Authenticate with Key A then Key B, read blocks 8 and 9, return decoded name
    for key_mode in (rdr.AUTHENT1A, rdr.AUTHENT1B):
        if rdr.auth(key_mode, 8, key, raw_uid) == rdr.OK:
            data8 = rdr.read(8)
            data9 = rdr.read(9)
            rdr.stop_crypto1()
            if data8 is not None and data9 is not None:
                try:
                    b8 = bytes(bytearray(data8))
                except Exception:
                    b8 = bytes(data8) if isinstance(data8, (bytes, bytearray)) else bytes([d for d in data8])
                try:
                    b9 = bytes(bytearray(data9))
                except Exception:
                    b9 = bytes(data9) if isinstance(data9, (bytes, bytearray)) else bytes([d for d in data9])
                buf = b8 + b9
                # Trim at first 0x00 terminator
                try:
                    zero_idx = buf.index(0)
                    buf = buf[:zero_idx]
                except Exception:
                    pass
                # Decode without errors kwarg for MicroPython compatibility
                try:
                    return buf.decode('utf-8').strip()
                except Exception:
                    try:
                        return buf.decode().strip()
                    except Exception:
                        try:
                            return buf.decode('latin-1').strip()
                        except Exception:
                            return _bytes_to_text(buf)
    return None


def _handle_detected_name(name):
    if name is None:
        return False
    normalized = _normalize(name)
    if len(normalized) == 0:
        return False
    approved = _match_person(name)
    if approved is None:
        if _whitelist_configured():
            print("Detected card value '%s' is not in whitelist" % name)
            _signal_reject()
            return False
        else:
            approved = name
    print("Card content decoded:", name)
    print("Attempting to upload to Adafruit IO...")
    oled.show()
    oled.fill(0)
    oled.show()
    oled.text("Hello:   "+ name,0,9,1)
    oled.show()
    sleep_ms(2000)
    oled.fill(1)
    sent_ok = _aio_publish_resilient(name)
    if sent_ok:
        try:
            led_sent.value(1)
            sleep_ms(2000)
            led_sent.value(0)
            oled.show()
            oled.fill(0)
            oled.show()
            oled.text("Upload OK",0,9,1)
            oled.show()
            sleep_ms(2000)
            oled.fill(1)
        except Exception:
            pass
        print("Upload complete for:", name)
    else:
        print("Upload failed for:", name)
    _signal_authorized()
    sleep_ms(500)
    return True


def do_read():
    try:
        global last_seen_uid
        print("RFID reader starting... SCK=%d MOSI=%d MISO=%d CS=%d, baud=%d, HW_SPI=%s, SPI_ID=%d" % (
            PIN_SCK, PIN_MOSI, PIN_MISO, PIN_CS, _spi_baudrates[0], str(USE_HARDWARE_SPI), SPI_ID))
        _pulse_reset()
        rdr = MFRC522(spi, cs)
        # Ensure antenna is on and set RX gain high for better detection
        try:
            rdr.antenna_on(True)
        except Exception:
            pass
        try:
            if hasattr(rdr, 'set_antenna_gain'):
                rdr.set_antenna_gain(7)
        except Exception:
            pass
        sleep_ms(30)
        ver = _read_version(rdr)
        if ver is not None:
            print("MFRC522 VersionReg=0x%02X" % ver)
            if ver in (0x88, 0x90, 0x91, 0x92):
                pass
            else:
                print("Warning: unexpected VersionReg (check wiring/CS pin)")
        idle_ticks = 0
        while True:
            # 嘗試兩種請求模式增加檢卡成功率，並加入小延時與重試
            found = False
            for _ in range(2):
                (stat, tag_bits) = rdr.request(rdr.REQIDL)
                if stat != rdr.OK:
                    (stat, tag_bits) = rdr.request(rdr.REQALL)
                if stat == rdr.OK:
                    found = True
                    break
                sleep_ms(5)

            if found:
                (stat, raw_uid) = rdr.anticoll()
                if stat == rdr.OK and len(raw_uid) >= 4:
                    if rdr.select_tag(raw_uid) == rdr.OK:
                        should_signal_detect = False
                        try:
                            uid_tuple = tuple(int(x) for x in raw_uid[:4])
                        except Exception:
                            try:
                                uid_tuple = tuple(raw_uid)
                            except Exception:
                                uid_tuple = None
                        if uid_tuple is not None and uid_tuple != last_seen_uid:
                            should_signal_detect = True
                            last_seen_uid = uid_tuple
                        key_default = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]
                        # Read name specifically from blocks 8 & 9 (writer stores here)
                        name = _read_name_blocks_8_9(rdr, raw_uid, key_default)
                        handled = False
                        if name is not None:
                            handled = _handle_detected_name(name)
                        if not handled:
                            # Fallback to previous broader read logic if needed
                            auth_ok = False
                            for key_mode in (rdr.AUTHENT1A, rdr.AUTHENT1B):
                                if rdr.auth(key_mode, 8, key_default, raw_uid) == rdr.OK:
                                    auth_ok = True
                                    break
                            if auth_ok:
                                blk_bytes = _read_blocks(rdr, 8, 3)
                                rdr.stop_crypto1()
                                if blk_bytes is not None:
                                    name8 = _bytes_to_text(blk_bytes[0:16])
                                    name810 = _bytes_to_text(blk_bytes)
                                    candidate = name810 if len(_normalize(name810)) >= len(_normalize(name8)) else name8
                                    candidate = candidate.split('\x00')[0].strip()
                                    if len(_normalize(candidate)) > 0:
                                        handled = _handle_detected_name(candidate)
                                    else:
                                        print("Card detected but name is empty")
                            else:
                                rdr.stop_crypto1()
                        if should_signal_detect:
                            _signal_detected()
                        elif handled:
                            print("Repeated card detected; skipping detect LED")
                        else:
                            print("Card detected but no data processed; waiting for next card")
                    sleep_ms(150)
                else:
                    sleep_ms(50)
            else:
                # 每約 1 秒打印一次等待訊息，並在若干秒無卡時切換 SPI 設定重試
                idle_ticks += 0.5
                # 無卡時重置上次 UID，下一次新卡靠近才會再次閃燈
                try:
                    last_seen_uid = None
                    oled.fill(1)
                except Exception:
                    pass
                if idle_ticks % 20 == 0:
                    print("Waiting for card... (current cfg idx=%d)" % _cfg_index)
                    oled.show()
                    oled.fill(0)
                    oled.show()
                    oled.text("Waiting card",0,9,1)
                    oled.show()
                    sleep_ms(2000)
                    oled.fill(1)
                # 更頻繁地重初始化以提高相容性
                if idle_ticks != 0 and idle_ticks % 60 == 0:
                    rdr = _reinit_reader()
                sleep_ms(50)
    except KeyboardInterrupt:
        print("Bye")

# 程序入口
if __name__ == '__main__':
    do_read()


