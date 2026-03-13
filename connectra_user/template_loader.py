import os
import json

TEMPLATE_DIR = "templates"


def load_templates():

    templates = []

    if not os.path.exists(TEMPLATE_DIR):
        return templates

    for file in os.listdir(TEMPLATE_DIR):

        if file.endswith(".json"):

            path = os.path.join(TEMPLATE_DIR, file)

            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                templates.append(data)

    return templates