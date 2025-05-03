import os
import pytest
from unittest.mock import patch, MagicMock
import ipaddress

from utils.db import DatabaseManager
from utils.auth import (
    get_users_collection, hash_password, verify_password,
    register_user, authenticate_user, change_password, logout,
    get_current_user, is_admin, can_edit_prompts,
    get_client_ip, is_ip_allowed, check_ip_access
)
from utils.exceptions import DatabaseError


def get_mongo_client():
    return DatabaseManager.get_instance().get_client()


class SessionState(dict):
    """Streamlitのセッション状態をエミュレートするクラス"""

    def __getattr__(self, name):
        if name in self:
            return self[name]
        return None

    def __setattr__(self, name, value):
        self[name] = value


@pytest.fixture
def mock_st():
    with patch('utils.auth.st') as mock_st:
        # カスタムクラスでセッション状態をモック
        mock_st.session_state = SessionState()
        mock_st.session_state.user = None
        mock_st.error = MagicMock()
        mock_st.success = MagicMock()
        yield mock_st


@patch('utils.db.MongoClient')
def test_get_mongo_client(mock_mongo_client):
    """MongoDBクライアント取得機能のテスト"""
    mock_client = MagicMock()
    mock_mongo_client.return_value = mock_client

    DatabaseManager._instance = None
    DatabaseManager._client = None

    # 環境変数が設定されている場合
    with patch('utils.db.MONGODB_URI', 'mongodb://localhost:27017'):
        client = get_mongo_client()
        assert client == mock_client
        mock_mongo_client.assert_called_once()

    # DatabaseManagerのシングルトンをリセット
    DatabaseManager._instance = None
    DatabaseManager._client = None

    # 環境変数が設定されていない場合
    with patch('utils.db.MONGODB_URI', None):
        with pytest.raises(DatabaseError) as excinfo:
            get_mongo_client()
        assert "MongoDB接続情報が設定されていません" in str(excinfo.value)


@patch('utils.auth.DatabaseManager.get_instance')
def test_get_users_collection(mock_get_instance):
    """ユーザーコレクション取得機能のテスト"""
    mock_db_manager = MagicMock()
    mock_collection = MagicMock()

    mock_get_instance.return_value = mock_db_manager
    mock_db_manager.get_collection.return_value = mock_collection

    # 環境変数をモック
    with patch.dict('os.environ', {
        'MONGODB_USERS_COLLECTION': 'test_users'
    }):
        collection = get_users_collection()

        assert collection == mock_collection
        mock_db_manager.get_collection.assert_called_once_with('test_users')


def test_hash_password():
    """パスワードハッシュ化機能のテスト"""
    password = "testpassword"
    hashed = hash_password(password)

    # ハッシュ値がバイト型であることを確認
    assert isinstance(hashed, bytes)
    # 同じパスワードでも異なるハッシュ値が生成される（ソルトが異なるため）
    assert hashed != hash_password(password)
    # 正しいパスワードで検証できることを確認
    assert verify_password(password, hashed) == True
    # 誤ったパスワードでは検証に失敗することを確認
    assert verify_password("wrongpassword", hashed) == False


@patch('utils.auth.get_users_collection')
def test_register_user(mock_get_users_collection):
    """ユーザー登録機能のテスト"""
    mock_collection = MagicMock()
    mock_get_users_collection.return_value = mock_collection

    # 既存のユーザー（登録失敗ケース）
    mock_collection.find_one.return_value = {"username": "existinguser"}
    success, message = register_user("existinguser", "password")
    assert success == False
    assert "このユーザー名は既に使用されています" in message

    # 新規ユーザー（登録成功ケース）
    mock_collection.find_one.return_value = None

    with patch('utils.auth.hash_password', return_value=b'hashed_password'):
        success, message = register_user("newuser", "password", is_admin=True)
        assert success == True
        assert "ユーザー登録が完了しました" in message

        # insert_oneが適切な引数で呼ばれたか確認
        mock_collection.insert_one.assert_called_once()
        called_args = mock_collection.insert_one.call_args[0][0]
        assert called_args["username"] == "newuser"
        assert called_args["password"] == b'hashed_password'
        assert called_args["is_admin"] == True


