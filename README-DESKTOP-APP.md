# TG PRO QUANTUM - Desktop Application

Professional Telegram broadcast desktop client with GUI.

## Download

Download the latest `.exe` from [GitHub Releases](https://github.com/adsgogle251-collab/tg_pro_quantum/releases).

## System Requirements

- **OS**: Windows 10 or later (64-bit)
- **RAM**: 2 GB minimum, 4 GB recommended
- **Disk**: 500 MB free space
- **Python**: Not required (standalone executable)

## Installation

1. Download `TG-PRO-QUANTUM-vX.X.X.exe` from Releases.
2. Double-click the `.exe` file to run it.
3. If Windows shows a security warning, click **"More info" → "Run anyway"**.
4. The admin panel launches automatically.

## Build from Source

```bash
pip install -r requirements-gui.txt
python build_executable.py
# Output: dist/TG-PRO-QUANTUM.exe
```

## Troubleshooting

| Issue | Solution |
|---|---|
| SmartScreen warning | Click "More info" → "Run anyway" |
| Cannot connect to API | Check internet; verify backend at https://tg-pro-quantum.onrender.com |
| License validation failed | Verify license key is valid and not expired |
| App crashes on startup | Delete config files and restart; report issue on GitHub |

## Features

- Multi-account Telegram management
- Broadcast campaigns to groups
- Real-time statistics and auto-scheduling
- License validation and OTP verification

## Support

- **API Backend**: https://tg-pro-quantum.onrender.com
- **GitHub Issues**: https://github.com/adsgogle251-collab/tg_pro_quantum/issues
