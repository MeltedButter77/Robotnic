import os, json
from config.paths import SETTINGS_PATH


def load_settings() -> dict:
    # Create settings file if it doesn't exist
    if not os.path.exists(SETTINGS_PATH):
        with open("default_settings.json", "r") as src:
            default_settings = json.load(src)
        with open(SETTINGS_PATH, "w") as dst:
            json.dump(default_settings, dst, indent=4)
        print(
            f"Created settings.json at {SETTINGS_PATH} from default_settings.json. "
            "Edit settings.json to change debug settings."
        )

    # Load settings
    with open(SETTINGS_PATH, "r") as f:
        settings = json.load(f)

    return settings
