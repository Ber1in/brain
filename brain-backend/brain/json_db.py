# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

import json
import threading
import sqlite3
import os

from typing import Dict, List, Any
from filelock import FileLock
from abc import ABC, abstractmethod

SERVER_COLLECTION = "servers"
TEST_CASE_COLLECTION = "test_cases"
TEST_HISTORY_COLLECTION = "test_history"
TASK_POOL_COLLECTION = "tasks"


class BaseDocumentDB(ABC):
    @abstractmethod
    def insert(self, collection: str, document: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def find(self, collection: str, filter_dict=None) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def find_one(self, collection: str, filter_dict=None) -> Dict[str, Any]:
        pass

    @abstractmethod
    def update(self, collection: str,
               filter_dict: Dict[str, Any], update_dict: Dict[str, Any]) -> int:
        pass

    @abstractmethod
    def update_one(self, collection: str, filter_dict: Dict[str, Any], 
                   update_dict: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def delete(self, collection: str, filter_dict: Dict[str, Any]) -> int:
        pass

    @abstractmethod
    def delete_one(self, collection: str, filter_dict: Dict[str, Any]) -> Dict[str, Any]:
        pass


class JSONDocumentDB(BaseDocumentDB):
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


class SQLiteDocumentDB:
    _instance = None
    _instance_lock = threading.Lock()

    # 固定列结构，新增字段填默认值
    COLLECTION_SCHEMAS = {
        "images": {
            "id": None,
            "name": "",
            "ceph_location": "",
            "min_size": 0,
            "mon_host": "",
            "description": "",
            "brain": 0
        },
        "mv_servers": {
            "id": None,
            "name": "",
            "ip_address": "",
            "description": "",
            "sn": "",
            "mac": "",
            "gateway": None,
            "nic_sn": "",
            "clouddisk_enable": 0,
            "recovery_mode": "",
            "task_id": ""
        },
        "system_disks": {
            "id": None,
            "rbd_path": "",
            "image_id": "",
            "mv200_id": "",
            "mv200_ip": "",
            "mon_host": "",
            "bare_id": "",
            "size_gb": 0,
            "flatten": 0,
            "description": "",
            "creator": "",
            "blk_id": 0,
            "efi_uuid": ""
        },
        "bare_metals": {
            "id": None,
            "name": "",
            "host_ip": "",
            "mac": "",
            "gateway": "",
            "description": "",
            "os_user": "",
            "os_password": ""
        },
        "networks": {
            "id": None,
            "mv200_id": "",
            "ip": "",
            "vlan_tag": 0,
            "gateway": "",
            "mtu": 1500,
            "mac": "",
            "dns": "[]",
            "description": "",
            "xsc_id": 0,
            "ifname": "",
            "creator": ""
        },
        SERVER_COLLECTION: {
            "bmc": {
                "ip": "10.0.2.206",
                "hostname": "string"
            },
            "device": {
                "sn": "79V5QJ3",
                "ip": "10.0.3.206",
                "username": "root",
                "vendor": "",
                "product": "",
                "arch": "",
                "cpu_vendor": "",
                "cpu_mode": "",
            },
            "nics": [],
            "tags": [],
            "notes": "",
            "user": "",
            "start": "",
            "time": 0,
            "created_at": "2025-11-04 15:24:12",
            "updated_at": "",
            "id": "99b62073-21dd-440a-9d2a-5e8f5b538a81",
            "recipients": [],
            "task_id": ""
        },
        "tags": {
            "id": "",
            "name": "",
            "color": ""
        },
        TEST_CASE_COLLECTION: {
            "id": "",
            "name": "",
            "created_at": "",
            "user": "",
            "cases": []
        },
        TEST_HISTORY_COLLECTION: {
            "id": "",
            "current": "",
            "latest_commit": "",
            "time": "",
            "url": "",
            "user": "",
            "topo": "",
            "log": ""
        }, 
        TASK_POOL_COLLECTION: {
            "id": "",
            "server_id": "",
            "status": "",
            "stage": "", 
            "detail": "",
            "timestamp": "",
            "mcr": "",
            "type": ""
        }
    }

    def __new__(cls, db_path="/opt/brain/db.sqlite3"):
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path="/opt/brain/db.sqlite3"):
        if getattr(self, "_initialized", False):
            return
        self.db_path = db_path
        self.lock = threading.Lock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._tables_initialized = set()
        self._initialized = True

    def _ensure_table(self, collection: str):
        """Ensure table exists and all schema columns are present."""
        if collection in self._tables_initialized:
            return

        schema = self.COLLECTION_SCHEMAS.get(collection)
        if not schema:
            raise ValueError(f"Unknown collection {collection}")

        with self.lock:
            columns_def = []
            for k, v in schema.items():
                col_type = "INTEGER" if isinstance(v, int) else "TEXT"
                if k == "id":
                    columns_def.append(f"{k} {col_type} PRIMARY KEY")
                else:
                    columns_def.append(f"{k} {col_type}")
            self._conn.execute(
                f"CREATE TABLE IF NOT EXISTS {collection} ({', '.join(columns_def)})"
            )

            cur = self._conn.execute(f"PRAGMA table_info({collection})")
            existing_columns = {row[1] for row in cur.fetchall()}

            for col, default in schema.items():
                if col not in existing_columns:
                    col_type = "INTEGER" if isinstance(default, int) else "TEXT"
                    default_val = self._serialize_field(default)
                    self._conn.execute(
                        f"ALTER TABLE {collection} ADD COLUMN {col} {col_type}"
                    )

                    if default_val is not None:
                        self._conn.execute(
                            f"UPDATE {collection} SET {col} = ? WHERE {col} IS NULL",
                            (default_val,)
                        )

            self._tables_initialized.add(collection)

    def insert(self, collection: str, document: Dict[str, Any]) -> None:
        if "id" not in document:
            raise ValueError("Document must have 'id' key before insert.")
        self._ensure_table(collection)
        schema = self.COLLECTION_SCHEMAS[collection]
        row = {k: document.get(k, v) for k, v in schema.items()}
        cols = list(row.keys())
        vals = [self._serialize_field(row[c]) for c in cols]
        placeholders = ",".join("?" for _ in cols)
        sql = f"INSERT INTO {collection} ({','.join(cols)}) VALUES ({placeholders})"
        with self.lock, self._conn:
            self._conn.execute(sql, vals)

    def find(self, collection: str, filter_dict=None) -> List[Dict[str, Any]]:
        self._ensure_table(collection)
        sql = f"SELECT * FROM {collection}"
        params = []

        if filter_dict:
            conds = []
            for k, v in filter_dict.items():
                # json_extract 特殊处理
                if k.startswith("json_extract("):
                    conds.append(f"{k} = ?")
                else:
                    # 支持操作符，默认 =
                    if " " in k:
                        col, op = k.split(" ", 1)
                        conds.append(f"{col} {op} ?")
                    else:
                        conds.append(f"{k} = ?")
                params.append(self._serialize_field(v))
            sql += " WHERE " + " AND ".join(conds)

        with self.lock:
            cur = self._conn.execute(sql, params)
            rows = [
                dict(
                    zip(
                        [c[0] for c in cur.description],
                        [self._deserialize_field(v) for v in row],
                    )
                )
                for row in cur.fetchall()
            ]
        return rows

    def find_one(self, collection: str, filter_dict=None) -> Dict[str, Any]:
        results = self.find(collection, filter_dict)
        if not results:
            raise ValueError(f"No entry found matching {filter_dict}")
        if len(results) > 1:
            raise ValueError(
                f"Expected 1 document, but found {len(results)} matching {filter_dict}")
        return results[0]

    def update(self, collection: str, filter_dict: Dict[str, Any],
               update_dict: Dict[str, Any]) -> int:
        if not update_dict:
            return 0
        self._ensure_table(collection)
        set_clause = ", ".join(f"{k}=?" for k in update_dict)
        set_vals = [self._serialize_field(v) for v in update_dict.values()]
        params = set_vals
        sql = f"UPDATE {collection} SET {set_clause}"
        if filter_dict:
            conds = []
            for k, v in filter_dict.items():
                conds.append(f"{k}=?")
                params.append(self._serialize_field(v))
            sql += " WHERE " + " AND ".join(conds)
        with self.lock, self._conn:
            cur = self._conn.execute(sql, params)
            return cur.rowcount

    def update_one(self, collection: str, filter_dict: Dict[str, Any], 
                   update_dict: Dict[str, Any]) -> Dict[str, Any]:
        row = self.find_one(collection, filter_dict)
        self.update(collection, {"id": row["id"]}, update_dict)
        return row

    def delete(self, collection: str, filter_dict: Dict[str, Any]) -> int:
        self._ensure_table(collection)
        sql = f"DELETE FROM {collection}"
        params = []
        if filter_dict:
            conds = []
            for k, v in filter_dict.items():
                conds.append(f"{k}=?")
                params.append(self._serialize_field(v))
            sql += " WHERE " + " AND ".join(conds)
        with self.lock, self._conn:
            cur = self._conn.execute(sql, params)
            return cur.rowcount

    def delete_one(self, collection: str, filter_dict: Dict[str, Any]) -> Dict[str, Any]:
        row = self.find_one(collection, filter_dict)
        self.delete(collection, {"id": row["id"]})
        return row

    @staticmethod
    def _serialize_field(value):
        if isinstance(value, list) or isinstance(value, dict):
            return json.dumps(value)
        if isinstance(value, bool):
            return int(value)
        return value

    @staticmethod
    def _deserialize_field(value):
        if value is None:
            return None
        if isinstance(value, bytes):
            value = value.decode()
        try:
            return json.loads(value)
        except Exception:
            return value
