import os

RUNTIME_ROOT = "C:/Connectra"

TEMPLATE_DIR = os.path.join(RUNTIME_ROOT, "templates")
DATA_DIR = os.path.join(RUNTIME_ROOT, "data")
LOG_DIR = os.path.join(RUNTIME_ROOT, "logs")


def initialize_runtime():

    os.makedirs(RUNTIME_ROOT, exist_ok=True)
    os.makedirs(TEMPLATE_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)