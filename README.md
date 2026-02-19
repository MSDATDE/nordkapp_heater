# Nordkapp Heater - Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![License](https://img.shields.io/github/license/netresearch-digital/nordkapp_heater.svg)](LICENSE)

Control your Nordkapp / HeatGenie diesel heater from Home Assistant via Bluetooth.

## Features

- **Climate Entity** - Full thermostat control with target temperature and preset modes (Auto/Manual/Start-Stop)
- **Power Switch** - Simple ON/OFF control
- **Gear Level Control** - Adjust heating power (1-10) via fan entity
- **Sensors** - Monitor ambient temperature, shell temperature, battery voltage, fan RPM, pump frequency, altitude, error codes
- **Binary Sensors** - Running state, error indicator, glow plug, pump and fan activity
- **Action Buttons** - Clear error, start ventilation mode
- **Auto-Discovery** - Automatic detection of heater via BLE
- **Bluetooth LE** - Direct local connection, no cloud required
- **Multi-language** - Polish, English, German, Spanish

## Supported Devices

| Feature | Details |
|---------|---------|
| Protocol | HeatGenie AA + CRC16 (8-byte packets) |
| BLE Service | `181A` (Environmental Sensing) |
| Write method | `writeNoResponse` (single write) |
| MAC Pattern | `C1:XX:XX:XX:FE:XX` (random address) |
| Brands | Nordkapp, HeatGenie, Vevor (181A variant) |

> **Note:** This integration does NOT support heaters using FFE0/FFF0 protocols (Vevor AA55/AA66, HeaterCC, Sunster, Hcalory). For those, use the [Diesel Heater](https://github.com/MSDATDE/homeassistant-vevor-heater) integration.

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations**
3. Click the three dots menu -> **Custom repositories**
4. Add this repository URL
5. Category: **Integration**
6. Click **Add**
7. Search for **"Nordkapp Heater"** and install
8. Restart Home Assistant

### Manual Installation

1. Download the latest release from GitHub
2. Copy the `custom_components/nordkapp_heater` folder to your Home Assistant's `custom_components` directory
3. Restart Home Assistant

## Configuration

### Auto-Discovery

If your heater is powered on and advertising via BLE, Home Assistant will automatically detect it. You'll see a notification to set up the new device - just confirm and you're done.

> **Important:** The heater only advertises via BLE when it is powered on. If the heater is off, it will not be discoverable.

### Manual Setup

1. Go to **Settings** -> **Devices & Services**
2. Click **"+ Add Integration"**
3. Search for **"Nordkapp Heater"**
4. Enter your heater's BLE MAC address (e.g. `C1:01:7B:E7:FE:73`)
5. Click **Submit**

### Finding Your MAC Address

The MAC address is on the QR code sticker on your heater. It follows the pattern `C1:XX:XX:XX:FE:XX`.

You can also find it by scanning with the HeatGenie app or using a BLE scanner app looking for devices advertising service `181A`.

## Entities

After setup, you'll have these entities:

### Climate
| Entity | Description |
|--------|-------------|
| `climate.nordkapp_heater` | Thermostat control (OFF / HEAT / FAN_ONLY) with presets Auto, Manual, Start-Stop |

### Fan
| Entity | Description |
|--------|-------------|
| `fan.nordkapp_heater_gear` | Gear level 1-10 mapped as fan speed percentage |

### Switch
| Entity | Description |
|--------|-------------|
| `switch.nordkapp_heater_power` | Power ON/OFF |

### Sensors
| Entity | Description |
|--------|-------------|
| Ambient temperature | Room/cabin temperature (°C) |
| Shell temperature | Heater body temperature (°C) |
| Battery voltage | Supply voltage (V) |
| Fan speed | Fan RPM |
| Pump frequency | Oil pump frequency (Hz) |
| Heater state | Current state (Standby, Igniting, Auto Run, Manual Run, etc.) |
| Error code | Error code (0 = no error) |
| Altitude | Altitude from sensor (m) |
| Target temperature | Current target temperature (°C) |
| Gear level | Current gear level (1-10) |

### Binary Sensors
| Entity | Description |
|--------|-------------|
| Running | Heater is active |
| Error | Error condition detected |
| Glow plug | Glow plug is active |
| Pump | Oil pump is active |
| Fan | Fan is running |

### Buttons
| Entity | Description |
|--------|-------------|
| Clear error | Clear the current error code |
| Ventilation | Start ventilation mode |

## Heater States

| State | Description |
|-------|-------------|
| Standby | Heater is off, ready to start |
| Igniting | Starting up, glow plug heating |
| Auto Run | Running in automatic temperature mode |
| Manual Run | Running at fixed gear level |
| Residual Burn | Cooling down after power off |
| Ventilation | Fan-only mode (no heating) |
| Start-Stop Run | Running in start-stop mode |
| Error | Error condition - check error code |

## Troubleshooting

### Heater Not Found

- Make sure the heater is **powered on** (when off, BLE stops advertising)
- Make sure Bluetooth is enabled on your Home Assistant host
- The HeatGenie app must be **disconnected** (only one BLE connection at a time)
- If using ESPHome Bluetooth Proxy, ensure it has available connection slots

### Connection Drops

- The integration automatically reconnects every 15 seconds
- BLE range is limited - keep HA host within ~10m of the heater
- Check Home Assistant logs for connection errors

### Commands Not Working

- The heater requires a BLE bind handshake - this is handled automatically
- If commands are ignored, try power-cycling the heater
- Some commands only work in specific states (e.g. gear change requires Manual mode)

### Debug Logging

Enable debug logging in `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.nordkapp_heater: debug
```

## Technical Details

### BLE Protocol

This heater uses a completely different protocol from common diesel heaters:

- **Service UUID**: `181A` (not FFE0/FFF0)
- **Notify**: characteristic `3A00`
- **Write**: characteristic `3A01` (writeNoResponse only)
- **Packets**: 8-byte commands with CRC16 checksum
- **Bind**: 12-byte handshake (0x91 with reversed MAC)
- **Status**: 52-byte broadcast every ~2 seconds

### Connection Flow

1. Scan for BLE device with service `181A`
2. Connect and subscribe to notifications on `3A00`
3. Start status polling (command `0x65`)
4. Perform bind handshake if requested
5. Send commands via `writeNoResponse` to `3A01`

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

If you find this integration useful, consider supporting development:

[!["Buy Me A Coffee"](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-support-yellow.svg)](https://buymeacoffee.com/)

If you encounter issues:
1. Check the [Issues](../../issues) page
2. Enable debug logging and include logs in your report
3. Provide your heater model and MAC address pattern

---

**Disclaimer**: This is an unofficial integration and is not affiliated with Nordkapp, HeatGenie, or Vevor.
