import json
import threading
import os

from typing import Dict, List, Any
from filelock import FileLock


class JSONDocumentDB:
    """A lightweight JSON document database with thread-safe operations."""
    _instance = None
    _instance_lock = threading.Lock()

    def __new__(cls):
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super(JSONDocumentDB, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self.file_path: str = "/opt/brain/db.json"
        self.lock = threading.Lock()
        self.file_lock: FileLock = FileLock(f"{self.file_path}.lock")
        self._ensure_file_exists()
        self._cache = None
        self._initialized: bool = True

    def _ensure_file_exists(self) -> None:
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w") as f:
                json.dump({}, f)

    def _load_db(self) -> Dict[str, List[Dict[str, Any]]]:
        if self._cache is not None:
            return self._cache
        with self.file_lock:
            self._ensure_file_exists()
            with open(self.file_path, "r") as f:
                self._cache = json.load(f)
        return self._cache

    def _save_db(self, data: Dict[str, List[Dict[str, Any]]]) -> None:
        with self.file_lock:
            self._ensure_file_exists()
            with open(self.file_path, "w") as f:
                json.dump(data, f, indent=2)
        self._cache = data

    def insert(self, collection: str, document: Dict[str, Any]) -> None:
        with self.lock:
            db = self._load_db()
            if collection not in db:
                db[collection] = []
            db[collection].append(document)
            self._save_db(db)

    def find(self, collection: str, filter_dict=None) -> List[Dict[str, Any]]:
        with self.lock:
            db = self._load_db()
            return [doc for doc in db.get(collection, []) if self._match(doc, filter_dict)]

    def find_one(self, collection: str, filter_dict=None) -> Dict[str, Any]:
        """Find a single document in the collection matching the filter."""
        results = self.find(collection, filter_dict)
        if not results:
            raise ValueError(f"No entry found matching {filter_dict}")
        if len(results) > 1:
            raise ValueError(
                f"Expected 1 document, but found {len(results)} matching {filter_dict}")
        return results[0]

    def update(self, collection: str, filter_dict: Dict[str, Any],
               update_dict: Dict[str, Any]) -> int:
        with self.lock:
            db = self._load_db()
            updated = 0
            for doc in db.get(collection, []):
                if self._match(doc, filter_dict):
                    doc.update(update_dict)
                    updated += 1
            if updated > 0:
                self._save_db(db)
            return updated

    def update_one(self, collection: str, filter_dict: Dict[str, Any],
                   update_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Update the first matching document in the collection."""
        with self.lock:
            db = self._load_db()
            matched_docs = [doc for doc in db.get(collection, []) if self._match(doc, filter_dict)]

            if not matched_docs:
                raise ValueError(f"No document found in '{collection}' matching {filter_dict}")

            if len(matched_docs) > 1:
                raise ValueError(
                    f"Expected 1 document, but found {len(matched_docs)} in '{collection}'")

            original_doc = matched_docs[0].copy()
            matched_docs[0].update(update_dict)
            self._save_db(db)

            return original_doc

    def delete(self, collection: str, filter_dict: Dict[str, Any]) -> int:
        with self.lock:
            db = self._load_db()
            original_len = len(db.get(collection, []))
            db[collection] = [doc for doc in db.get(
                collection, []) if not self._match(doc, filter_dict)]
            deleted = original_len - len(db[collection])
            if deleted > 0:
                self._save_db(db)
            return deleted

    def delete_one(self, collection: str, filter_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Delete the first matching document in the collection."""
        with self.lock:
            db = self._load_db()
            matched_docs = [doc for doc in db.get(collection, []) if self._match(doc, filter_dict)]

            if not matched_docs:
                raise ValueError(f"No document found in '{collection}' matching {filter_dict}")
            if len(matched_docs) > 1:
                raise ValueError(
                    f"Expected 1 document, but found {len(matched_docs)} in '{collection}'")

            deleted_doc = matched_docs[0]
            db[collection] = [doc for doc in db.get(collection, []) if doc != deleted_doc]
            self._save_db(db)

            return deleted_doc

    def _match(self, document: Dict[str, Any], filter_dict) -> bool:
        if not filter_dict:
            return True
        for key, value in filter_dict.items():
            if document.get(key) != value:
                return False
        return True

    def clear_cache(self) -> None:
        with self.lock:
            self._cache = None
