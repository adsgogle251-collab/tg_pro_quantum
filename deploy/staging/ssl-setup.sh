#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# TG PRO QUANTUM – SSL Certificate Setup (Staging)
# Generates a self-signed certificate valid 365 days for staging domain.
# Usage: ./ssl-setup.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SSL_DIR="${SCRIPT_DIR}/ssl"
DOMAIN="${SSL_DOMAIN:-staging.tg-pro-quantum.app}"
DAYS=365
CERT="${SSL_DIR}/staging.crt"
KEY="${SSL_DIR}/staging.key"

echo "=== TG PRO QUANTUM – SSL Setup (Staging) ==="
echo "Domain : ${DOMAIN}"
echo "Output : ${SSL_DIR}"
echo ""

# ── Create SSL directory ─────────────────────────────────────────────────────
mkdir -p "${SSL_DIR}"
chmod 700 "${SSL_DIR}"

# ── Generate private key ─────────────────────────────────────────────────────
echo "[1/5] Generating private key..."
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:4096 -out "${KEY}"
chmod 600 "${KEY}"
echo "  ✅ Private key generated: ${KEY}"

# ── Generate CSR config ──────────────────────────────────────────────────────
CSR_CONF=$(mktemp /tmp/ssl-csr-XXXXXX.conf)
trap 'rm -f "${CSR_CONF}"' EXIT
cat > "${CSR_CONF}" <<EOF
[req]
default_bits       = 4096
prompt             = no
default_md         = sha256
req_extensions     = req_ext
distinguished_name = dn

[dn]
C  = ID
ST = Jakarta
L  = Jakarta
O  = TG PRO QUANTUM
OU = Staging
CN = ${DOMAIN}

[req_ext]
subjectAltName = @alt_names

[alt_names]
DNS.1 = ${DOMAIN}
DNS.2 = api-staging.tg-pro-quantum.app
DNS.3 = monitoring-staging.tg-pro-quantum.app
DNS.4 = logs-staging.tg-pro-quantum.app
DNS.5 = localhost
IP.1  = 127.0.0.1
EOF

# ── Generate self-signed certificate ─────────────────────────────────────────
echo "[2/5] Generating self-signed certificate (${DAYS} days)..."
openssl req -new -x509 \
    -key  "${KEY}" \
    -out  "${CERT}" \
    -days "${DAYS}" \
    -config "${CSR_CONF}" \
    -extensions req_ext
chmod 644 "${CERT}"
echo "  ✅ Certificate generated: ${CERT}"

# ── Verify certificate ───────────────────────────────────────────────────────
echo "[3/5] Verifying certificate..."
openssl x509 -in "${CERT}" -text -noout | grep -E "Subject:|Not After|DNS:"
echo "  ✅ Certificate verified"

# ── Test SSL configuration ───────────────────────────────────────────────────
echo "[4/5] Checking certificate validity..."
EXPIRY=$(openssl x509 -in "${CERT}" -noout -enddate | cut -d= -f2)
echo "  Certificate expires: ${EXPIRY}"
openssl verify -CAfile "${CERT}" "${CERT}" 2>/dev/null && echo "  ✅ Self-signed cert validates OK" || true

# ── Summary ──────────────────────────────────────────────────────────────────
echo "[5/5] Summary:"
echo "  Certificate : ${CERT}"
echo "  Private key : ${KEY}"
echo "  Domains     : ${DOMAIN}, api-staging.tg-pro-quantum.app"
echo "  Valid for   : ${DAYS} days"
echo "  Expiry      : ${EXPIRY}"

echo ""
echo "=== SSL setup complete ✅ ==="
echo ""
echo "NOTE: Self-signed certificates trigger browser warnings."
echo "      For production, use Let's Encrypt or a commercial CA."
