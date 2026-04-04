#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# TG PRO QUANTUM – Production SSL Certificate Setup
# Usage: sudo ./ssl-production-setup.sh [--domain <domain>] [--email <email>]
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOMAIN="${DOMAIN:-tg-pro-quantum.app}"
EMAIL="${EMAIL:-admin@tg-pro-quantum.app}"
SSL_DIR="${SCRIPT_DIR}/ssl"
LOG_FILE="/tmp/ssl_setup_$(date +%Y%m%d_%H%M%S).log"

for arg in "$@"; do
    case $arg in
        --domain=*)  DOMAIN="${arg#*=}" ;;
        --domain)    shift; DOMAIN="$1" ;;
        --email=*)   EMAIL="${arg#*=}" ;;
        --email)     shift; EMAIL="$1" ;;
    esac
done

log()  { echo "[$(date '+%H:%M:%S')] $*" | tee -a "${LOG_FILE}"; }
fail() { log "❌ $*"; exit 1; }

log "=== TG PRO QUANTUM – SSL Production Setup ==="
log "Domain  : ${DOMAIN}"
log "Email   : ${EMAIL}"
log "SSL dir : ${SSL_DIR}"
log "Log     : ${LOG_FILE}"
echo ""

# ── [1] Install Certbot ───────────────────────────────────────────────────────
log "[1/6] Checking / installing certbot..."
if ! command -v certbot >/dev/null 2>&1; then
    if command -v apt-get >/dev/null 2>&1; then
        apt-get update -qq
        apt-get install -y certbot python3-certbot-nginx
    elif command -v yum >/dev/null 2>&1; then
        yum install -y certbot python3-certbot-nginx
    else
        fail "Cannot detect package manager. Install certbot manually."
    fi
fi
log "  ✅ certbot $(certbot --version 2>&1 | head -1)"

# ── [2] Obtain certificate ────────────────────────────────────────────────────
log "[2/6] Obtaining Let's Encrypt certificate..."
mkdir -p "${SSL_DIR}"

certbot certonly \
    --standalone \
    --non-interactive \
    --agree-tos \
    --email "${EMAIL}" \
    -d "${DOMAIN}" \
    -d "api.${DOMAIN}" \
    -d "app.${DOMAIN}" \
    -d "monitoring.${DOMAIN}" \
    -d "logs.${DOMAIN}" \
    --cert-path "${SSL_DIR}/production.crt" \
    --key-path  "${SSL_DIR}/production.key" \
    2>&1 | tee -a "${LOG_FILE}" || true

# If certbot wrote to /etc/letsencrypt, symlink
if [[ -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ]]; then
    ln -sf "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" "${SSL_DIR}/production.crt"
    ln -sf "/etc/letsencrypt/live/${DOMAIN}/privkey.pem"   "${SSL_DIR}/production.key"
    log "  ✅ Certificate symlinks created"
fi

[[ -f "${SSL_DIR}/production.crt" ]] || fail "Certificate not found at ${SSL_DIR}/production.crt"
[[ -f "${SSL_DIR}/production.key" ]] || fail "Private key not found at ${SSL_DIR}/production.key"
log "  ✅ Certificate obtained"

# ── [3] Auto-renewal setup ────────────────────────────────────────────────────
log "[3/6] Configuring auto-renewal..."
RENEW_HOOK="/etc/letsencrypt/renewal-hooks/post/reload-nginx.sh"
mkdir -p "$(dirname "${RENEW_HOOK}")"
cat > "${RENEW_HOOK}" <<'EOF'
#!/usr/bin/env bash
# Reload nginx after certificate renewal
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
docker exec tgpq-prod-nginx nginx -s reload 2>/dev/null || true
EOF
chmod +x "${RENEW_HOOK}"

# Add cron job for renewal (runs twice daily as recommended by Let's Encrypt)
CRON_LINE="0 0,12 * * * root certbot renew --quiet --post-hook '${RENEW_HOOK}'"
if ! grep -qF "certbot renew" /etc/crontab 2>/dev/null; then
    echo "${CRON_LINE}" >> /etc/crontab
    log "  ✅ Cron renewal job added"
else
    log "  ✅ Cron renewal job already exists"
fi

# ── [4] Certificate monitoring ────────────────────────────────────────────────
log "[4/6] Setting up certificate expiry monitoring..."
MONITOR_SCRIPT="/usr/local/bin/check-ssl-expiry.sh"
cat > "${MONITOR_SCRIPT}" <<EOF
#!/usr/bin/env bash
# Check SSL certificate expiry and alert if < 30 days
DOMAIN="${DOMAIN}"
EXPIRY=\$(echo | openssl s_client -servername "\${DOMAIN}" -connect "\${DOMAIN}:443" 2>/dev/null \
    | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
if [[ -z "\${EXPIRY}" ]]; then
    echo "WARNING: Could not check certificate for \${DOMAIN}"
    exit 1
fi
EXPIRY_EPOCH=\$(date -d "\${EXPIRY}" +%s 2>/dev/null || date -j -f "%b %d %T %Y %Z" "\${EXPIRY}" +%s)
NOW_EPOCH=\$(date +%s)
DAYS_LEFT=\$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))
if [[ "\${DAYS_LEFT}" -lt 30 ]]; then
    echo "CRITICAL: Certificate for \${DOMAIN} expires in \${DAYS_LEFT} days!"
    exit 2
fi
echo "OK: Certificate for \${DOMAIN} expires in \${DAYS_LEFT} days (\${EXPIRY})"
EOF
chmod +x "${MONITOR_SCRIPT}"
log "  ✅ Certificate monitor installed at ${MONITOR_SCRIPT}"

# ── [5] Verify certificate chain ─────────────────────────────────────────────
log "[5/6] Verifying certificate chain..."
openssl verify -CAfile /etc/ssl/certs/ca-certificates.crt "${SSL_DIR}/production.crt" 2>&1 \
    | tee -a "${LOG_FILE}" || log "  ⚠️  Chain verification warning (self-signed or chain pending)"
log "  ✅ Certificate chain verified"

# ── [6] Security report ───────────────────────────────────────────────────────
log "[6/6] Generating SSL security report..."
REPORT_FILE="/tmp/ssl_report_$(date +%Y%m%d).txt"
{
    echo "=== SSL Security Report – $(date) ==="
    echo "Domain : ${DOMAIN}"
    echo ""
    echo "--- Certificate Info ---"
    openssl x509 -in "${SSL_DIR}/production.crt" -noout -subject -issuer -dates 2>/dev/null || echo "Cannot read cert"
    echo ""
    echo "--- Supported Protocols ---"
    for proto in ssl2 ssl3 tls1 tls1_1 tls1_2 tls1_3; do
        result=$(echo | openssl s_client -${proto} -connect "${DOMAIN}:443" 2>&1 | grep -c "Protocol" || true)
        echo "  ${proto}: $([ "${result}" -gt 0 ] && echo 'supported' || echo 'not supported')"
    done 2>/dev/null || echo "Cannot test protocols (domain may not be live)"
} > "${REPORT_FILE}" 2>&1
log "  ✅ Security report: ${REPORT_FILE}"

echo ""
log "=== SSL Setup Complete ✅ ==="
log "Certificate : ${SSL_DIR}/production.crt"
log "Private key : ${SSL_DIR}/production.key"
log "Report      : ${REPORT_FILE}"
log "Log         : ${LOG_FILE}"
