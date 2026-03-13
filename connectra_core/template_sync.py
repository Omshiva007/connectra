import os
import shutil

ADMIN_TEMPLATE_FOLDER = "D:/ConnectraTemplates"
LOCAL_TEMPLATE_FOLDER = "templates"


def sync_templates():

    if not os.path.exists(ADMIN_TEMPLATE_FOLDER):
        return

    if not os.path.exists(LOCAL_TEMPLATE_FOLDER):
        os.makedirs(LOCAL_TEMPLATE_FOLDER)

    # remove old templates
    for file in os.listdir(LOCAL_TEMPLATE_FOLDER):

        if file.endswith(".json"):
            os.remove(os.path.join(LOCAL_TEMPLATE_FOLDER, file))

    # copy admin templates
    for file in os.listdir(ADMIN_TEMPLATE_FOLDER):

        if file.endswith(".json"):

            src = os.path.join(ADMIN_TEMPLATE_FOLDER, file)
            dst = os.path.join(LOCAL_TEMPLATE_FOLDER, file)

            shutil.copy(src, dst)