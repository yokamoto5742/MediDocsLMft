import datetime
import pytest
from unittest.mock import patch, MagicMock

from utils.prompt_manager import (
    get_prompt_collection, get_department_collection, get_current_datetime,
    insert_document, update_document, initialize_departments, get_all_departments,
    create_department, delete_department, initialize_default_prompt,
    get_prompt_by_department, get_all_prompts, create_or_update_prompt,
    delete_prompt, initialize_database
)


@pytest.fixture
def mock_db_connection():
    """MongoDB接続のモック"""
    with patch('utils.db.DatabaseManager.get_instance') as mock_conn:
        mock_instance = MagicMock()
        mock_conn.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_prompt_collection():
    """プロンプトコレクションのモック"""
    with patch('utils.prompt_manager.get_prompt_collection') as mock_coll:
        mock_collection = MagicMock()
        mock_coll.return_value = mock_collection
        yield mock_collection


@pytest.fixture
def mock_department_collection():
    """診療科コレクションのモック"""
    with patch('utils.prompt_manager.get_department_collection') as mock_coll:
        mock_collection = MagicMock()
        mock_coll.return_value = mock_collection
        yield mock_collection


@pytest.fixture
def mock_datetime():
    """日時関連のモック"""
    with patch('utils.prompt_manager.datetime') as mock_dt:
        mock_now = datetime.datetime(2025, 4, 1, 12, 0, 0)
        mock_dt.datetime.now.return_value = mock_now
        yield mock_dt


def test_get_prompt_collection(mock_db_connection):
    """プロンプトコレクション取得のテスト"""
    mock_collection = MagicMock()
    mock_db_connection.get_collection.return_value = mock_collection

    with patch('utils.prompt_manager.os.environ.get', return_value='test_prompts'):
        collection = get_prompt_collection()

        assert collection == mock_collection
        mock_db_connection.get_collection.assert_called_once_with('test_prompts')


def test_get_department_collection(mock_db_connection):
    """診療科コレクション取得のテスト"""
    mock_collection = MagicMock()
    mock_db_connection.get_collection.return_value = mock_collection

    with patch('utils.prompt_manager.os.environ.get', return_value='test_departments'):
        collection = get_department_collection()

        assert collection == mock_collection
        mock_db_connection.get_collection.assert_called_once_with('test_departments')


def test_get_current_datetime(mock_datetime):
    """現在時刻取得のテスト"""
    expected_time = datetime.datetime(2025, 4, 1, 12, 0, 0)
    result = get_current_datetime()

    assert result == expected_time


def test_insert_document(mock_datetime):
    """ドキュメント挿入のテスト"""
    mock_collection = MagicMock()
    test_document = {"name": "テスト"}
    expected_time = datetime.datetime(2025, 4, 1, 12, 0, 0)

    result = insert_document(mock_collection, test_document)

    mock_collection.insert_one.assert_called_once()
    # ドキュメントに日時フィールドが追加されていることを確認
    called_with = mock_collection.insert_one.call_args[0][0]
    assert called_with["name"] == "テスト"
    assert called_with["created_at"] == expected_time
    assert called_with["updated_at"] == expected_time
    assert result == mock_collection.insert_one.return_value


def test_update_document(mock_datetime):
    """ドキュメント更新のテスト"""
    mock_collection = MagicMock()
    test_query = {"_id": "123"}
    test_update = {"name": "更新テスト"}
    expected_time = datetime.datetime(2025, 4, 1, 12, 0, 0)

    result = update_document(mock_collection, test_query, test_update)

    mock_collection.update_one.assert_called_once()
    # 更新データに日時フィールドが追加されていることを確認
    called_args = mock_collection.update_one.call_args
    assert called_args[0][0] == test_query
    assert called_args[0][1]["$set"]["name"] == "更新テスト"
    assert called_args[0][1]["$set"]["updated_at"] == expected_time
    assert result == mock_collection.update_one.return_value


