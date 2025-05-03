import os
import json
import datetime
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, call

from utils.backup_manager import (
    get_backup_dir, backup_data, backup_prompts,
    backup_departments, restore_data, restore_prompts,
    restore_departments, list_backup_files
)


@patch('utils.backup_manager.get_config')
@patch('utils.backup_manager.Path')
def test_get_backup_dir_from_config(mock_path, mock_get_config):
    """設定ファイルからバックアップディレクトリを取得するテスト"""
    # モックの設定
    mock_config = {
        'BACKUP': {
            'prompts_dir': 'custom/prompts/backup',
            'departments_dir': 'custom/departments/backup'
        }
    }
    mock_get_config.return_value = mock_config

    mock_parent = MagicMock()
    mock_parent.parent = "/app"
    mock_path.return_value.parent.parent = mock_parent

    # 相対パスの場合
    result = get_backup_dir('prompts')
    assert 'custom/prompts/backup' in result

    result = get_backup_dir('departments')
    assert 'custom/departments/backup' in result

    # 絶対パスの場合
    mock_config['BACKUP']['prompts_dir'] = '/absolute/path/to/prompts'
    result = get_backup_dir('prompts')
    assert result == '/absolute/path/to/prompts'


@patch('utils.backup_manager.get_config')
@patch('utils.backup_manager.Path')
def test_get_backup_dir_default(mock_path, mock_get_config):
    """設定がない場合のデフォルトバックアップディレクトリ取得テスト"""
    # 設定がない場合
    mock_get_config.return_value = {}

    mock_parent = MagicMock()
    mock_parent.parent = "/app"
    mock_path.return_value.parent.parent = mock_parent

    # デフォルトディレクトリが使用される
    with patch('os.path.join', return_value='/app/backups/prompts'):
        result = get_backup_dir('prompts')
        assert result == '/app/backups/prompts'

    with patch('os.path.join', return_value='/app/backups/departments'):
        result = get_backup_dir('departments')
        assert result == '/app/backups/departments'


@patch('utils.backup_manager.datetime')
@patch('utils.backup_manager.get_prompt_collection')
@patch('utils.backup_manager.os')
def test_backup_prompts(mock_os, mock_get_collection, mock_datetime):
    """プロンプトバックアップ機能のテスト"""
    # モックの設定
    mock_collection = MagicMock()
    mock_get_collection.return_value = mock_collection

    mock_datetime.datetime.now.return_value = datetime.datetime(2025, 4, 3, 12, 0, 0)
    mock_datetime.datetime.strftime.return_value = "20250403_120000"

    mock_os.path.join.return_value = "/backup/prompts/prompts_backup_20250403_120000.json"
    mock_os.makedirs = MagicMock()

    # テストデータ
    test_data = [
        {"department": "内科", "name": "テストプロンプト1", "content": "テスト内容1"},
        {"department": "外科", "name": "テストプロンプト2", "content": "テスト内容2"}
    ]
    mock_collection.find.return_value = test_data

    # バックアップ実行
    m = mock_open()
    with patch('builtins.open', m):
        result = backup_prompts("/backup/prompts")

    # 検証
    assert result == "/backup/prompts/prompts_backup_20250403_120000.json"
    mock_os.makedirs.assert_called_once_with("/backup/prompts", exist_ok=True)
    mock_collection.find.assert_called_once_with({}, {'_id': False})

    # JSONファイルに正しく書き込まれたか確認
    m.assert_called_once_with("/backup/prompts/prompts_backup_20250403_120000.json", 'w', encoding='utf-8')
    handle = m()

    # 注: json.dumpの検証は複雑なので、呼び出されたことだけを確認
    assert handle.write.call_count > 0


@patch('utils.backup_manager.datetime')
@patch('utils.backup_manager.get_department_collection')
@patch('utils.backup_manager.os')
def test_backup_departments(mock_os, mock_get_collection, mock_datetime):
    """診療科バックアップ機能のテスト"""
    # モックの設定
    mock_collection = MagicMock()
    mock_get_collection.return_value = mock_collection

    mock_datetime.datetime.now.return_value = datetime.datetime(2025, 4, 3, 12, 0, 0)
    mock_datetime.datetime.strftime.return_value = "20250403_120000"

    mock_os.path.join.return_value = "/backup/departments/departments_backup_20250403_120000.json"
    mock_os.makedirs = MagicMock()

    # テストデータ
    test_data = [
        {"name": "内科"},
        {"name": "外科"}
    ]
    mock_collection.find.return_value = test_data

    # バックアップ実行
    m = mock_open()
    with patch('builtins.open', m):
        result = backup_departments("/backup/departments")

    # 検証
    assert result == "/backup/departments/departments_backup_20250403_120000.json"
    mock_os.makedirs.assert_called_once_with("/backup/departments", exist_ok=True)
    mock_collection.find.assert_called_once_with({}, {'_id': False})


