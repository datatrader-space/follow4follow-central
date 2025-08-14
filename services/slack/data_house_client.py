import json
import requests

class DataHouseClient:
    def __init__(self, api_key, base_url):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def provide(self, payload ):
        url = f"{self.base_url}/provide/"
        # payload = {"object_type": object_type}
        

        try:
            response = requests.post(url, data=json.dumps(payload))
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error providing data: {e}")
            raise

    def consume(self, payload):
        url = f"{self.base_url}/consume/"
        try:
            response = requests.post(url, headers=self.headers, data=json.dumps(payload))
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error consuming data: {e}")
            raise
