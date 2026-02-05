# 🏠 Vesta/Climax Local Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/mphel44/vesta-local-ha)](https://github.com/mphel44/vesta-local-ha/releases)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A Home Assistant custom integration for **local control** of Vesta/Climax alarm panels (HSGW-MAX series and compatible models). This integration communicates directly with your panel over your local network - **no cloud required**.

## 🙏 Acknowledgements

This integration is inspired by [koying's smarthomesec_ha](https://github.com/koying/smarthomesec_ha), an integration that talks to the Smarthomesec website. This version has been adapted to communicate locally with the panel instead. Thanks to koying for the original work!

## ✨ Features

- 🔒 **100% Local Control** - All communication stays on your local network
- ⚡ **Responsive** - 5-second polling interval for near real-time updates
- 🚨 **Alarm Control Panel** - Arm/Disarm in multiple modes (Away, Home, Night) - no code required
- 📡 **Binary Sensors** - Door contacts, motion detectors, smoke/CO detectors, water leak sensors, glass break detectors
- 🔋 **Device Battery Monitoring** - Dedicated battery status sensor for each wireless device
- 📜 **Event Log** - Access the panel's event history
- 📋 **Per-device Event Log** - Each device gets a "Last Event" sensor with its full event history

## 📦 Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots menu (top right) and select "Custom repositories"
4. Add this repository URL: `https://github.com/mphel44/vesta-local-ha`
5. Select "Integration" as the category
6. Click "Add"
7. Search for "Vesta/Climax Local" and install it
8. Restart Home Assistant

### Manual Installation

1. Download the latest release from the [releases page](https://github.com/mphel44/vesta-local-ha/releases)
2. Extract the `custom_components/vesta_local` folder to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

## ⚙️ Configuration

### Automatic Discovery

If your panel supports Zeroconf/mDNS, Home Assistant will automatically detect it and prompt you to set it up.

### Manual Setup

1. Go to **Settings** > **Devices & Services**
2. Click **Add Integration**
3. Search for "Vesta/Climax Local"
4. Enter your panel's details:
   - **Host**: IP address or hostname of your panel (e.g., `192.168.1.100`)
   - **Username**: Panel username (default: `admin`)
   - **Password**: Panel password (default: `cX+HsA*7F1`)
   - **Use HTTPS**: Enable if your panel uses HTTPS (e.g., via a reverse proxy)

> **Note**: The default credentials can be found on page 9 of the [installation manual](https://www.scribd.com/document/715294461/Vesta-HSGW-MAX-20220330). The username and password can be changed later in the panel configuration webpage.

### Direct Connection (Default)

For direct connection to your panel on your local network:
- Leave "Use HTTPS" unchecked
- Enter the panel's local IP address (e.g., `192.168.1.100`)
- The integration will use HTTP on port 80

### Via Reverse Proxy

If you access your panel through a reverse proxy with HTTPS:
- Check "Use HTTPS"
- Enter your proxy hostname (e.g., `vesta.yourdomain.com`)
- The integration will use HTTPS

## 🚨 Alarm Control

The alarm control panel entity supports the following modes:
- **Disarm** - Disarm the alarm system
- **Arm Away** - Full arm mode
- **Arm Home** - Home arm mode (partial perimeter)
- **Arm Night** - Night arm mode

> **Note**: No code is required to arm or disarm the alarm through this integration. The panel authenticates via HTTP Basic Auth with your configured credentials.

## 🎛️ Supported Devices

### Alarm Panel
- Climax/Vesta HSGW-MAX series
- Other Vesta-compatible panels with local HTTP API

### Sensors (automatically detected)
| Device Type | Home Assistant Entity |
|-------------|----------------------|
| 🚪 Door Contact | Binary Sensor (Door) |
| 🏃 PIR / IR Motion | Binary Sensor (Motion) |
| 🔥 Smoke Detector | Binary Sensor (Smoke) |
| 💨 CO Detector | Binary Sensor (CO) |
| 💧 Water Leak Sensor | Binary Sensor (Moisture) |
| 🪟 Glass Break Detector | Binary Sensor (Vibration) |

### Diagnostic Sensors
- 📶 GSM Signal Strength (%)
- 🔋 Panel Battery Status
- 🔌 AC Power Status
- 📜 Event Log (last event + 20 most recent events in attributes)
- 📋 Per-device Last Event (last action + 20 most recent device events in attributes)
- 🪫 Per-device Battery Status (Low Battery alerts)

## 🛠️ Technical Details

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/action/panelCondGet` | Get panel status (mode, battery, GSM signal) |
| `/action/deviceListGet` | Get list of all enrolled devices |
| `/action/panelCondPost` | Set alarm mode |
| `/action/logsGet` | Get event history (POST with `max_count`) |

### Polling

- Default interval: 5 seconds
- Panel status, device list, and event log are fetched concurrently for efficiency
- Exponential backoff retry logic for network resilience

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This integration is not affiliated with, endorsed by, or connected to Climax Technology or Vesta. All product names, logos, and brands are property of their respective owners.