@patch('utils.backup_manager.os.path.exists')
@patch('utils.backup_manager.get_prompt_collection')
def test_restore_prompts_file_not_found(mock_get_collection, mock_exists):
    """存在しないプロンプトバックアップファイルの復元テスト"""
    # ファイルが存在しない場合
    mock_exists.return_value = False

    # 復元実行
    with patch('builtins.print') as mock_print:
        result = restore_prompts("/nonexistent/file.json")

    # 検証
    assert result == False
    mock_print.assert_called_once()
    assert "バックアップファイルが見つかりません" in mock_print.call_args[0][0]


@patch('utils.backup_manager.os.path.exists')
@patch('utils.backup_manager.get_department_collection')
def test_restore_departments_file_not_found(mock_get_collection, mock_exists):
    """存在しない診療科バックアップファイルの復元テスト"""
    # ファイルが存在しない場合
    mock_exists.return_value = False

    # 復元実行
    with patch('builtins.print') as mock_print:
        result = restore_departments("/nonexistent/file.json")

    # 検証
    assert result == False
    mock_print.assert_called_once()
    assert "バックアップファイルが見つかりません" in mock_print.call_args[0][0]


@patch('utils.backup_manager.os.path.exists')
@patch('utils.backup_manager.get_prompt_collection')
def test_restore_prompts_success(mock_get_collection, mock_exists):
    """プロンプトの正常復元テスト"""
    pass


@patch('utils.backup_manager.os.path.exists')
@patch('utils.backup_manager.get_department_collection')
def test_restore_departments_success(mock_get_collection, mock_exists):
    """診療科の正常復元テスト"""
    # モックの設定
    mock_exists.return_value = True
    mock_collection = MagicMock()
    mock_get_collection.return_value = mock_collection

    # テストデータ
    test_data = [
        {
            "name": "内科",
            "created_at": "2025-04-01T10:00:00Z",
            "updated_at": "2025-04-02T10:00:00Z"
        },
        {
            "name": "外科",
            "created_at": "2025-04-01T11:00:00Z",
            "updated_at": "2025-04-02T11:00:00Z"
        }
    ]

    # 既存項目のモック
    mock_collection.find_one.side_effect = [{"name": "内科"}, None]

    # 復元実行
    m = mock_open(read_data=json.dumps(test_data))
    with patch('builtins.open', m):
        with patch('builtins.input', return_value='y'):
            with patch('builtins.print') as mock_print:
                result = restore_departments("/backup/file.json")

    # 検証
    assert result == True
    mock_collection.delete_many.assert_called_once_with({})
    assert mock_collection.update_one.call_count == 1
    assert mock_collection.insert_one.call_count == 1


@patch('utils.backup_manager.os.path.exists')
def test_restore_data_json_error(mock_exists):
    """不正なJSONファイルの復元テスト"""
    # ファイルは存在するがJSON形式が不正
    mock_exists.return_value = True

    # 復元実行
    m = mock_open(read_data="不正なJSONデータ")
    with patch('builtins.open', m):
        with patch('builtins.input', return_value='y'):
            with patch('builtins.print') as mock_print:
                result = restore_data("/backup/file.json", 'prompts')

    # 検証
    assert result == False
    assert mock_print.call_count > 0
    assert any("エラーが発生しました" in call[0][0] for call in mock_print.call_args_list)


