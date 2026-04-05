# TG PRO QUANTUM — Desktop App Setup

## Prerequisites

- Python **3.9** or higher
- `pip` (bundled with Python)
- A Telegram account with **API ID** and **API Hash** from [my.telegram.org](https://my.telegram.org)
- The TG PRO QUANTUM backend must be running (see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md))

---

## Installation

### 1. Clone the repository
```bash
git clone https://github.com/your-org/tg_pro_quantum.git
cd tg_pro_quantum
```

### 2. Create a virtual environment (recommended)
```bash
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
.venv\Scripts\activate.bat       # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

---

## Configuration

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```dotenv
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
SECRET_KEY=your_jwt_secret
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/tg_quantum
REDIS_URL=redis://localhost:6379/0
```

> Obtain `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` from [https://my.telegram.org/apps](https://my.telegram.org/apps).

---

## Running the App

### GUI (Desktop)
```bash
python gui/main_window.py
```

### Admin Panel (CLI)
```bash
python admin_panel.py
```

### Backend API only
```bash
uvicorn main:app --reload --port 8000
```

---

## Troubleshooting

### `ModuleNotFoundError`
Ensure your virtual environment is activated and dependencies are installed:
```bash
pip install -r requirements.txt
```

### `Cannot connect to database`
- Verify PostgreSQL is running: `pg_isready -h localhost`
- Double-check `DATABASE_URL` in `.env`

### `Session file not found`
Sessions are stored in `./sessions/`. Make sure the directory exists and the app has write permission:
```bash
mkdir -p sessions
```

### `TELEGRAM_API_ID` not set
Confirm `.env` exists and contains valid values. The app will print a clear error on startup if credentials are missing.

### GUI does not open on Linux
Install the required system packages:
```bash
sudo apt install python3-tk
```

### Windows: `uvloop` install fails
`uvloop` is not supported on Windows. Install `requirements.txt` — the project auto-detects the platform and skips `uvloop` on Windows.
