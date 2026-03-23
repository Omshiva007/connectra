# Testing Guide

## Prerequisites

Install all dependencies (including dev/test extras):

```bash
pip install -r requirements.txt
```

## Running the Tests

### All tests

```bash
pytest -v
```

### With coverage report

```bash
pytest -v --cov=connectra_core --cov-report=term-missing
```

### HTML coverage report

```bash
pytest -v --cov=connectra_core --cov-report=html
# Open htmlcov/index.html in a browser
```

## Test Structure

| File | What it tests |
|------|---------------|
| `tests/test_database.py` | Cross-platform path resolution, table creation, CRUD |
| `tests/test_security.py` | Password encryption / decryption round-trips |
| `tests/test_validators.py` | Email, template-name, template and domain validation |
| `tests/test_email.py` | Email log persistence, SMTP call contract (mocked) |

## Environment Variables

Copy `.env.example` to `.env` and adjust as needed:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `CONNECTRA_DATA_DIR` | `~/.connectra` | Runtime data directory |
| `CONNECTRA_SECRET_KEY` | *(auto-generated)* | Fernet encryption key for stored passwords |
| `CONNECTRA_BACKEND_URL` | `http://localhost:8000` | FastAPI backend URL |

## Cross-Platform Notes

- All runtime files are stored under `~/.connectra` by default — no
  hardcoded Windows paths.
- Override the location with the `CONNECTRA_DATA_DIR` environment variable.
- Tests automatically redirect all I/O to a temporary directory so they
  never touch your real data.
