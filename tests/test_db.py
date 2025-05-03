import os
import pytest
from unittest.mock import patch, MagicMock

from utils.db import DatabaseManager
from utils.exceptions import DatabaseError


@pytest.fixture
def reset_database_manager():
    """各テスト前後にDatabaseManagerのシングルトンインスタンスをリセット"""
    DatabaseManager._instance = None
    DatabaseManager._client = None
    yield
    DatabaseManager._instance = None
    DatabaseManager._client = None


@patch('utils.db.MongoClient')
def test_get_instance_creates_singleton(mock_mongo_client, reset_database_manager):
    """get_instanceメソッドがシングルトンインスタンスを返すことをテスト"""
    # モックのクライアントを設定
    mock_client = MagicMock()
    mock_mongo_client.return_value = mock_client

    # 環境変数を設定してMongoDBURIがあるようにする
    with patch.dict('os.environ', {'MONGODB_URI': 'mongodb://localhost:27017'}):
        # 初回の呼び出し
        instance1 = DatabaseManager.get_instance()
        # 2回目の呼び出し
        instance2 = DatabaseManager.get_instance()

        # 同じインスタンスが返されることを確認
        assert instance1 is instance2
        # MongoClientが一度だけ呼ばれることを確認
        mock_mongo_client.assert_called_once()


@patch('utils.db.MONGODB_URI', None)
def test_init_raises_error_without_uri(reset_database_manager):
    """MongoDB URIがない場合にDatabaseErrorが発生することをテスト"""
    with pytest.raises(DatabaseError) as excinfo:
        DatabaseManager()
    assert "MongoDB接続情報が設定されていません" in str(excinfo.value)


@patch('utils.db.MongoClient')
def test_init_raises_error_on_connection_failure(mock_mongo_client, reset_database_manager):
    """MongoDBへの接続に失敗した場合にDatabaseErrorが発生することをテスト"""
    # MongoClientが例外を投げるように設定
    mock_mongo_client.side_effect = Exception("Connection failed")

    # 環境変数を設定してMongoDBURIがあるようにする
    with patch.dict('os.environ', {'MONGODB_URI': 'mongodb://localhost:27017'}):
        with pytest.raises(DatabaseError) as excinfo:
            DatabaseManager()
        assert "MongoDBへの接続に失敗しました" in str(excinfo.value)


@patch('utils.db.MongoClient')
def test_get_client(mock_mongo_client, reset_database_manager):
    """get_clientメソッドが正しいクライアントインスタンスを返すことをテスト"""
    # モックのクライアントを設定
    mock_client = MagicMock()
    mock_mongo_client.return_value = mock_client

    # 環境変数を設定してMongoDBURIがあるようにする
    with patch.dict('os.environ', {'MONGODB_URI': 'mongodb://localhost:27017'}):
        manager = DatabaseManager.get_instance()
        client = manager.get_client()

        assert client is mock_client


@patch('utils.db.MongoClient')
def test_get_database_with_default(mock_mongo_client, reset_database_manager):
    """get_databaseメソッドがデフォルトのデータベース名を使用することをテスト"""
    # モックのクライアントとデータベースを設定
    mock_db = MagicMock()
    mock_client = MagicMock()
    mock_client.__getitem__.return_value = mock_db
    mock_mongo_client.return_value = mock_client

    # 環境変数を設定してMongoDBURIがあるようにする
    with patch.dict('os.environ', {'MONGODB_URI': 'mongodb://localhost:27017'}):
        manager = DatabaseManager.get_instance()
        db = manager.get_database()

        assert db is mock_db
        # デフォルトのデータベース名でアクセスされることを確認
        mock_client.__getitem__.assert_called_once_with("discharge_summary_app")


