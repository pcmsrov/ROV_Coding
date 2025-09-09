#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# －－－－湖南创乐博智能科技有限公司－－－－
#  文件名：35_RFID_read.py
#  版本：V2.0
#  author: zhulin
# 说明：RFID 读取数据
#####################################################
from time import sleep_ms
from machine import Pin, SPI, SoftSPI
from mfrc522 import MFRC522

# 可依實際接線修改
PIN_SCK = 18
PIN_MOSI = 23
PIN_MISO = 19
PIN_CS = 5  # MFRC522 SDA/SS 腳位
PIN_RST = None  # 若 RST 接到了某個 GPIO，填入該腳位號；若接 3.3V 則保持 None

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
    "hayden",
     "kenny",
     "nathan",
     "queenie",
    "ryan",
    "rianna",
    "helios",
    "bosco",
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
    candidates = [(_normalize(name), name) for name in PEOPLE if name and len(name) > 0]
    for norm_name, raw_name in candidates:
        if norm_text.startswith(norm_name):
            return raw_name
    # 次選：若首塊剛好完整等長，做等長比較
    for norm_name, raw_name in candidates:
        if norm_text[:len(norm_name)] == norm_name:
            return raw_name
    return None


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


def do_read():
    try:
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
                        key_default = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]
                        # Read name specifically from blocks 8 & 9 (writer stores here)
                        name = _read_name_blocks_8_9(rdr, raw_uid, key_default)
                        if name and len(_normalize(name)) > 0:
                            print("Name: %s" % name)
                            sleep_ms(500)
                        else:
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
                                        print("Name: %s" % candidate)
                                        sleep_ms(500)
                                    else:
                                        print("Card detected but name is empty")
                            else:
                                rdr.stop_crypto1()
                    sleep_ms(150)
                else:
                    sleep_ms(50)
            else:
                # 每約 1 秒打印一次等待訊息，並在若干秒無卡時切換 SPI 設定重試
                idle_ticks += 1
                if idle_ticks % 20 == 0:
                    print("Waiting for card... (current cfg idx=%d)" % _cfg_index)
                # 更頻繁地重初始化以提高相容性
                if idle_ticks != 0 and idle_ticks % 60 == 0:
                    rdr = _reinit_reader()
                sleep_ms(50)
    except KeyboardInterrupt:
        print("Bye")

# 程序入口
if __name__ == '__main__':
    do_read()