# TG PRO QUANTUM – Desktop Application Guide

## System Requirements

| Component | Minimum |
|-----------|---------|
| OS | Windows 10 / 11 (64-bit) |
| RAM | 4 GB |
| Disk space | 500 MB free |
| Internet | Required for Telegram API calls |

> **No Python installation required.** The `.exe` bundles everything.

---

## Download

1. Go to the [Releases page](../../releases).
2. Find the latest release (e.g. **Release v7.0.1 – Desktop & API**).
3. Under **Assets**, download **`TG-PRO-QUANTUM-vX.X.X.exe`**.

---

## Installation

The application is a single portable executable – no installer needed.

1. Move the downloaded `.exe` to a convenient folder (e.g. `C:\TG-PRO-QUANTUM\`).
2. Double-click `TG-PRO-QUANTUM-vX.X.X.exe` to launch.
3. If Windows SmartScreen warns you, click **More info → Run anyway**.

---

## First Launch Configuration

On the very first run you will be prompted for:

| Field | Description |
|-------|-------------|
| **API ID** | From [my.telegram.org](https://my.telegram.org) → API development tools |
| **API Hash** | Same page as API ID |
| **License Key** | Provided after purchase |

Settings are saved locally in `config/config.json` next to the `.exe`.

---

## Troubleshooting

### App doesn't start
- Make sure you are on Windows 10 or later (64-bit).
- Run the `.exe` as Administrator if you see permission errors.

### "Missing DLL" error
- Install the [Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe).

### Telegram connection fails
- Check your internet connection.
- Verify your API ID / API Hash at [my.telegram.org](https://my.telegram.org).

### License validation error
- Confirm the license key matches the machine / IP it was issued for.
- Contact support: admin@tgproquantum.com

---

## FAQs

**Q: Can I run multiple instances?**  
A: Yes – copy the `.exe` to separate folders, each with its own `config/`.

**Q: Is my data stored locally?**  
A: Yes. All account sessions and settings are stored on your machine only.

**Q: How do I update?**  
A: Download the new `.exe` from the Releases page and replace the old file.

**Q: Does it work on macOS / Linux?**  
A: The `.exe` is Windows-only. Run the Python source directly on macOS/Linux.

---

## Build from Source

```bash
# 1. Install build dependencies
pip install -r requirements-gui.txt

# 2. Build the executable
python build_executable.py

# Output: dist/TG-PRO-QUANTUM.exe
```

The GitHub Actions workflow (`.github/workflows/build-exe.yml`) runs this
automatically on every published release and attaches the `.exe` to the
release assets.

---

## License

See [LICENSE](license/) for terms of use.  
Commercial use requires a valid license key issued by the TG PRO QUANTUM team.
