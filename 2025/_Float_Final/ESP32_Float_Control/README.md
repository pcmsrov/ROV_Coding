# ESP32 浮標控制程序

此程序用於控制浮標的浮力系統，通過 ESP32 和 DRV8871 馬達驅動器實現。

## 硬體連接

| ESP32 引腳 | 連接目標 |
|------------|----------|
| GPIO25     | DRV8871 IN1 |
| GPIO26     | DRV8871 IN2 |
| 5V         | 感測器供電 (如有) |
| GND        | 共地 |
| 3.3V       | 感測器邏輯電平 (如有) |
| SDA (GPIO21) | 感測器 SDA (如有) |
| SCL (GPIO22) | 感測器 SCL (如有) |


## BlueRobtics, Bar30 Depth Sensor, I2C
Supply Voltage	2.5–5.5 volts
I2C Logic Voltage (SDA and SCL)	2.5–3.6 volts
[ESP32 GPIO 3.3V, OK. Arduino PinOut 5V, Need Converter]
Connector Pinout	
1 - Red / Vin
2 - Green / SCL
3 - White / SDA
4 - Black / GND



## DRV8871 操作邏輯

| IN1 | IN2 | 動作 |
|-----|-----|------|
| LOW | LOW | 停止/煞車 |
| LOW | HIGH | 正轉 (上升) |
| HIGH | LOW | 反轉 (下潛) |
| HIGH | HIGH | 停止/煞車 |

## WiFi 設置

程序將創建一個名為 `Float_Control` 的 WiFi 網絡，密碼為 `12345678`。
連接後可通過 `192.168.4.1` 訪問控制界面。

## API 端點

- `GET /` - 網頁控制界面
- `GET /status` - 獲取當前狀態 (JSON 格式)
- `POST /up` - 控制上升
- `POST /down` - 控制下潛
- `POST /stop` - 控制停止

## 安裝所需庫

在 Arduino IDE 中安裝以下庫：

1. ESP32 開發板支援 (通過開發板管理器)
2. WiFi 庫 (ESP32 自帶)
3. WebServer 庫 (ESP32 自帶)
4. ArduinoJson 庫 (通過庫管理器)

## 添加實際深度感測器

如需添加實際深度感測器（如 MS5837 或 BMP390），請按照以下步驟：

1. 安裝相應的庫
2. 修改程序中的 `updateDepth()` 函數
3. 將 `isSimulation` 變量設置為 `false`

## 故障排除

- 如果無法連接 WiFi，請檢查 ESP32 是否已啟動，電源是否正常
- 如果馬達不轉動，請檢查 DRV8871 的連接和供電
- 如果數據不準確，請校準深度感測器 



===== Notes =====
In Air
Accending 上升, Push, 7.3s
Deccending 下降, Pull, 7.5s 