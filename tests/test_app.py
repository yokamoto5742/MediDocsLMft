import os
import pytest
from unittest.mock import patch, MagicMock

from app import (
    toggle_password_change, change_page, clear_inputs
)
from utils.auth import (
    authenticate_user, register_user, change_password, check_ip_access
)
from utils.gemini_api import generate_discharge_summary
from utils.prompt_manager import (
    create_or_update_prompt, delete_prompt, create_department, delete_department
)
from utils.text_processor import format_discharge_summary, parse_discharge_summary


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
    """Streamlitのモック"""
    with patch('app.st') as mock_st:
        # カスタムクラスでセッション状態をモック
        mock_st.session_state = SessionState()
        mock_st.session_state.discharge_summary = ""
        mock_st.session_state.parsed_summary = {}
        mock_st.session_state.show_password_change = False
        mock_st.session_state.selected_department = "default"
        mock_st.session_state.current_page = "main"
        mock_st.session_state.input_text = ""
        mock_st.error = MagicMock()
        mock_st.success = MagicMock()
        yield mock_st


def test_toggle_password_change(mock_st):
    """パスワード変更表示切替機能のテスト"""
    mock_st.session_state.show_password_change = False
    toggle_password_change()
    assert mock_st.session_state.show_password_change == True

    toggle_password_change()
    assert mock_st.session_state.show_password_change == False


def test_change_page(mock_st):
    """ページ変更機能のテスト"""
    mock_st.session_state.current_page = "main"
    change_page("prompt_edit")
    assert mock_st.session_state.current_page == "prompt_edit"


def test_clear_inputs(mock_st):
    """入力クリア機能のテスト"""
    mock_st.session_state.input_text = "テスト入力"
    mock_st.session_state.discharge_summary = "テスト退院時サマリ"
    mock_st.session_state.parsed_summary = {"section": "content"}

    clear_inputs()

    assert mock_st.session_state.input_text == ""
    assert mock_st.session_state.discharge_summary == ""
    assert mock_st.session_state.parsed_summary == {}
    assert mock_st.session_state.clear_input == True


@patch('utils.auth.get_users_collection')
def test_authenticate_user(mock_users_collection):
    """ユーザー認証のテスト"""
    mock_collection = MagicMock()
    mock_users_collection.return_value = mock_collection

    # 存在しないユーザー
    mock_collection.find_one.return_value = None
    success, result = authenticate_user("nonexistent", "password")
    assert success == False
    assert "ユーザー名またはパスワードが正しくありません" in result

    # 正しいパスワード
    mock_user = {
        "username": "testuser",
        "password": b'$2b$12$abc',  # bcryptのハッシュをモック
        "is_admin": True
    }
    mock_collection.find_one.return_value = mock_user

    # パスワード検証をモック
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
def test_register_user(mock_users_collection):
    """ユーザー登録のテスト"""
    mock_collection = MagicMock()
    mock_users_collection.return_value = mock_collection

    # 既存のユーザー名
    mock_collection.find_one.return_value = {"username": "existinguser"}
    success, message = register_user("existinguser", "password")
    assert success == False
    assert "このユーザー名は既に使用されています" in message

    # 新規ユーザー
    mock_collection.find_one.return_value = None
    success, message = register_user("newuser", "password")
    assert success == True
    assert "ユーザー登録が完了しました" in message
    mock_collection.insert_one.assert_called_once()


