import json
from typing import List


def load_data(file_path: str) -> List[int]:
    """
    Загружает данные из файла.

    :param file_path: Путь к файлу
    :return: Список данных из файла
    """
    try:
        with open(file_path, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return []


def save_data(file_path: str, data: List[int]) -> None:
    """
    Сохраняет данные в файл.

    :param file_path: Путь к файлу
    :param data: Данные для сохранения
    """
    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)
