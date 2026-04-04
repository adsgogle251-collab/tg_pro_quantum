"""License management module"""
from .manager import (
    check_license,
    activate_license,
    load_session,
    save_session,
    clear_session,
    show_activation,
)
from .generator import LicenseGenerator, LICENSE_DB

__all__ = [
    "check_license",
    "activate_license",
    "load_session",
    "save_session",
    "clear_session",
    "show_activation",
    "LicenseGenerator",
    "LICENSE_DB",
]
