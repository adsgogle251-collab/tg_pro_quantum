# TG PRO QUANTUM — Web Dashboard Setup

## Prerequisites

- **Node.js 16+** (Node.js 18 LTS recommended) — [nodejs.org](https://nodejs.org)
- **npm 8+** (bundled with Node.js)
- The TG PRO QUANTUM backend must be running at `http://localhost:8000`

---

## Local Development

### 1. Install dependencies
```bash
cd frontend
npm install
```

### 2. Configure environment
```bash
cp .env.example .env.local
```

Edit `frontend/.env.local`:
```dotenv
VITE_API_URL=http://localhost:8000/api/v1
VITE_WS_URL=http://localhost:8000
```

### 3. Start the dev server
```bash
npm run dev
```

The dashboard will be available at **http://localhost:3000** with hot-reload enabled.

### 4. Build for production
```bash
npm run build
# Output in frontend/dist/
```

---

## Docker

Start only the frontend container:
```bash
docker-compose up frontend
```

Or start the full stack:
```bash
docker-compose up -d
```

Environment variables can be overridden in `docker-compose.yml`:
```yaml
environment:
  - VITE_API_URL=https://your-domain.com/api/v1
  - VITE_WS_URL=https://your-domain.com
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000/api/v1` | Backend REST API base URL |
| `VITE_WS_URL` | `http://localhost:8000` | WebSocket server base URL |

> Variables prefixed with `VITE_` are embedded at build time by Vite and exposed to the browser.

---

## Accessing the Dashboard

| Environment | URL |
|---|---|
| Local dev | http://localhost:3000 |
| Docker | http://localhost:3000 |
| Production (HTTPS) | https://your-domain.com |

---

## Troubleshooting

### `ENOENT: package.json not found`
Run `npm install` from inside the `frontend/` directory, not the repo root.

### API requests fail (CORS error)
Ensure `ALLOWED_ORIGINS` in the backend `.env` includes the dashboard URL, e.g.:
```dotenv
ALLOWED_ORIGINS=http://localhost:3000
```

### WebSocket disconnects immediately
Verify `VITE_WS_URL` points to the running backend and no firewall blocks the port.

### `Port 3000 already in use`
Change the port in `vite.config.ts`:
```ts
server: { port: 3001 }
```
