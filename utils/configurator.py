import os
import toml


class Config:
    def __init__(self, config_file):
        self.config = toml.load(config_file)

    def get(self, key, default=None):
        if "." in key:
            section, key = key.split(".")
            # Try to get the value from the TOML file
            value = self.config.get(section, {}).get(key)

        # If the value is not found, try to get it from the environment variables
        else:
            value = os.getenv(key, default)

        return value
