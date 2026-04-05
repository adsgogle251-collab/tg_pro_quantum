# TG PRO QUANTUM — User Guide

## Table of Contents
1. [Getting Started](#getting-started)
2. [Login & Authentication](#login--authentication)
3. [Dashboard Overview](#dashboard-overview)
4. [Managing Accounts](#managing-accounts)
5. [Creating Campaigns](#creating-campaigns)
6. [Broadcasting Messages](#broadcasting-messages)
7. [Scraping Members](#scraping-members)
8. [Finder Feature](#finder-feature)
9. [Analytics](#analytics)
10. [Settings](#settings)
11. [Keyboard Shortcuts](#keyboard-shortcuts)

---

## Getting Started

### Prerequisites
- Python 3.9 or higher
- PostgreSQL 14+
- Redis 7+
- A Telegram API ID and API Hash from [my.telegram.org](https://my.telegram.org)

### Installation (Docker — Recommended)
```bash
git clone https://github.com/your-org/tg_pro_quantum.git
cd tg_pro_quantum
cp .env.example .env          # fill in your Telegram API credentials
docker-compose up -d
```

The backend API will be available at `http://localhost:8000` and the web dashboard at `http://localhost:3000`.

### Installation (Manual)
```bash
pip install -r requirements.txt
# configure .env then:
python main.py
```

---

## Login & Authentication

1. Open the web dashboard at `http://localhost:3000`.
2. Enter your admin **username** and **password**.
3. On first launch, register via `POST /api/v1/auth/register` or the registration page.
4. After login, a **JWT Bearer token** is issued and stored in your browser session.
5. Tokens expire after 24 hours; you will be redirected to the login page automatically.

### Desktop App Login
Launch the desktop GUI, enter the same credentials, and click **Login**. The app stores the token locally for the session.

---

## Dashboard Overview

The main dashboard displays a real-time summary of:

| Panel | Description |
|---|---|
| **Active Accounts** | Number of Telegram accounts currently connected |
| **Campaigns** | Total / active / completed campaigns |
| **Broadcasts Today** | Messages sent in the last 24 hours |
| **Scraping Jobs** | Running or queued scrape tasks |
| **Analytics Sparkline** | 7-day message delivery trend |

Use the left sidebar to navigate between sections. Click the **⚡** logo to return to the dashboard at any time.

---

## Managing Accounts

### Adding a Telegram Account
1. Go to **Accounts → Add Account**.
2. Enter the phone number (international format, e.g. `+14155552671`).
3. Click **Send Code** — Telegram will send an OTP to the device.
4. Enter the OTP in the **Verification Code** field and click **Verify**.
5. If two-step verification (2FA) is enabled, enter your cloud password when prompted.
6. The account status will change to **Active** once connected.

### Account States
- **Active** — connected and ready to use.
- **Flood Wait** — rate-limited by Telegram; shows remaining wait time.
- **Banned** — account has been restricted by Telegram.
- **Disconnected** — session expired; re-verify to reconnect.

### Removing an Account
Click the **⋮** menu next to the account and choose **Remove**. This deletes the session file and removes the account from the database.

---

## Creating Campaigns

1. Navigate to **Campaigns → New Campaign**.
2. Fill in:
   - **Name** — a descriptive label.
   - **Type** — `DM`, `Group Broadcast`, or `Scrape`.
   - **Message Template** — supports `{first_name}`, `{username}` placeholders.
   - **Media** — optionally attach an image or file.
   - **Schedule** — immediate or a future datetime.
3. Click **Save Campaign**.

Campaigns can be cloned via the **Duplicate** action.

---

## Broadcasting Messages

### Direct Messages (DM)
1. Open a campaign of type **DM**.
2. Select the target list (scraped members or a CSV upload).
3. Choose the **Sender Account(s)** — distributing load across multiple accounts reduces flood risk.
4. Set the **delay range** (e.g. 3–8 seconds between messages).
5. Click **Start Broadcast**.

### Group Broadcast
1. Open a campaign of type **Group Broadcast**.
2. Add target group usernames or links.
3. Configure the message and delay.
4. Click **Start Broadcast**.

### Monitoring Progress
The broadcast panel shows:
- Messages sent / failed / pending
- Live log stream
- Per-account delivery stats

Click **Pause** or **Stop** at any time.

---

## Scraping Members

1. Go to **Scraper → New Scrape Job**.
2. Enter the target group username or invite link.
3. Choose **Scrape Mode**:
   - **All Members** — exports the full member list.
   - **Recent Active** — only members who have been active recently.
   - **Admins Only** — exports admin accounts.
4. Set the **limit** (0 = no limit).
5. Click **Start Scraping**.

Results are exported as CSV and stored in the database. Go to **Scraper → Results** to download.

---

## Finder Feature

The **Finder** searches public Telegram groups and channels by keyword.

1. Navigate to **Finder → Search**.
2. Enter keywords (e.g. `crypto trading`, `nft marketplace`).
3. Set the maximum number of results.
4. Click **Search**.

Found groups appear in a table with **member count**, **activity rating**, and a **Scrape** shortcut button.

---

## Analytics

The **Analytics** dashboard provides:

- **Message Volume** — hourly / daily / weekly breakdown.
- **Delivery Rate** — sent vs failed per campaign.
- **Account Health** — flood events, bans, and active sessions.
- **Top Performing Campaigns** — ranked by delivery rate.

Use the date range picker to filter. Export data as CSV with the **Export** button.

---

## Settings

| Setting | Description |
|---|---|
| **API Credentials** | Telegram API ID & Hash |
| **Default Delay** | Global delay between messages (seconds) |
| **Max Accounts per Broadcast** | Concurrency limit |
| **Session Directory** | Path where `.session` files are stored |
| **Log Level** | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| **Theme** | Light / Dark / System |

---

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl + D` | Go to Dashboard |
| `Ctrl + A` | Open Accounts |
| `Ctrl + C` | Open Campaigns |
| `Ctrl + B` | Open Broadcasts |
| `Ctrl + S` | Open Scraper |
| `Ctrl + F` | Open Finder |
| `Ctrl + N` | New item (context-sensitive) |
| `Ctrl + ,` | Open Settings |
| `Esc` | Close modal / cancel |
| `?` | Show shortcut help overlay |
