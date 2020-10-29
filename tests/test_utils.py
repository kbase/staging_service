import configparser

from dotenv import load_dotenv
import os


def bootstrap():
    test_env_0 = "../test.env"
    test_env_1 = "test.env"
    test_env_2 = "test/test.env"

    for item in [test_env_0, test_env_1, test_env_2]:
        try:
            load_dotenv(item, verbose=True)
        except Exception:
            pass


def bootstrap_config():
    bootstrap()
    config_filepath = os.environ["KB_DEPLOYMENT_CONFIG"]
    if not os.path.exists(config_filepath):
        raise FileNotFoundError(config_filepath)

    config = configparser.ConfigParser()
    config.read(config_filepath)
    return config
