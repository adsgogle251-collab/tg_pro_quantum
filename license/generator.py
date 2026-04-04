"""License Generator - Admin panel license key generation"""
import json
import random
import string
from datetime import datetime, timedelta
from pathlib import Path

LICENSE_DB = Path(__file__).parent.parent / "data" / "license_database.json"

_TIERS = {"free", "starter", "pro", "enterprise", "owner"}


def _load_db() -> dict:
    """Load the license database, creating it if it does not exist."""
    LICENSE_DB.parent.mkdir(parents=True, exist_ok=True)
    if LICENSE_DB.exists():
        try:
            with open(LICENSE_DB, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"licenses": [], "customers": []}


def _save_db(db: dict) -> bool:
    """Persist the license database to disk."""
    try:
        LICENSE_DB.parent.mkdir(parents=True, exist_ok=True)
        with open(LICENSE_DB, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2)
        return True
    except Exception:
        return False


def _random_segment(length: int = 4) -> str:
    """Return a random uppercase alphanumeric segment."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


class LicenseGenerator:
    """Generate and manage TG PRO QUANTUM license keys."""

    def generate_key(self, email: str, days: int, tier: str) -> dict:
        """Generate a new license key.

        Args:
            email: Customer email address
            days: License validity in days
            tier: License tier (free/starter/pro/enterprise/owner)

        Returns:
            dict: {"key": str, "email": str, "tier": str, "expires": str, "issued_at": str}
        """
        if tier not in _TIERS:
            tier = "pro"

        seg1 = _random_segment()
        seg2 = _random_segment()
        seg3 = _random_segment()
        expiry_date = (datetime.now() + timedelta(days=days)).strftime("%Y%m%d")
        # Key embeds expiry as YYYYMMDD (no dashes) for a compact key format.
        key = f"TGPRO-{seg1}-{seg2}-{seg3}-{expiry_date}"

        issued_at = datetime.now().isoformat()
        expires = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

        record = {
            "key": key,
            "email": email,
            "tier": tier,
            "issued_at": issued_at,
            "expires": expires,
            "valid": True,
            "status": "active",
            "activated": False,
            "activated_at": None,
            "hwid": None,
        }

        db = _load_db()
        db["licenses"].append(record)

        # Update or add customer entry
        customer = next((c for c in db["customers"] if c.get("email") == email), None)
        if customer is None:
            db["customers"].append({"email": email, "tier": tier, "created": issued_at})
        _save_db(db)

        return {
            "key": key,
            "email": email,
            "tier": tier,
            "expires": expires,
            "issued_at": issued_at,
        }

    def get_all_licenses(self) -> list:
        """Return all generated licenses.

        Returns:
            list: List of license dicts
        """
        db = _load_db()
        return db.get("licenses", [])

    def extend_license(self, key: str, days: int) -> bool:
        """Extend the expiry of an existing license.

        Args:
            key: License key to extend
            days: Number of additional days

        Returns:
            bool: True if extended successfully
        """
        db = _load_db()
        for lic in db["licenses"]:
            if lic.get("key") == key:
                try:
                    current_expires = datetime.strptime(lic["expires"], "%Y-%m-%d")
                except ValueError:
                    current_expires = datetime.now()
                new_expires = current_expires + timedelta(days=days)
                lic["expires"] = new_expires.strftime("%Y-%m-%d")
                return _save_db(db)
        return False

    def revoke_license(self, key: str) -> bool:
        """Revoke an existing license.

        Args:
            key: License key to revoke

        Returns:
            bool: True if revoked successfully
        """
        db = _load_db()
        for lic in db["licenses"]:
            if lic.get("key") == key:
                lic["valid"] = False
                lic["status"] = "revoked"
                return _save_db(db)
        return False
