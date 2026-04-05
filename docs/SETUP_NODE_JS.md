# Node.js Setup Guide

## Why Node.js?

Node.js is required to run the **React Web Dashboard** at `http://localhost:3000`.

The desktop app (Tkinter) does NOT need Node.js - only the web dashboard does.

## Installation

### Windows

#### Option 1: Direct Download (Easiest)
1. Visit: https://nodejs.org/
2. Click **LTS** (Long Term Support) version
3. Download installer
4. Run installer (click Next → Next → Finish)
5. Restart terminal/command prompt
6. Verify installation:
   ```bash
   node --version
   npm --version
   ```

#### Option 2: Windows Package Manager
```bash
winget install OpenJS.NodeJS
```

#### Option 3: Chocolatey
```bash
choco install nodejs
```

### macOS

#### Using Homebrew
```bash
brew install node
```

#### Direct Download
1. Visit: https://nodejs.org/
2. Download macOS Installer
3. Run installer

### Linux

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install nodejs npm
```

#### Fedora
```bash
sudo dnf install nodejs npm
```

## Verify Installation

```bash
node --version    # Should show v18.x or v20.x
npm --version     # Should show 9.x or higher
```

## Starting Web Dashboard

After Node.js is installed:

```bash
cd frontend
npm install
npm start
```

This will:
✅ Install dependencies
✅ Start dev server
✅ Open http://localhost:3000 automatically

## Troubleshooting

### 'npm' is not recognized

**Solution:**
1. Close terminal completely
2. Open NEW terminal (administrator mode on Windows)
3. Restart computer (if still not working)
4. Reinstall Node.js

### Port 3000 already in use

**Solution:**
```bash
# Kill process using port 3000 (Windows)
netstat -ano | findstr :3000
taskkill /PID <PID_NUMBER> /F

# Kill process using port 3000 (Linux/macOS)
lsof -ti:3000 | xargs kill
```
