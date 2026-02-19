from helpers.config import get_settings, Settings

class BaseData:

    def __init__(self, client: object):
        self.client= client
        self.app_settings= get_settings()