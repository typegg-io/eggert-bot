import os


def get_command_groups():
    groups = []
    for dir in os.listdir("./commands"):
        if not dir.startswith("_") and os.path.isdir(os.path.join("./commands", dir)):
            groups.append(dir)

    return groups
