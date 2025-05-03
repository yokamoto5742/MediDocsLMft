import os

from pymongo import MongoClient

from utils.config import MONGODB_URI
from utils.exceptions import DatabaseError


class DatabaseManager:
    _instance = None
    _client = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = DatabaseManager()
        return cls._instance

    def __init__(self):
        if DatabaseManager._client is not None:
            return

        if not MONGODB_URI:
            raise DatabaseError("MongoDB接続情報が設定されていません。環境変数または設定ファイルを確認してください。")

        try:
            DatabaseManager._client = MongoClient(
                MONGODB_URI,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=30000,
                ssl=True
            )
        except Exception as e:
            raise DatabaseError(f"MongoDBへの接続に失敗しました: {str(e)}")

    @staticmethod
    def get_client():
        return DatabaseManager._client

    def get_database(self, db_name=None):
        if db_name is None:
            db_name = os.environ.get("MONGODB_DB_NAME", "discharge_summary_app")
        return self.get_client()[db_name]

    def get_collection(self, collection_name, db_name=None):
        db = self.get_database(db_name)
        return db[collection_name]


def get_usage_collection():
    """使用統計を保存するコレクションを取得"""
    try:
        db_manager = DatabaseManager.get_instance()
        collection_name = "summary_usage"
        return db_manager.get_collection(collection_name)
    except Exception as e:
        raise DatabaseError(f"使用状況コレクションの取得に失敗しました: {str(e)}")
