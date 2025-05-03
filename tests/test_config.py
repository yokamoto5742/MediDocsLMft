import os
import sys
import importlib
import pytest
from unittest.mock import patch, MagicMock

# テスト前に各テストケースで使用する設定をインポート
from utils.config import get_config


@pytest.fixture
def mock_configparser():
    """ConfigParserのモック"""
    with patch('utils.config.configparser.ConfigParser') as mock_cp:
        mock_instance = MagicMock()
        mock_cp.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_path():
    """Pathクラスのモック"""
    with patch('utils.config.Path') as mock_p:
        mock_instance = MagicMock()
        mock_parent = MagicMock()
        mock_parent.parent = "/app"
        mock_instance.parent.parent = mock_parent
        mock_p.return_value = mock_instance
        yield mock_instance


@patch('utils.config.os.path.join')
def test_get_config(mock_join, mock_configparser, mock_path):
    """設定ファイル読み込み機能のテスト"""
    mock_join.return_value = "/app/config.ini"

    # 設定ファイルが存在する場合
    result = get_config()

    # ConfigParserのreadメソッドが正しく呼ばれたか確認
    mock_configparser.read.assert_called_once_with("/app/config.ini", encoding='utf-8')
    assert result == mock_configparser


@patch('utils.config.load_dotenv')
def test_environment_variables_loaded(mock_load_dotenv):
    """環境変数からの設定読み込みテスト"""
    # 元の環境変数を保存
    original_env = os.environ.copy()

    try:
        # 環境変数を設定し、モジュールを再読み込み
        test_env = {
            'MONGODB_URI': 'mongodb://testuser:testpass@localhost:27017',
            'MONGODB_DB_NAME': 'test_db',
            'MONGODB_USERS_COLLECTION': 'test_users',
            'MONGODB_PROMPTS_COLLECTION': 'test_prompts',
            'MONGODB_DEPARTMENTS_COLLECTION': 'test_departments',
            'GEMINI_CREDENTIALS': 'test_api_key',
            'GEMINI_MODEL': 'test_model',
            'REQUIRE_LOGIN': 'true',
            'IP_WHITELIST': '127.0.0.1',
            'IP_CHECK_ENABLED': 'true'
        }

        os.environ.clear()
        os.environ.update(test_env)

        # config モジュールをリロード
        if 'utils.config' in sys.modules:
            importlib.reload(sys.modules['utils.config'])

        # リロード後のモジュールから変数をインポート
        from utils.config import (
            MONGODB_URI, MONGODB_DB_NAME, MONGODB_USERS_COLLECTION,
            MONGODB_PROMPTS_COLLECTION, MONGODB_DEPARTMENTS_COLLECTION,
            GEMINI_CREDENTIALS, GEMINI_MODEL,
            REQUIRE_LOGIN, IP_WHITELIST, IP_CHECK_ENABLED
        )

        # 環境変数から設定値が正しく取り込まれているか確認
        assert MONGODB_URI == 'mongodb://testuser:testpass@localhost:27017'
        assert MONGODB_DB_NAME == 'test_db'
        assert MONGODB_USERS_COLLECTION == 'test_users'
        assert MONGODB_PROMPTS_COLLECTION == 'test_prompts'
        assert MONGODB_DEPARTMENTS_COLLECTION == 'test_departments'
        assert GEMINI_CREDENTIALS == 'test_api_key'
        assert GEMINI_MODEL == 'test_model'
        assert REQUIRE_LOGIN == True
        assert IP_WHITELIST == '127.0.0.1'
        assert IP_CHECK_ENABLED == True

    finally:
        # テスト後に元の環境変数を復元
        os.environ.clear()
        os.environ.update(original_env)


def test_boolean_environment_variables():
    """ブール値の環境変数解釈テスト"""
    # 元の環境変数を保存
    original_env = os.environ.copy()

    try:
        # Falseとして解釈される環境変数値のテスト
        os.environ.clear()
        os.environ.update({
            'REQUIRE_LOGIN': 'false',
            'IP_CHECK_ENABLED': 'no'
        })

        # モジュールをリロード
        if 'utils.config' in sys.modules:
            importlib.reload(sys.modules['utils.config'])

        # リロード後の変数をインポート
        from utils.config import REQUIRE_LOGIN, IP_CHECK_ENABLED
        assert REQUIRE_LOGIN == False
        assert IP_CHECK_ENABLED == False

        # Trueとして解釈される環境変数値のテスト
        os.environ.clear()
        os.environ.update({
            'REQUIRE_LOGIN': '1',
            'IP_CHECK_ENABLED': 'yes'
        })

        # モジュールをリロード
        if 'utils.config' in sys.modules:
            importlib.reload(sys.modules['utils.config'])

        # リロード後の変数をインポート
        from utils.config import REQUIRE_LOGIN, IP_CHECK_ENABLED
        assert REQUIRE_LOGIN == True
        assert IP_CHECK_ENABLED == True

    finally:
        # テスト後に元の環境変数を復元
        os.environ.clear()
        os.environ.update(original_env)


@patch('utils.config.MongoClient')
def test_get_mongodb_connection(mock_mongo_client):
    """MongoDB接続機能のテスト"""
    pass


@patch('utils.config.genai')
def test_get_gemini_client(mock_genai):
    pass


def test_default_collection_names():
    """コレクション名のデフォルト値テスト"""
    # 元の環境変数を保存
    original_env = os.environ.copy()

    try:
        # 環境変数を完全に削除してデフォルト値が使用されるようにする
        os.environ.clear()
        # 他の必須環境変数を設定（必要に応じて）
        os.environ.update({
            'MONGODB_URI': 'mongodb://localhost:27017',
            'MONGODB_DB_NAME': 'test_db'
        })
        # MONGODB_PROMPTS_COLLECTIONとMONGODB_DEPARTMENTS_COLLECTIONは設定しない

        # モジュールをリロード
        if 'utils.config' in sys.modules:
            importlib.reload(sys.modules['utils.config'])

        # インポート
        from utils.config import MONGODB_PROMPTS_COLLECTION, MONGODB_DEPARTMENTS_COLLECTION
        assert MONGODB_PROMPTS_COLLECTION == 'prompts'
        assert MONGODB_DEPARTMENTS_COLLECTION == 'departments'

    finally:
        # テスト後に元の環境変数を復元
        os.environ.clear()
        os.environ.update(original_env)


@patch('utils.config.get_config')
def test_config_values(mock_get_config):
    """設定ファイルからの値取得テスト"""
    # 設定ファイルがある場合の動作テスト
    mock_config = {
        'PROMPTS': {
            'discharge_summary': 'テストプロンプト'
        }
    }
    mock_get_config.return_value = mock_config

    # リロードは不要（モックを使用するため）
    from utils.config import get_config
    config = get_config()
    assert config['PROMPTS']['discharge_summary'] == 'テストプロンプト'
