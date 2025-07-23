class JuniperHandler:
    def push_config(self, cml_url, lab_id, node_id, headers, config_text):
        print(f"Juniper config would be applied to {node_id}")