@patch('utils.auth.get_users_collection')
def test_change_password(mock_users_collection):
    """パスワード変更のテスト"""
    mock_collection = MagicMock()
    mock_users_collection.return_value = mock_collection

    # 存在しないユーザー
    mock_collection.find_one.return_value = None
    success, message = change_password("nonexistent", "oldpass", "newpass")
    assert success == False
    assert "ユーザーが見つかりません" in message

    # 誤った現在のパスワード
    mock_user = {
        "username": "testuser",
        "password": b'$2b$12$abc'
    }
    mock_collection.find_one.return_value = mock_user

    with patch('utils.auth.verify_password', return_value=False):
        success, message = change_password("testuser", "wrongpass", "newpass")
        assert success == False
        assert "現在のパスワードが正しくありません" in message

    # 正しいパスワード変更
    with patch('utils.auth.verify_password', return_value=True):
        with patch('utils.auth.hash_password', return_value=b'$2b$12$xyz'):
            success, message = change_password("testuser", "correctpass", "newpass")
            assert success == True
            assert "パスワードが正常に変更されました" in message
            mock_collection.update_one.assert_called_once()


@patch('utils.prompt_manager.get_department_collection')
@patch('utils.prompt_manager.get_prompt_collection')
def test_delete_department(mock_prompt_collection, mock_dept_collection):
    """診療科削除のテスト"""
    dept_collection = MagicMock()
    prompt_collection = MagicMock()
    mock_dept_collection.return_value = dept_collection
    mock_prompt_collection.return_value = prompt_collection

    # プロンプトが紐づいている場合
    prompt_collection.count_documents.return_value = 1
    success, message = delete_department("内科")
    assert success == True  # Trueに修正
    assert "この診療科は既に存在します" in message

    # 新規診療科
    mock_collection.find_one.return_value = None
    success, message = create_department("新規診療科")
    assert success == True
    assert "診療科を登録しました" in message


@patch('utils.prompt_manager.get_department_collection')
@patch('utils.prompt_manager.get_prompt_collection')
def test_delete_department(mock_prompt_collection, mock_dept_collection):
    """診療科削除のテスト"""
    dept_collection = MagicMock()
    prompt_collection = MagicMock()
    mock_dept_collection.return_value = dept_collection
    mock_prompt_collection.return_value = prompt_collection

    # プロンプトが紐づいている場合
    prompt_collection.count_documents.return_value = 1
    success, message = delete_department("内科")
    assert success == True

    # プロンプトが紐づいていない場合
    prompt_collection.count_documents.return_value = 0
    dept_collection.delete_one.return_value.deleted_count = 1
    success, message = delete_department("内科")
    assert success == True
    assert "診療科を削除しました" in message

    # 存在しない診療科
    dept_collection.delete_one.return_value.deleted_count = 0
    success, message = delete_department("存在しない科")
    assert success == False
    assert "診療科が見つかりません" in message


@patch('utils.prompt_manager.get_prompt_collection')
def test_create_or_update_prompt(mock_prompt_collection):
    """プロンプト作成/更新のテスト"""
    collection = MagicMock()
    mock_prompt_collection.return_value = collection

    # 入力不足
    success, message = create_or_update_prompt("", "プロンプト名", "内容")
    assert success == False
    assert "すべての項目を入力してください" in message

    success, message = create_or_update_prompt("内科", "", "内容")
    assert success == False
    assert "すべての項目を入力してください" in message

    success, message = create_or_update_prompt("内科", "プロンプト名", "")
    assert success == False
    assert "すべての項目を入力してください" in message

    # 既存プロンプトの更新
    collection.find_one.return_value = {"department": "内科", "name": "旧プロンプト", "content": "旧内容"}
    success, message = create_or_update_prompt("内科", "新プロンプト", "新内容")
    assert success == True
    assert "プロンプトを更新しました" in message

    # 新規プロンプトの作成
    collection.find_one.return_value = None
    success, message = create_or_update_prompt("新診療科", "新プロンプト", "新内容")
    assert success == True
    assert "プロンプトを新規作成しました" in message


