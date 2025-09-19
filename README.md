# Merit Access – Technical Documentation

## 1. Main Operating Modes

### 1.1 Offline Mode

#### LED Indicator

Magenta (solid)  

#### Mode Number

1  

#### Configuration Parameters

- **Wi-Fi Status:** Determined by database settings
- **Network:** DHCP or Static (per database settings)
- **MQTT:** Determined by database settings
- **Syslog:** Determined by database settings
- **Time Plans:** Determined by database settings
- **Config Button Action:** Short press → Switch to *ConfigModeOffline*

#### Functionality

In Offline Mode, the device operates solely with the **local offline database**:

- If a presented card exists in the local database with access permissions, access is granted.
- If the card is not found or lacks permissions, access is denied.

---

### 1.2 Cloud Mode

#### LED Indicator

Yellow (solid/blinking)  

#### Mode Number

0  

#### Configuration Parameters

- **Wi-Fi Status:** Determined by database settings
- **Network:** DHCP or Static (per database settings)
- **MQTT:** Determined by database settings
- **Syslog:** Determined by database settings
- **Time Plans:** Determined by database settings
- **Config Button Action:** Short press → Switch to *Config Mode – Cloud*
- **LED States:**
  - Solid yellow: Connected to Cloud
  - Fast blink: Disconnected from Cloud

#### Functionality

In Cloud Mode, the device validates credentials against both the **local** and **remote (cloud)** databases:

- If the card is not found locally, validation is performed via cloud web services.
- Access is granted or denied based on the results of this validation.

---

## 2. Configuration Modes

### 2.1 ConfigModeOffline

#### LED Indicator

Blue (blinking)  

#### Activation

Short press of Config Button from Offline Mode  

#### Configuration Parameters

- **Wi-Fi Status:** Access Point mode, IP: `10.10.10.1`
- **Network:** Static (`10.10.10.1`)
- **MQTT:** Disabled
- **Syslog:** Determined by database settings
- **Time Plans:** Disabled
- **Easy Add/Remove:** Determined by database settings
- **Config Button Action:** Short press → Return to Offline Mode

#### Functionality

- Device acts as a **Wi-Fi access point** for configuration.
- Connect to `10.10.10.1` via the Merit Access web application to manage the local database.
- **Quick Add/Remove** card feature available:
  - Present cart to the reader:
    - If card exists → removed (LED: solid red)
    - If card does not exist → added with access granted (LED: solid green)

---

### 2.2 Config Mode – Cloud

#### LED Indicator

Blue (blinking)  

#### Activation

Short press of Config Button from Cloud Mode  

#### Configuration Parameters

- **Wi-Fi Status:** Access Point mode, IP: `10.10.10.1`
- **Network:** Static (`10.10.10.1`)
- **MQTT:** Disabled
- **Syslog:** Determined by database settings
- **Time Plans:** Disabled
- **Easy Add/Remove:** Disabled
- **Config Button Actions:**
  - Short press → Return to Cloud Mode
  - Long press (10s) → Switch to *Config Mode – Connect*

#### Functionality

- Device acts as a **Wi-Fi access point** for configuration.
- Local database management available via `10.10.10.1` and the Merit Access web application.

---

### 2.3 ConfigModeOSDP

#### LED Indicator

White (fast blinking)  

#### Activation

Long press (10s) of Config Button  

#### Purpose

Special mode for **OSDP device scanning**, secure key generation, and connection setup.

#### Procedure

**With Secure Channel**

1. In main mode, set all readers to *install mode* via HID Manager app (MOB key required).
2. Press Config Button for 10 seconds to enter ConfigOSDPMode.
3. Wait until process completes and device returns to main mode.
4. Set all readers to *secure mode* via HID Manager app (MOB key required).

**Without Secure Channel**

1. In main mode, set all readers to *install mode* via HID Manager app (MOB key required).
2. Press Config Button for 10 seconds to enter ConfigOSDPMode.
3. Wait until process completes and device returns to main mode.

---

## 3. Factory Reset Procedure

1. Press and hold the **Config Button**.
2. While holding, press the **Reboot Button**.
3. Continue holding until the LED blinks red three times, then release.

---

## 4. Updates

- updates are handled by the auto_update service

---

## 5. Development Notes

### 5.1 Pigpio Setup

```bash
sudo apt-get install pigpio python3-pigpio
pip install pigpio
sudo nano /etc/systemd/system/pigpiod.service
```

add

```ini
[Unit]
Description=Pigpio daemon
After=network.target

[Service]
ExecStartPre=/bin/rm -f /var/run/pigpio.pid
ExecStart=/usr/bin/pigpiod -x 0x0FFFFFFF
ExecStop=/bin/systemctl kill pigpiod
Type=forking

[Install]
WantedBy=multi-user.target
```

run

```bash
sudo systemctl daemon-reload
sudo systemctl enable pigpiod

sudo reboot
sudo systemctl status pigpiod (check if it is running)
ps aux | grep pigpiod
```

should look like this:

```bash
root       450  6.3  0.1  13620  1812 ?        SLsl 17:53   0:25 /usr/bin/pigpiod -x 0x0FFFFFFF
meritac+  1508  0.0  0.0   7448   552 pts/0    S+   18:00   0:00 grep --color=auto pigpiod
```

### 5.2 Requirements

```bash
pip install -r requirements.txt
```