def test_initialize_departments_empty(mock_department_collection):
    """診療科初期化のテスト（空のコレクション）"""
    # コレクションが空の場合
    mock_department_collection.count_documents.return_value = 0

    initialize_departments()

    # デフォルトの診療科が追加されたことを確認
    assert mock_department_collection.count_documents.call_count == 1
    assert mock_department_collection.count_documents.call_args[0][0] == {}
    # デフォルト診療科の数だけinsert_documentが呼ばれるはず
    from utils.prompt_manager import DEFAULT_DEPARTMENTS
    assert mock_department_collection.insert_one.call_count >= len(DEFAULT_DEPARTMENTS)


def test_initialize_departments_nonempty(mock_department_collection):
    """診療科初期化のテスト（既存データあり）"""
    # コレクションに既存データがある場合
    mock_department_collection.count_documents.return_value = 5

    initialize_departments()

    # 既存データがある場合は追加されない
    assert mock_department_collection.count_documents.call_count == 1
    assert mock_department_collection.insert_one.call_count == 0


def test_get_all_departments(mock_department_collection):
    """全診療科取得のテスト"""
    # テスト用の診療科データ
    test_departments = [
        {"name": "内科", "_id": "1"},
        {"name": "外科", "_id": "2"},
        {"name": "小児科", "_id": "3"}
    ]
    # ソート済みでfindの結果を返すよう設定
    mock_cursor = MagicMock()
    mock_cursor.__iter__.return_value = iter(test_departments)
    mock_department_collection.find.return_value = mock_cursor
    mock_cursor.sort.return_value = mock_cursor  # この行を追加

    departments = get_all_departments()

    # 正しい診療科名リストが返されることを確認
    assert departments == ["内科", "外科", "小児科"]
    mock_department_collection.find.assert_called_once()
    assert mock_cursor.sort.call_count == 1


def test_create_department_empty_name(mock_department_collection):
    """診療科作成のテスト（空の名前）"""
    result = create_department("")
    assert result == False
    mock_department_collection.find_one.assert_not_called()


def test_create_department_existing(mock_department_collection):
    """診療科作成のテスト（既存の名前）"""
    mock_department_collection.find_one.return_value = {"name": "内科"}

    result, message = create_department("内科")

    assert result == False
    assert "この診療科は既に存在します" in message
    mock_department_collection.find_one.assert_called_once_with({"name": "内科"})


def test_create_department_success(mock_department_collection):
    """診療科作成のテスト（成功ケース）"""
    mock_department_collection.find_one.side_effect = [
        None,
        {"order": 5}
    ]

    result, message = create_department("新しい診療科")

    assert result == True
    assert "診療科を登録しました" in message
    assert mock_department_collection.insert_one.call_count == 1


def test_delete_department_with_prompts(mock_department_collection, mock_prompt_collection):
    """診療科削除のテスト（プロンプトが紐づいている場合）"""
    mock_department_collection.delete_one.return_value.deleted_count = 1

    result, message = delete_department("内科")

    assert result == True
    assert "診療科を削除しました" in message
    mock_department_collection.delete_one.assert_called_once_with({"name": "内科"})
    mock_prompt_collection.delete_many.assert_called_once_with({"department": "内科"})


def test_delete_department_success(mock_department_collection, mock_prompt_collection):
    """診療科削除のテスト（成功ケース）"""
    mock_prompt_collection.count_documents.return_value = 0
    mock_department_collection.delete_one.return_value.deleted_count = 1

    result, message = delete_department("内科")

    assert result == True
    assert "診療科を削除しました" in message
    mock_department_collection.delete_one.assert_called_once_with({"name": "内科"})
    mock_prompt_collection.delete_many.assert_called_once_with({"department": "内科"})


def test_delete_department_not_found(mock_department_collection, mock_prompt_collection):
    """診療科削除のテスト（診療科が見つからない場合）"""
    # 該当する診療科がない
    mock_department_collection.delete_one.return_value.deleted_count = 0

    result, message = delete_department("存在しない科")

    assert result == False
    assert "診療科が見つかりません" in message
    mock_department_collection.delete_one.assert_called_once_with({"name": "存在しない科"})
    # 診療科が見つからない場合はプロンプト削除が呼ばれないことを確認
    mock_prompt_collection.delete_many.assert_not_called()