@patch('utils.auth.get_users_collection')
def test_authenticate_user(mock_get_users_collection):
    """ユーザー認証機能のテスト"""
    mock_collection = MagicMock()
    mock_get_users_collection.return_value = mock_collection

    # 存在しないユーザー
    mock_collection.find_one.return_value = None
    success, result = authenticate_user("nonexistent", "password")
    assert success == False
    assert "ユーザー名またはパスワードが正しくありません" in result

    # 正しいパスワード
    mock_collection.find_one.return_value = {
        "username": "testuser",
        "password": b'hashed_password',
        "is_admin": True
    }

    with patch('utils.auth.verify_password', return_value=True):
        success, result = authenticate_user("testuser", "correctpassword")
        assert success == True
        assert result["username"] == "testuser"
        assert result["is_admin"] == True

    # 誤ったパスワード
    with patch('utils.auth.verify_password', return_value=False):
        success, result = authenticate_user("testuser", "wrongpassword")
        assert success == False
        assert "ユーザー名またはパスワードが正しくありません" in result


@patch('utils.auth.get_users_collection')
def test_change_password(mock_get_users_collection):
    """パスワード変更機能のテスト"""
    mock_collection = MagicMock()
    mock_get_users_collection.return_value = mock_collection

    # 存在しないユーザー
    mock_collection.find_one.return_value = None
    success, message = change_password("nonexistent", "oldpass", "newpass")
    assert success == False
    assert "ユーザーが見つかりません" in message

    # 誤った現在のパスワード
    mock_collection.find_one.return_value = {
        "username": "testuser",
        "password": b'hashed_old_password'
    }

    with patch('utils.auth.verify_password', return_value=False):
        success, message = change_password("testuser", "wrongpass", "newpass")
        assert success == False
        assert "現在のパスワードが正しくありません" in message

    # 正しいパスワード変更
    with patch('utils.auth.verify_password', return_value=True):
        with patch('utils.auth.hash_password', return_value=b'hashed_new_password'):
            success, message = change_password("testuser", "correctpass", "newpass")
            assert success == True
            assert "パスワードが正常に変更されました" in message

            # update_oneが適切な引数で呼ばれたか確認
            mock_collection.update_one.assert_called_once_with(
                {"username": "testuser"},
                {"$set": {"password": b'hashed_new_password'}}
            )


def test_logout(mock_st):
    """ログアウト機能のテスト"""
    # ログイン済み状態
    mock_st.session_state.user = {"username": "testuser"}
    result = logout()
    assert result == True
    assert mock_st.session_state.user is None

    # 未ログイン状態
    mock_st.session_state.user = None
    result = logout()
    assert result == True


def test_get_current_user(mock_st):
    """現在のユーザー取得機能のテスト"""
    # ユーザーがある場合
    mock_st.session_state.user = {"username": "testuser", "is_admin": True}
    user = get_current_user()
    assert user == {"username": "testuser", "is_admin": True}

    # ユーザーがない場合
    mock_st.session_state.user = None
    user = get_current_user()
    assert user is None


def test_is_admin(mock_st):
    """管理者チェック機能のテスト"""
    # 管理者ユーザーの場合
    mock_st.session_state.user = {"username": "adminuser", "is_admin": True}
    assert is_admin() == True

    # 一般ユーザーの場合
    mock_st.session_state.user = {"username": "normaluser", "is_admin": False}
    assert is_admin() == False

    # ユーザーがない場合
    mock_st.session_state.user = None
    assert is_admin() == False


