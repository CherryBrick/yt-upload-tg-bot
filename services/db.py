import json
from typing import List

def load_data(file_path: str) -> List[int]:
    try:
        with open(file_path, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return []

def save_data(file_path: str, data: list) -> None:
    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)
