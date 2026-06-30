"""Runtime folder initialization for the Admin desktop app."""

from connectra_core.config import RUNTIME_ROOT, TEMPLATE_DIR, DATA_DIR, LOG_DIR


def initialize_runtime():
    """Create admin app runtime folders if they are missing."""
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