@patch('utils.prompt_manager.get_config')
def test_initialize_default_prompt_existing(mock_get_config, mock_prompt_collection):
    """デフォルトプロンプト初期化のテスト（既存の場合）"""
    # デフォルトプロンプトが既に存在する
    mock_prompt_collection.find_one.return_value = {
        "department": "default",
        "name": "退院時サマリ",
        "content": "既存のプロンプト",
        "is_default": True
    }

    initialize_default_prompt()

    # 既に存在する場合は新たに作成されない
    mock_prompt_collection.find_one.assert_called_once_with({"department": "default", "is_default": True})
    mock_get_config.assert_not_called()
    assert mock_prompt_collection.insert_one.call_count == 0


@patch('utils.prompt_manager.get_config')
def test_initialize_default_prompt_new(mock_get_config, mock_prompt_collection):
    """デフォルトプロンプト初期化のテスト（新規作成）"""
    # デフォルトプロンプトが存在しない
    mock_prompt_collection.find_one.return_value = None
    # 設定からのプロンプト取得
    mock_config = {
        'PROMPTS': {
            'discharge_summary': 'デフォルトプロンプト内容'
        }
    }
    mock_get_config.return_value = mock_config

    initialize_default_prompt()

    # 新規作成される
    mock_prompt_collection.find_one.assert_called_once_with({"department": "default", "is_default": True})
    mock_get_config.assert_called_once()
    assert mock_prompt_collection.insert_one.call_count == 1
    # 挿入されるデータの確認
    insert_data = mock_prompt_collection.insert_one.call_args[0][0]
    assert insert_data["department"] == "default"
    assert insert_data["name"] == "退院時サマリ"
    assert insert_data["content"] == "デフォルトプロンプト内容"
    assert insert_data["is_default"] == True


def test_get_prompt_by_department_exists(mock_prompt_collection):
    """診療科プロンプト取得のテスト（存在する場合）"""
    # 指定した診療科のプロンプトが存在する
    expected_prompt = {
        "department": "内科",
        "name": "内科プロンプト",
        "content": "内科用の内容"
    }
    mock_prompt_collection.find_one.return_value = expected_prompt

    result = get_prompt_by_department("内科")

    assert result == expected_prompt
    mock_prompt_collection.find_one.assert_called_once_with({"department": "内科"})


def test_get_prompt_by_department_fallback(mock_prompt_collection):
    """診療科プロンプト取得のテスト（存在しない場合のフォールバック）"""
    # 指定した診療科のプロンプトが存在しない→デフォルトにフォールバック
    mock_prompt_collection.find_one.side_effect = [
        None,  # 最初の呼び出し（指定診療科）の結果
        {"department": "default", "content": "デフォルト内容"}  # 2回目の呼び出し（デフォルト）の結果
    ]

    result = get_prompt_by_department("存在しない科")

    assert result["department"] == "default"
    assert result["content"] == "デフォルト内容"
    assert mock_prompt_collection.find_one.call_count == 2
    # 1回目と2回目の呼び出し引数を確認
    assert mock_prompt_collection.find_one.call_args_list[0][0][0] == {"department": "存在しない科"}
    assert mock_prompt_collection.find_one.call_args_list[1][0][0] == {"department": "default", "is_default": True}


def test_get_all_prompts(mock_prompt_collection):
    """全プロンプト取得のテスト"""
    # テスト用のプロンプトデータ
    test_prompts = [
        {"department": "default", "name": "デフォルト"},
        {"department": "内科", "name": "内科用"}
    ]
    # ソート済みでfindの結果を返すよう設定
    mock_cursor = MagicMock()
    mock_cursor.__iter__.return_value = iter(test_prompts)
    mock_prompt_collection.find.return_value = mock_cursor
    mock_cursor.sort.return_value = mock_cursor  # この行を追加

    prompts = get_all_prompts()

    # 正しいプロンプトリストが返されることを確認
    assert prompts == test_prompts
    mock_prompt_collection.find.assert_called_once()
    assert mock_cursor.sort.call_count == 1