def test_can_edit_prompts(mock_st):
    """プロンプト編集権限チェック機能のテスト"""
    # ログイン不要モードの場合（誰でも編集可能）
    with patch('utils.auth.REQUIRE_LOGIN', False):
        assert can_edit_prompts() == True

    # ログイン必須モードで管理者の場合
    with patch('utils.auth.REQUIRE_LOGIN', True):
        mock_st.session_state.user = {"username": "adminuser", "is_admin": True}
        assert can_edit_prompts() == True

    # ログイン必須モードで一般ユーザーの場合
    with patch('utils.auth.REQUIRE_LOGIN', True):
        mock_st.session_state.user = {"username": "normaluser", "is_admin": False}
        assert can_edit_prompts() == False

    # ログイン必須モードでユーザーがない場合
    with patch('utils.auth.REQUIRE_LOGIN', True):
        mock_st.session_state.user = None
        assert can_edit_prompts() == False


def test_get_client_ip():
    """クライアントIPの取得機能のテスト"""
    # 環境変数にIPアドレスが設定されている場合
    with patch.dict('os.environ', {'HTTP_X_FORWARDED_FOR': '192.168.1.1'}):
        assert get_client_ip() == '192.168.1.1'

    # HTTP_X_FORWARDED_FORがなくREMOTE_ADDRがある場合
    with patch.dict('os.environ', {'HTTP_X_FORWARDED_FOR': '', 'REMOTE_ADDR': '10.0.0.1'}):
        assert get_client_ip() == '10.0.0.1'

    # 両方の環境変数がない場合（ローカル環境）
    with patch.dict('os.environ', {'HTTP_X_FORWARDED_FOR': '', 'REMOTE_ADDR': ''}):
        assert get_client_ip() == '127.0.0.1'


def test_is_ip_allowed():
    """IPホワイトリストチェック機能のテスト"""
    # ホワイトリストが空の場合（すべて許可）
    assert is_ip_allowed('192.168.1.1', '') == True
    assert is_ip_allowed('10.0.0.1', ' ') == True

    # 単一IPのホワイトリスト
    assert is_ip_allowed('192.168.1.1', '192.168.1.1') == True
    assert is_ip_allowed('192.168.1.2', '192.168.1.1') == False

    # 複数IPのホワイトリスト
    assert is_ip_allowed('192.168.1.1', '192.168.1.1, 10.0.0.1') == True
    assert is_ip_allowed('10.0.0.1', '192.168.1.1, 10.0.0.1') == True
    assert is_ip_allowed('172.16.0.1', '192.168.1.1, 10.0.0.1') == False

    # CIDRブロックのホワイトリスト
    assert is_ip_allowed('192.168.1.5', '192.168.1.0/24') == True
    assert is_ip_allowed('192.168.2.1', '192.168.1.0/24') == False

    # 混合したホワイトリスト
    assert is_ip_allowed('192.168.1.5', '10.0.0.1, 192.168.1.0/24') == True
    assert is_ip_allowed('10.0.0.1', '10.0.0.1, 192.168.1.0/24') == True
    assert is_ip_allowed('172.16.0.1', '10.0.0.1, 192.168.1.0/24') == False

    # 無効なIPアドレス
    assert is_ip_allowed('invalid-ip', '192.168.1.0/24') == False


@patch('utils.auth.get_client_ip')
@patch('utils.auth.is_ip_allowed')
def test_check_ip_access(mock_is_ip_allowed, mock_get_client_ip, mock_st):
    """IPアクセス制限チェック機能のテスト"""
    mock_get_client_ip.return_value = '192.168.1.1'

    # 許可されたIPアドレスの場合
    mock_is_ip_allowed.return_value = True
    result = check_ip_access('whitelist')
    assert result == True
    mock_is_ip_allowed.assert_called_with('192.168.1.1', 'whitelist')
    mock_st.error.assert_not_called()

    # 許可されていないIPアドレスの場合
    mock_is_ip_allowed.return_value = False
    result = check_ip_access('whitelist')
    assert result == False
    mock_st.error.assert_called_once()
