"""
core/adaptive_delay.py - Adaptive delay system for join flood detection
"""
import time
from threading import Lock
from typing import Optional


class AdaptiveDelay:
    """
    Manages join delay with adaptive flood detection.

    Delay progression on flood:  base → 5 → 10 → 30 (exponential)
    Auto-reset on consecutive successes.

    Presets:
        conservative  – 30 s base
        normal        – 3 s  base
        aggressive    – 1 s  base
    """

    PRESETS = {
        "conservative": 30.0,
        "normal": 3.0,
        "aggressive": 1.0,
    }

    # Steps: base, ×2, ×3, ×6  (relative multipliers applied to base)
    _FLOOD_STEPS = [1, 2, 4, 10]

    def __init__(self, preset: str = "normal"):
        self._lock = Lock()
        self._preset = preset
        self._base = self.PRESETS.get(preset, 3.0)
        self._step_index = 0          # index into _FLOOD_STEPS
        self._consecutive_success = 0
        self._success_reset_threshold = 5  # successes before step back down

    # ─────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────

    @property
    def current_delay(self) -> float:
        with self._lock:
            return self._base * self._FLOOD_STEPS[self._step_index]

    @property
    def preset(self) -> str:
        return self._preset

    def set_preset(self, preset: str):
        """Change preset (conservative / normal / aggressive)."""
        with self._lock:
            self._preset = preset
            self._base = self.PRESETS.get(preset, 3.0)
            self._step_index = 0
            self._consecutive_success = 0

    def set_custom_base(self, seconds: float):
        """Override base delay with a custom value."""
        with self._lock:
            self._base = max(0.5, float(seconds))
            self._step_index = 0
            self._consecutive_success = 0

    def on_success(self):
        """Call after a successful join."""
        with self._lock:
            self._consecutive_success += 1
            if self._consecutive_success >= self._success_reset_threshold and self._step_index > 0:
                self._step_index -= 1
                self._consecutive_success = 0

    def on_flood(self, wait_seconds: Optional[float] = None):
        """Call when a flood-wait / rate-limit error is received."""
        with self._lock:
            self._consecutive_success = 0
            self._step_index = min(self._step_index + 1, len(self._FLOOD_STEPS) - 1)
            if wait_seconds and wait_seconds > self.current_delay:
                # Telegram told us to wait longer – honour it this cycle
                self._base = max(self._base, wait_seconds / self._FLOOD_STEPS[self._step_index])

    def on_failure(self):
        """Call on non-flood failure (optional – slightly increases caution)."""
        with self._lock:
            self._consecutive_success = 0

    def wait(self):
        """Block for the current computed delay."""
        time.sleep(self.current_delay)

    def describe(self) -> str:
        return f"{self.current_delay:.1f}s ({self._preset})"


# Singleton used by join_engine
adaptive_delay = AdaptiveDelay()

__all__ = ["AdaptiveDelay", "adaptive_delay"]
