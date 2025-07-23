import time
import requests


class CiscoHandler:
    def push_config(self, cml_url, lab_id, node_id, headers, config_text):
        requests.patch(
            f"{cml_url}/api/v0/labs/{lab_id}/nodes/{node_id}",
            json={"configuration": config_text},
            headers=headers,
            verify=False
        )
        time.sleep(2)
        requests.put(
            f"{cml_url}/api/v0/labs/{lab_id}/nodes/{node_id}/state/start",
            headers=headers,
            verify=False
        )