def test_create_or_update_prompt_empty_fields(mock_prompt_collection):
    """プロンプト作成/更新のテスト（未入力フィールドあり）"""
    # 空の入力があるケース
    result, message = create_or_update_prompt("", "名前", "内容")
    assert result == False
    assert "すべての項目を入力してください" in message

    result, message = create_or_update_prompt("内科", "", "内容")
    assert result == False
    assert "すべての項目を入力してください" in message

    result, message = create_or_update_prompt("内科", "名前", "")
    assert result == False
    assert "すべての項目を入力してください" in message

    mock_prompt_collection.find_one.assert_not_called()


def test_create_or_update_prompt_update(mock_prompt_collection):
    """プロンプト作成/更新のテスト（既存プロンプトの更新）"""
    # 既存のプロンプトがある場合
    mock_prompt_collection.find_one.return_value = {
        "department": "内科",
        "name": "旧名前",
        "content": "旧内容"
    }

    result, message = create_or_update_prompt("内科", "新名前", "新内容")

    assert result == True
    assert "プロンプトを更新しました" in message
    mock_prompt_collection.find_one.assert_called_once_with({"department": "内科"})
    # update_documentが呼ばれたことを確認
    assert mock_prompt_collection.update_one.call_count == 1
    update_args = mock_prompt_collection.update_one.call_args[0]
    assert update_args[0] == {"department": "内科"}
    assert update_args[1]["$set"]["name"] == "新名前"
    assert update_args[1]["$set"]["content"] == "新内容"


def test_create_or_update_prompt_create(mock_prompt_collection):
    """プロンプト作成/更新のテスト（新規プロンプトの作成）"""
    # 既存のプロンプトがない場合
    mock_prompt_collection.find_one.return_value = None

    result, message = create_or_update_prompt("新診療科", "新名前", "新内容")

    assert result == True
    assert "プロンプトを新規作成しました" in message
    mock_prompt_collection.find_one.assert_called_once_with({"department": "新診療科"})
    # insert_documentが呼ばれたことを確認
    assert mock_prompt_collection.insert_one.call_count == 1
    insert_args = mock_prompt_collection.insert_one.call_args[0][0]
    assert insert_args["department"] == "新診療科"
    assert insert_args["name"] == "新名前"
    assert insert_args["content"] == "新内容"
    assert insert_args["is_default"] == False


def test_delete_prompt_default(mock_prompt_collection):
    """プロンプト削除のテスト（デフォルトプロンプト）"""
    # デフォルトプロンプトは削除できない
    result, message = delete_prompt("default")

    assert result == False
    assert "デフォルトプロンプトは削除できません" in message
    mock_prompt_collection.delete_one.assert_not_called()


def test_delete_prompt_success(mock_prompt_collection):
    """プロンプト削除のテスト（成功ケース）"""
    # 削除成功
    mock_prompt_collection.delete_one.return_value.deleted_count = 1

    result, message = delete_prompt("内科")

    assert result == True
    assert "プロンプトと関連する診療科を削除しました" in message
    mock_prompt_collection.delete_one.assert_called_once_with({"department": "内科"})


def test_delete_prompt_not_found(mock_prompt_collection):
    """プロンプト削除のテスト（プロンプトが見つからない場合）"""
    # 該当するプロンプトがない
    mock_prompt_collection.delete_one.return_value.deleted_count = 0

    result, message = delete_prompt("存在しない科")

    assert result == False
    assert "プロンプトが見つかりません" in message
    mock_prompt_collection.delete_one.assert_called_once_with({"department": "存在しない科"})


@patch('utils.prompt_manager.initialize_default_prompt')
@patch('utils.prompt_manager.initialize_departments')
def test_initialize_database(mock_init_depts, mock_init_prompt):
    """データベース初期化のテスト"""
    initialize_database()

    mock_init_prompt.assert_called_once()
    mock_init_depts.assert_called_once()