@patch('utils.db.MongoClient')
def test_get_database_with_env_var(mock_mongo_client, reset_database_manager):
    """get_databaseメソッドが環境変数からデータベース名を取得することをテスト"""
    # モックのクライアントとデータベースを設定
    mock_db = MagicMock()
    mock_client = MagicMock()
    mock_client.__getitem__.return_value = mock_db
    mock_mongo_client.return_value = mock_client

    # 環境変数を設定してMongoDBURIとDB名があるようにする
    with patch.dict('os.environ', {
        'MONGODB_URI': 'mongodb://localhost:27017',
        'MONGODB_DB_NAME': 'test_db'
    }):
        manager = DatabaseManager.get_instance()
        db = manager.get_database()

        assert db is mock_db
        # 環境変数で指定されたデータベース名でアクセスされることを確認
        mock_client.__getitem__.assert_called_once_with("test_db")


@patch('utils.db.MongoClient')
def test_get_database_with_param(mock_mongo_client, reset_database_manager):
    """get_databaseメソッドが引数でデータベース名を指定できることをテスト"""
    # モックのクライアントとデータベースを設定
    mock_db = MagicMock()
    mock_client = MagicMock()
    mock_client.__getitem__.return_value = mock_db
    mock_mongo_client.return_value = mock_client

    # 環境変数を設定してMongoDBURIがあるようにする
    with patch.dict('os.environ', {'MONGODB_URI': 'mongodb://localhost:27017'}):
        manager = DatabaseManager.get_instance()
        db = manager.get_database(db_name="custom_db")

        assert db is mock_db
        # 引数で指定されたデータベース名でアクセスされることを確認
        mock_client.__getitem__.assert_called_once_with("custom_db")


@patch('utils.db.MongoClient')
def test_get_collection(mock_mongo_client, reset_database_manager):
    """get_collectionメソッドが正しいコレクションを返すことをテスト"""
    # モックのクライアント、データベース、コレクションを設定
    mock_collection = MagicMock()
    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_collection
    mock_client = MagicMock()
    mock_client.__getitem__.return_value = mock_db
    mock_mongo_client.return_value = mock_client

    # 環境変数を設定してMongoDBURIがあるようにする
    with patch.dict('os.environ', {'MONGODB_URI': 'mongodb://localhost:27017'}):
        manager = DatabaseManager.get_instance()
        collection = manager.get_collection(collection_name="test_collection")

        assert collection is mock_collection
        # 正しいデータベースとコレクション名でアクセスされることを確認
        mock_client.__getitem__.assert_called_once_with("discharge_summary_app")
        mock_db.__getitem__.assert_called_once_with("test_collection")


@patch('utils.db.MongoClient')
def test_get_collection_with_custom_db(mock_mongo_client, reset_database_manager):
    """get_collectionメソッドがカスタムデータベースのコレクションを返すことをテスト"""
    # モックのクライアント、データベース、コレクションを設定
    mock_collection = MagicMock()
    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_collection
    mock_client = MagicMock()
    mock_client.__getitem__.return_value = mock_db
    mock_mongo_client.return_value = mock_client

    # 環境変数を設定してMongoDBURIがあるようにする
    with patch.dict('os.environ', {'MONGODB_URI': 'mongodb://localhost:27017'}):
        manager = DatabaseManager.get_instance()
        collection = manager.get_collection(collection_name="test_collection", db_name="custom_db")

        assert collection is mock_collection
        # 引数で指定されたデータベースとコレクション名でアクセスされることを確認
        mock_client.__getitem__.assert_called_once_with("custom_db")
        mock_db.__getitem__.assert_called_once_with("test_collection")


@patch('utils.db.MongoClient')
def test_client_created_once(mock_mongo_client, reset_database_manager):
    """クライアントが一度だけ作成されることをテスト（コンストラクタが2回呼ばれても）"""
    # モックのクライアントを設定
    mock_client = MagicMock()
    mock_mongo_client.return_value = mock_client

    # 環境変数を設定してMongoDBURIがあるようにする
    with patch.dict('os.environ', {'MONGODB_URI': 'mongodb://localhost:27017'}):
        # 最初のインスタンスを作成
        manager1 = DatabaseManager()
        # 2つ目のインスタンスを作成（内部的には新しいクライアントは作成されないはず）
        manager2 = DatabaseManager()

        # MongoClientが一度だけ呼ばれることを確認
        mock_mongo_client.assert_called_once()