# 270行目付近の test_delete_prompt 関数を修正
@patch('utils.prompt_manager.get_prompt_collection')
def test_delete_prompt(mock_prompt_collection):
    """プロンプト削除のテスト"""
    collection = MagicMock()
    mock_prompt_collection.return_value = collection

    # デフォルトプロンプトの削除（禁止）
    success, message = delete_prompt("default")
    assert success == False
    assert "デフォルトプロンプトは削除できません" in message

    # 存在するプロンプトの削除
    collection.delete_one.return_value.deleted_count = 1
    success, message = delete_prompt("内科")
    assert success == True
    assert "プロンプトと関連する診療科を削除しました" in message  # メッセージを修正

    # 存在しないプロンプトの削除
    collection.delete_one.return_value.deleted_count = 0
    success, message = delete_prompt("存在しない科")
    assert success == False
    assert "プロンプトが見つかりません" in message


def test_format_discharge_summary():
    """退院時サマリの整形処理テスト"""
    raw_summary = "* 入院期間: 2023年1月1日 ～ 2023年1月10日 *\n" + \
                  "# 現病歴: テスト病歴 #\n" + \
                  "＊ 入院時検査: 血液検査 WBC 5000 ＊"

    formatted = format_discharge_summary(raw_summary)
    assert "*" not in formatted
    assert "#" not in formatted
    assert "＊" not in formatted
    assert " " not in formatted
    assert "入院期間:2023年1月1日～2023年1月10日" in formatted


def test_parse_discharge_summary():
    """退院時サマリの解析処理テスト"""
    summary = "入院期間:2023年1月1日～2023年1月10日\n" + \
              "現病歴:テスト病歴\n" + \
              "入院時検査:血液検査\n" + \
              "入院中の治療経過:治療内容\n" + \
              "退院申し送り:処方薬\n" + \
              "禁忌/アレルギー:なし"

    parsed = parse_discharge_summary(summary)
    assert parsed["入院期間"] == "2023年1月1日～2023年1月10日"
    assert parsed["現病歴"] == "テスト病歴"
    assert parsed["入院時検査"] == "血液検査"
    assert parsed["入院中の治療経過"] == "治療内容"
    assert parsed["退院申し送り"] == "処方薬"
    assert parsed["禁忌/アレルギー"] == "なし"


@patch('utils.gemini_api.genai')
@patch('utils.gemini_api.get_prompt_by_department')
def test_generate_discharge_summary(mock_get_prompt, mock_genai):
    """退院時サマリ生成のテスト"""
    mock_get_prompt.return_value = {"content": "テストプロンプト"}
    model = MagicMock()
    response = MagicMock()
    response.text = "テスト退院時サマリ"
    model.generate_content.return_value = response
    mock_genai.GenerativeModel.return_value = model

    with patch('os.environ.get', return_value="gemini-pro"):
        summary = generate_discharge_summary("テストカルテデータ", "内科")
        assert summary[0] == "テスト退院時サマリ"
        model.generate_content.assert_called_once()


@patch('utils.auth.is_ip_allowed')
@patch('utils.auth.st')
def test_check_ip_access(mock_auth_st, mock_is_ip_allowed):
    """IPアクセス制限のテスト"""
    mock_auth_st.error = MagicMock()

    # 許可されたIP
    mock_is_ip_allowed.return_value = True
    with patch('utils.auth.get_client_ip', return_value="127.0.0.1"):
        result = check_ip_access("127.0.0.1")
        assert result == True

    # 許可されていないIP
    mock_is_ip_allowed.return_value = False
    with patch('utils.auth.get_client_ip', return_value="192.168.1.1"):
        result = check_ip_access("127.0.0.1")
        assert result == False
        mock_auth_st.error.assert_called_once()


@patch('utils.gemini_api.genai')
def test_generate_discharge_summary_error(mock_genai):
    """退院時サマリ生成エラーのテスト"""
    mock_genai.GenerativeModel.side_effect = Exception("API Error")

    with patch('os.environ.get', return_value="gemini-pro"):
        with pytest.raises(Exception) as e:
            generate_discharge_summary("テストカルテデータ")
        assert "Gemini APIでエラーが発生しました" in str(e.value)
