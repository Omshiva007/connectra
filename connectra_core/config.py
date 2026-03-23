import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Base directory for all runtime data.  Can be overridden via the
# CONNECTRA_DATA_DIR environment variable so the app works on every
# platform (Windows, macOS, Linux).
RUNTIME_ROOT: Path = Path(
    os.environ.get("CONNECTRA_DATA_DIR", str(Path.home() / ".connectra"))
)

DATA_DIR: Path = RUNTIME_ROOT / "data"
TEMPLATE_DIR: Path = RUNTIME_ROOT / "templates"
LOG_DIR: Path = RUNTIME_ROOT / "logs"

BACKEND_BASE_URL: str = os.environ.get(
    "CONNECTRA_BACKEND_URL", "http://localhost:8000"
)

