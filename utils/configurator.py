import toml


class Config:
    """
    A class for handling configuration files.

    Args:
      config_file (str): The path to the configuration file.

    Attributes:
      config (dict): The parsed configuration data.

    Methods:
      __getitem__(section, key): Get the value of a specific key in a section of the configuration.

    """

    def __init__(self, config_file):
        self.config = toml.load(config_file)

    def __getitem__(self, section, key):
        return self.config[section][key]
