#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# －－－－湖南创乐博智能科技有限公司－－－－
#  文件名：35_RFID_write.py
#  版本：V2.0
#  author: zhulin
# 说明：RFID 写入数据
#####################################################

import mfrc522
from machine import Pin, SoftSPI
sck = Pin(18, Pin.OUT)
mosi = Pin(23, Pin.OUT)
miso = Pin(19, Pin.OUT)
spi = SoftSPI(baudrate=100000, polarity=0, phase=0, sck=sck, mosi=mosi, miso=miso)

sda = Pin(5, Pin.OUT)

# 将姓名编码为UTF-8并写入至两个数据块（8与9），最多32字节，使用0x00填充并追加终止符
def _prepare_name_buffer(name_str):
    try:
        name_bytes = name_str.encode('utf-8')
    except Exception:
        # 回退到ASCII
        name_bytes = bytes([b for b in name_str if ord(b) < 128])
    # 限制为最多31字节内容，保留1字节作为终止符0x00
    name_bytes = name_bytes[:31]
    buf = bytearray(32)
    buf[:len(name_bytes)] = name_bytes
    buf[len(name_bytes)] = 0x00
    return bytes(buf)

def do_write(name=""):
    rdr = mfrc522.MFRC522(spi, sda)

    if not name:
        try:
            name = input("請輸入要寫入卡片的姓名（最多約31字節，UTF-8）：")
        except Exception:
            name = ""

    data32 = _prepare_name_buffer(name)
    block8 = data32[0:16]
    block9 = data32[16:32]

    print("")
    print("Place card before reader to write name into blocks 8 and 9")
    print("")

    try:
        while True:

            (stat, tag_type) = rdr.request(rdr.REQIDL)

            if stat == rdr.OK:

                (stat, raw_uid) = rdr.anticoll()

                if stat == rdr.OK:
                    print("New card detected")
                    print("  - tag type: 0x%02x" % tag_type)
                    print("  - uid : 0x%02x%02x%02x%02x" % (raw_uid[0], raw_uid[1], raw_uid[2], raw_uid[3]))
                    print("")

                    if rdr.select_tag(raw_uid) == rdr.OK:

                        key = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]

                        if rdr.auth(rdr.AUTHENT1A, 8, key, raw_uid) == rdr.OK:
                            w1 = rdr.write(8, block8)
                            w2 = rdr.write(9, block9)
                            rdr.stop_crypto1()
                            if w1 == rdr.OK and w2 == rdr.OK:
                                print("Name written to card (blocks 8 & 9)")
                            else:
                                print("Failed to write name to card")
                        else:
                            print("Authentication error")
                    else:
                        print("Failed to select tag")

    except KeyboardInterrupt:
        print("Bye")

# 程序入口
if __name__ == '__main__':
    # 示例：直接传入固定姓名；也可留空在运行时输入
    do_write()  # 寫入姓名到區塊8與9