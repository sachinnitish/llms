import json
import os
from threading import Lock

class StateManager:
    def __init__(self, state_file=None):
        if state_file is None:
            # Resolve to <root>/data/state.json consistently
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(base_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            self.state_file = os.path.join(data_dir, "state.json")
        else:
            self.state_file = state_file
            
        self.lock = Lock()
        self._load_state()

    def _load_state(self):
        if not os.path.exists(self.state_file):
            self.state = {}
        else:
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    self.state = json.load(f)
            except Exception:
                self.state = {}

    def save_state(self):
        with self.lock:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2)

    def get_url_state(self, url):
        return self.state.get(url, {})

    def update_url_state(self, url, data):
        with self.lock:
            if url not in self.state:
                self.state[url] = {}
            self.state[url].update(data)
        self.save_state()

    def get_all_state(self):
        return self.state

    def get_all_completed(self):
        return {k: v for k, v in self.state.items() if v.get("status") == "completed"}

    def reset_state(self):
        with self.lock:
            self.state = {}
        self.save_state()
