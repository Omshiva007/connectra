import os
import json
import shutil

ADMIN_TEMPLATE_DIR = os.path.join(os.getcwd(), "templates")

RUNTIME_TEMPLATE_DIR = r"C:\Connectra\templates"


def ensure_dirs():

    if not os.path.exists(ADMIN_TEMPLATE_DIR):
        os.makedirs(ADMIN_TEMPLATE_DIR)

    if not os.path.exists(RUNTIME_TEMPLATE_DIR):
        os.makedirs(RUNTIME_TEMPLATE_DIR)


def list_templates():

    ensure_dirs()

    templates = []

    for file in os.listdir(ADMIN_TEMPLATE_DIR):

        if file.endswith(".json"):
            templates.append(file.replace(".json", ""))

    return templates


def load_template(name):

    path = os.path.join(ADMIN_TEMPLATE_DIR, name + ".json")

    with open(path, "r") as f:
        return json.load(f)


def save_template(name, subject, body):

    ensure_dirs()

    path = os.path.join(ADMIN_TEMPLATE_DIR, name + ".json")

    data = {
        "name": name,
        "subject": subject,
        "body": body
    }

    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def delete_template(name):

    path = os.path.join(ADMIN_TEMPLATE_DIR, name + ".json")

    if os.path.exists(path):
        os.remove(path)


def publish_templates():

    ensure_dirs()

    for file in os.listdir(ADMIN_TEMPLATE_DIR):

        if file.endswith(".json"):

            src = os.path.join(ADMIN_TEMPLATE_DIR, file)
            dst = os.path.join(RUNTIME_TEMPLATE_DIR, file)

            shutil.copy(src, dst)