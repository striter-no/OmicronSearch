import json
import os

def load_json(filename):
    with open(filename, 'r') as f:
        data = json.load(f)
    return data

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)


class DataBase:
    def __init__(self, path: str) -> None:
        self.path = path
        if not os.path.exists(path):
            with open(path, "w") as f:
                json.dump({}, f)

    def get(self, key):
        data = load_json(self.path)
        return data.get(key)
    
    def set(self, key, value) -> None:
        data = load_json(self.path)
        data[key] = value
        save_json(self.path, data)
    
    def exists(self, key) -> bool:
        data = load_json(self.path)
        return key in data
    
    def all(self) -> dict:
        return load_json(self.path)