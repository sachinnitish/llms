import json
import os
from threading import Lock

class ConfigManager:
    def __init__(self, config_file=None):
        if config_file is None:
            # Resolve to <root>/data/config.json consistently
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(base_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            self.config_file = os.path.join(data_dir, "config.json")
        else:
            self.config_file = config_file
            
        self.lock = Lock()
        self._load_config()

    def _load_config(self):
        if not os.path.exists(self.config_file):
            self.config = {}
        else:
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            except Exception:
                self.config = {}

    def save_config(self):
        with self.lock:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)

    def get_value(self, key, default=""):
        return self.config.get(key, default)

    def set_value(self, key, value):
        with self.lock:
            self.config[key] = value
        self.save_config()
