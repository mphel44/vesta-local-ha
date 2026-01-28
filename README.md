# 🏠 Vesta/Climax Local Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/mphel44/vesta-local-ha)](https://github.com/mphel44/vesta-local-ha/releases)
[![License](https://img.shields.io/github/license/mphel44/vesta-local-ha)](LICENSE)

A Home Assistant custom integration for **local control** of Vesta/Climax alarm panels (HSGW-MAX series and compatible models). This integration communicates directly with your panel over your local network - **no cloud required**.

## 🙏 Acknowledgements

This integration is inspired by [koying's smarthomesec_ha](https://github.com/koying/smarthomesec_ha), an integration that talks to the Smarthomesec website. This version has been adapted to communicate locally with the panel instead. Thanks to koying for the original work!

## ✨ Features

- 🔒 **100% Local Control** - All communication stays on your local network
- ⚡ **Responsive** - 5-second polling interval for near real-time updates
- 🚨 **Alarm Control Panel** - Arm/Disarm in multiple modes (Away, Home, Night) - no code required
- 📡 **Binary Sensors** - Door contacts, motion detectors, smoke/CO detectors, water leak sensors, glass break detectors
- 🔋 **Device Battery Monitoring** - Dedicated battery status sensor for each wireless device
- 📊 **Panel Diagnostics** - GSM signal strength, backup battery status, AC power status
- 📜 **Event Log** - Access the panel's event history
- 🔍 **Auto-Discovery** - Automatic detection via Zeroconf/mDNS
- 🌐 **Reverse Proxy Support** - Works with HTTPS reverse proxies

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
- 📜 Event Log (last event + full history in attributes)
- 🪫 Per-device Battery Status (Low Battery alerts)

## ⚙️ Configuration

### Automatic Discovery

If your panel supports Zeroconf/mDNS, Home Assistant will automatically detect it and prompt you to set it up.

### Manual Setup

1. Go to **Settings** > **Devices & Services**
2. Click **Add Integration**
3. Search for "Vesta/Climax Local"
4. Enter your panel's details:
   - **Host**: IP address or hostname of your panel (e.g., `192.168.1.100`)
   - **Username**: Panel username (usually `admin`)
   - **Password**: Panel password
   - **Use HTTPS**: Enable if your panel uses HTTPS (e.g., via a reverse proxy)

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

## 🔐 Security

This integration is designed with security in mind:

- 🏠 **Local Only** - No data leaves your network; no cloud dependencies
- 🔀 **HTTP/HTTPS Support** - Choose based on your setup (HTTP for direct, HTTPS for reverse proxy)
- 🔑 **HTTP Basic Auth** - Standard authentication mechanism used by the panel
- 🛡️ **No Stored Credentials** - Credentials are stored securely in Home Assistant's encrypted storage

### Network Requirements

- Your Home Assistant instance must be able to reach the panel on your local network
- Default port: 80 (HTTP) or 443 (HTTPS via reverse proxy)
- Ensure your firewall allows communication between Home Assistant and the panel

## 🚨 Alarm Control

The alarm control panel entity supports the following modes:
- **Disarm** - Disarm the alarm system
- **Arm Away** - Full arm mode
- **Arm Home** - Home arm mode (partial perimeter)
- **Arm Night** - Night arm mode

> **Note**: No code is required to arm or disarm the alarm through this integration. The panel authenticates via HTTP Basic Auth with your configured credentials.

## 🔧 Troubleshooting

### ❌ Cannot Connect

1. Verify the panel's IP address is correct
2. Ensure you can access the panel's web interface from a browser
3. Check that no firewall is blocking communication
4. Try using the IP address instead of hostname
5. If using HTTPS, verify the "Use HTTPS" option is checked

### 🔒 Invalid Authentication

1. Verify your username and password
2. Try logging into the panel's web interface with the same credentials
3. The default username is usually `admin`

### 👻 Sensors Not Appearing

1. Wait for the first polling cycle (up to 5 seconds)
2. Check that the devices are properly enrolled on your panel
3. Review the Home Assistant logs for any parsing errors

### 🔢 "Arming requires a code" Error

If you see this error with an alarm card, ensure you're using the latest version of the integration. The integration is configured to not require a code for arming/disarming operations.

## 🛠️ Technical Details

### API Communication

The integration communicates with the panel using:
- **Protocol**: HTTP (default) or HTTPS (for reverse proxy setups)
- **Authentication**: HTTP Basic Auth
- **Headers**: `X-Requested-With: XMLHttpRequest` and `Referer` for AJAX-style requests
- **Data Format**: `application/x-www-form-urlencoded` for POST requests
- **Library**: httpx (async HTTP client)

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/action/panelCondGet` | Get panel status (mode, battery, GSM signal) |
| `/action/deviceListGet` | Get list of all enrolled devices |
| `/action/panelCondPost` | Set alarm mode |
| `/action/eventLogGet` | Get event history |

### Polling

- Default interval: 5 seconds
- Panel status and device list are fetched concurrently for efficiency
- Exponential backoff retry logic for network resilience

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This integration is not affiliated with, endorsed by, or connected to Climax Technology or Vesta. All product names, logos, and brands are property of their respective owners.

## 💬 Support

- [GitHub Issues](https://github.com/mphel44/vesta-local-ha/issues) - Report bugs or request features
- [Home Assistant Community](https://community.home-assistant.io/) - General discussion
