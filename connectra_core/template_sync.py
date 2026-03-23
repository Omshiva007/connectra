import os
import shutil
from pathlib import Path

# where admin publishes templates
ADMIN_TEMPLATE_FOLDER = Path(os.environ.get("CONNECTRA_HOME", Path.home() / ".connectra")) / "templates"
LOCAL_TEMPLATE_FOLDER = "templates"


def sync_templates():

    if not ADMIN_TEMPLATE_FOLDER.exists():
        return

    if not os.path.exists(LOCAL_TEMPLATE_FOLDER):
        os.makedirs(LOCAL_TEMPLATE_FOLDER)

    # remove old templates
    for file in os.listdir(LOCAL_TEMPLATE_FOLDER):

        if file.endswith(".json"):
            os.remove(os.path.join(LOCAL_TEMPLATE_FOLDER, file))

    # copy admin templates
    for file in ADMIN_TEMPLATE_FOLDER.iterdir():

        if file.name.endswith(".json"):

            dst = os.path.join(LOCAL_TEMPLATE_FOLDER, file.name)

            shutil.copy(str(file), dst)
