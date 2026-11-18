"""저장과 불러오기. save.json은 진행 상황, collection.json은 엔딩 도감."""

import datetime
import json
import os

SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saves")


class SaveManager:
    def __init__(self, folder=SAVE_DIR):
        self.folder = folder
        os.makedirs(folder, exist_ok=True)
        self.save_path = os.path.join(folder, "save.json")
        self.collection_path = os.path.join(folder, "collection.json")

    def save(self, state):
        with open(self.save_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def load(self):
        """저장 파일이 없거나 깨졌으면 None."""
        try:
            with open(self.save_path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

    def delete_save(self):
        if os.path.exists(self.save_path):
            os.remove(self.save_path)

    def load_collection(self):
        """도감 파일이 깨졌으면 빈 도감으로 다시 시작."""
        try:
            with open(self.collection_path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}

    def save_collection(self, ending):
        collection = self.load_collection()
        collection.setdefault(ending, datetime.date.today().isoformat())
        with open(self.collection_path, "w", encoding="utf-8") as f:
            json.dump(collection, f, ensure_ascii=False, indent=2)
