import os
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from utils.env_loader import load_environment_variables


@patch('utils.env_loader.print')
@patch('utils.env_loader.os.environ.get')
def test_load_env_vars_with_system_env(mock_environ_get, mock_print):
    """システム環境変数が設定されている場合のテスト"""
    # システム環境変数が設定されている状態をモック
    mock_environ_get.return_value = "mongodb://localhost:27017"

    # 関数を実行
    load_environment_variables()

    # 関数が期待どおりに動作したことを確認
    mock_environ_get.assert_called_once_with("MONGODB_URI")
    mock_print.assert_called_once_with("システム環境変数が検出されました。")


@patch('utils.env_loader.print')
@patch('utils.env_loader.os.environ.get')
@patch('utils.env_loader.load_dotenv')
@patch('utils.env_loader.os.path.exists')
@patch('utils.env_loader.os.path.join')
def test_load_env_vars_with_dotenv_file(mock_join, mock_exists, mock_load_dotenv, mock_environ_get, mock_print):
    """システム環境変数が設定されておらず、.envファイルが存在する場合のテスト"""
    # システム環境変数が設定されていない状態をモック
    mock_environ_get.return_value = None

    # .envファイルが存在する状態をモック
    mock_exists.return_value = True
    mock_join.return_value = "/app/.env"

    # 関数を実行
    load_environment_variables()

    # 関数が期待どおりに動作したことを確認
    mock_environ_get.assert_called_once_with("MONGODB_URI")
    mock_load_dotenv.assert_called_once_with("/app/.env")
    mock_print.assert_called_once_with("環境変数を.envファイルから読み込みました")


@patch('utils.env_loader.print')
@patch('utils.env_loader.os.environ.get')
@patch('utils.env_loader.load_dotenv')
@patch('utils.env_loader.os.path.exists')
@patch('utils.env_loader.os.path.join')
def test_load_env_vars_without_env_file(mock_join, mock_exists, mock_load_dotenv, mock_environ_get, mock_print):
    """システム環境変数が設定されておらず、.envファイルも存在しない場合のテスト"""
    # システム環境変数が設定されていない状態をモック
    mock_environ_get.return_value = None

    # .envファイルが存在しない状態をモック
    mock_exists.return_value = False
    mock_join.return_value = "/app/.env"

    # 関数を実行
    load_environment_variables()

    # 関数が期待どおりに動作したことを確認
    mock_environ_get.assert_called_once_with("MONGODB_URI")
    mock_load_dotenv.assert_not_called()
    mock_print.assert_called_once_with(
        "警告: .envファイルが見つかりません。システム環境変数が設定されていることを確認してください。")


@patch('utils.env_loader.print')
@patch('utils.env_loader.os.environ.get')
@patch('utils.env_loader.load_dotenv')
@patch('utils.env_loader.os.path.exists')
@patch('utils.env_loader.os.path.join')
@patch('utils.env_loader.Path')
def test_correct_env_path_construction(mock_path, mock_join, mock_exists, mock_load_dotenv, mock_environ_get,
                                       mock_print):
    """環境変数ファイルのパスが正しく構築されるかテスト"""
    # システム環境変数が設定されていない状態をモック
    mock_environ_get.return_value = None

    # Pathモックの設定
    mock_path_instance = MagicMock()
    mock_parent = MagicMock()
    mock_parent.parent = "/app"
    mock_path_instance.parent.parent = mock_parent
    mock_path.return_value = mock_path_instance

    # .envファイルが存在する状態をモック
    mock_exists.return_value = True
    mock_join.return_value = "/app/.env"

    # 関数を実行
    load_environment_variables()

    # 関数が期待どおりに動作したことを確認
    # この行が修正されています - モックオブジェクトの親への参照を期待する
    mock_join.assert_called_once_with(mock_path_instance.parent.parent, '.env')
    mock_exists.assert_called_once_with("/app/.env")
    mock_load_dotenv.assert_called_once_with("/app/.env")
