####
# Avrae API Handler
###

import requests

class Avrae:
    def __init__(self, token: str):
        self.token = token