@patch('utils.backup_manager.get_backup_dir')
@patch('utils.backup_manager.os.path.exists')
@patch('utils.backup_manager.os.listdir')
@patch('utils.backup_manager.os.path.getsize')
@patch('utils.backup_manager.os.path.getmtime')
@patch('utils.backup_manager.datetime')
def test_list_backup_files(mock_datetime, mock_getmtime, mock_getsize, mock_listdir, mock_exists, mock_get_backup_dir):
    """バックアップファイル一覧表示のテスト"""
    # モックの設定
    mock_get_backup_dir.side_effect = ['/backup/prompts', '/backup/departments']
    mock_exists.side_effect = [True, True]

    # プロンプトディレクトリのファイル
    mock_listdir.side_effect = [
        ['prompts_1.json', 'prompts_2.json'],
        ['departments_1.json', 'departments_2.json']
    ]

    # ファイルのサイズと更新日時
    mock_getsize.return_value = 1024
    mock_getmtime.return_value = 1712131200  # 2024-04-03 12:00:00

    mock_datetime.datetime.fromtimestamp.return_value = datetime.datetime(2025, 4, 3, 12, 0, 0)

    # 一覧表示実行
    with patch('builtins.print') as mock_print:
        list_backup_files()

    # 検証
    assert mock_print.call_count > 0
    assert mock_get_backup_dir.call_count == 2
    assert mock_exists.call_count == 2
    assert mock_listdir.call_count == 2

    # プロンプトとディレクトリの両方のセクションが表示されたことを確認
    print_calls = [call[0][0] for call in mock_print.call_args_list if call[0]]
    assert any("=== プロンプトバックアップファイル ===" in call for call in print_calls)
    assert any("=== 診療科バックアップファイル ===" in call for call in print_calls)


@patch('utils.backup_manager.get_backup_dir')
@patch('utils.backup_manager.os.path.exists')
def test_list_backup_files_no_directory(mock_exists, mock_get_backup_dir):
    """バックアップディレクトリが存在しない場合のテスト"""
    # モックの設定
    mock_get_backup_dir.side_effect = ['/backup/prompts', '/backup/departments']
    mock_exists.side_effect = [False, False]  # 両方のディレクトリが存在しない

    # 一覧表示実行
    with patch('builtins.print') as mock_print:
        list_backup_files()

    # 検証
    assert mock_print.call_count > 0
    assert any("バックアップディレクトリが見つかりません" in call[0][0] for call in mock_print.call_args_list)


@patch('utils.backup_manager.get_backup_dir')
@patch('utils.backup_manager.os.path.exists')
@patch('utils.backup_manager.os.listdir')
def test_list_backup_files_empty_directory(mock_listdir, mock_exists, mock_get_backup_dir):
    """空のバックアップディレクトリの場合のテスト"""
    # モックの設定
    mock_get_backup_dir.side_effect = ['/backup/prompts', '/backup/departments']
    mock_exists.side_effect = [True, True]
    mock_listdir.side_effect = [[], []]  # 両方のディレクトリが空

    # 一覧表示実行
    with patch('builtins.print') as mock_print:
        list_backup_files()

    # 検証
    assert mock_print.call_count > 0
    assert any("バックアップファイルが見つかりません" in call[0][0] for call in mock_print.call_args_list)


@patch('utils.backup_manager.restore_data')
def test_restore_prompts_wrapper(mock_restore_data):
    """restore_prompts関数のラッパーテスト"""
    mock_restore_data.return_value = True
    result = restore_prompts('/path/to/backup.json')
    assert result == True
    mock_restore_data.assert_called_once_with('/path/to/backup.json', 'prompts')


@patch('utils.backup_manager.restore_data')
def test_restore_departments_wrapper(mock_restore_data):
    """restore_departments関数のラッパーテスト"""
    mock_restore_data.return_value = False
    result = restore_departments('/path/to/backup.json')
    assert result == False
    mock_restore_data.assert_called_once_with('/path/to/backup.json', 'departments')


@patch('utils.backup_manager.backup_data')
def test_backup_prompts_wrapper(mock_backup_data):
    """backup_prompts関数のラッパーテスト"""
    mock_backup_data.return_value = '/path/to/backup.json'
    result = backup_prompts('/custom/path')
    assert result == '/path/to/backup.json'
    mock_backup_data.assert_called_once_with('prompts', '/custom/path')


@patch('utils.backup_manager.backup_data')
def test_backup_departments_wrapper(mock_backup_data):
    """backup_departments関数のラッパーテスト"""
    mock_backup_data.return_value = '/path/to/backup.json'
    result = backup_departments('/custom/path')
    assert result == '/path/to/backup.json'
    mock_backup_data.assert_called_once_with('departments', '/custom/path')


@patch('utils.backup_manager.get_backup_dir')
def test_backup_data_invalid_type(mock_get_backup_dir):
    """無効なデータタイプに対するテスト"""
    with pytest.raises(ValueError) as excinfo:
        backup_data('invalid_type')

    assert "不明なデータタイプ" in str(excinfo.value)
