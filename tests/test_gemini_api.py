import os
import pytest
from unittest.mock import patch, MagicMock

from utils.gemini_api import (
    initialize_gemini, create_discharge_summary_prompt, generate_discharge_summary
)


@patch('utils.gemini_api.genai')
@patch('utils.gemini_api.GEMINI_CREDENTIALS')
def test_initialize_gemini_success(mock_credentials, mock_genai):
    """Gemini APIの初期化が成功するケースのテスト"""
    # 認証情報が設定されている場合
    mock_credentials.__bool__.return_value = True
    mock_credentials.__str__.return_value = "test_api_key"

    result = initialize_gemini()

    assert result is True
    mock_genai.configure.assert_called_once_with(api_key=mock_credentials)


@patch('utils.gemini_api.genai')
@patch('utils.gemini_api.GEMINI_CREDENTIALS')
def test_initialize_gemini_no_credentials(mock_credentials, mock_genai):
    """認証情報がない場合のGemini API初期化テスト"""
    # 認証情報が設定されていない場合
    mock_credentials.__bool__.return_value = False
    mock_credentials.__str__.return_value = ""

    with pytest.raises(Exception) as exc_info:
        initialize_gemini()

    assert "Gemini API初期化エラー" in str(exc_info.value)


@patch('utils.gemini_api.genai')
@patch('utils.gemini_api.GEMINI_CREDENTIALS')
def test_initialize_gemini_api_error(mock_credentials, mock_genai):
    """Gemini API初期化時にエラーが発生するケースのテスト"""
    # 認証情報はあるが、API初期化でエラーが発生する場合
    mock_credentials.__bool__.return_value = True
    mock_credentials.__str__.return_value = "test_api_key"
    mock_genai.configure.side_effect = Exception("API Error")

    with pytest.raises(Exception) as exc_info:
        initialize_gemini()

    assert "Gemini API初期化エラー" in str(exc_info.value)
    mock_genai.configure.assert_called_once()


@patch('utils.gemini_api.get_prompt_by_department')
@patch('utils.gemini_api.get_config')
def test_create_discharge_summary_prompt_default(mock_get_config, mock_get_prompt):
    """デフォルト診療科のプロンプト作成テスト"""
    # プロンプトデータが見つからない場合
    mock_get_prompt.return_value = None

    # 設定ファイルからデフォルトプロンプトを取得
    mock_config = {
        'PROMPTS': {
            'discharge_summary': 'デフォルトプロンプトテンプレート'
        }
    }
    mock_get_config.return_value = mock_config

    medical_text = "テストカルテデータ"

    prompt = create_discharge_summary_prompt(medical_text)

    assert "デフォルトプロンプトテンプレート" in prompt
    assert "テストカルテデータ" in prompt
    mock_get_prompt.assert_called_once_with("default")


@patch('utils.gemini_api.get_prompt_by_department')
def test_create_discharge_summary_prompt_with_department(mock_get_prompt):
    """特定の診療科のプロンプト作成テスト"""
    # 特定の診療科のプロンプトデータ
    mock_get_prompt.return_value = {
        'content': '内科用プロンプトテンプレート'
    }

    medical_text = "テストカルテデータ"
    department = "内科"

    prompt = create_discharge_summary_prompt(medical_text, department)

    assert "内科用プロンプトテンプレート" in prompt
    assert "テストカルテデータ" in prompt
    mock_get_prompt.assert_called_once_with("内科")


@patch('utils.gemini_api.initialize_gemini')
@patch('utils.gemini_api.os.environ.get')
@patch('utils.gemini_api.genai.GenerativeModel')
@patch('utils.gemini_api.create_discharge_summary_prompt')
def test_generate_discharge_summary_success(mock_create_prompt, mock_model_class, mock_environ_get, mock_initialize):
    """退院時サマリ生成が成功するケースのテスト"""
    # 初期化成功
    mock_initialize.return_value = True

    # 環境変数からモデル名を取得
    mock_environ_get.return_value = "gemini-pro"

    # プロンプト作成
    mock_create_prompt.return_value = "テストプロンプト"

    # モデルとレスポンスのモック
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "生成された退院時サマリ"

    mock_model.generate_content.return_value = mock_response
    mock_model_class.return_value = mock_model

    # 関数を実行
    result = generate_discharge_summary("テストカルテデータ", "内科")

    # 検証
    assert result[0] == "生成された退院時サマリ"
    mock_initialize.assert_called_once()
    mock_model_class.assert_called_once_with("gemini-2.5-pro-exp-03-25")
    mock_create_prompt.assert_called_once_with("テストカルテデータ", "内科")
    mock_model.generate_content.assert_called_once_with("テストプロンプト")


@patch('utils.gemini_api.initialize_gemini')
@patch('utils.gemini_api.os.environ.get')
@patch('utils.gemini_api.genai.GenerativeModel')
@patch('utils.gemini_api.create_discharge_summary_prompt')
def test_generate_discharge_summary_no_text_attribute(mock_create_prompt, mock_model_class, mock_environ_get,
                                                      mock_initialize):
    """レスポンスにtextプロパティがない場合のテスト"""
    # 初期化成功
    mock_initialize.return_value = True

    # 環境変数からモデル名を取得
    mock_environ_get.return_value = "gemini-pro"

    # プロンプト作成
    mock_create_prompt.return_value = "テストプロンプト"

    # モデルとレスポンスのモック (textプロパティなし)
    mock_model = MagicMock()

    # カスタムクラスを使用してtext属性なしのオブジェクトを作成
    class MockResponse:
        def __str__(self):
            return "文字列化されたレスポンス"

    mock_response = MockResponse()

    mock_model.generate_content.return_value = mock_response
    mock_model_class.return_value = mock_model

    # 関数を実行
    result = generate_discharge_summary("テストカルテデータ")

    # 検証
    assert result[0] == "文字列化されたレスポンス"
    mock_initialize.assert_called_once()


@patch('utils.gemini_api.initialize_gemini')
def test_generate_discharge_summary_error(mock_initialize):
    """サマリ生成時にエラーが発生するケースのテスト"""
    mock_initialize.side_effect = Exception("APIエラー")

    with pytest.raises(Exception) as exc_info:
        generate_discharge_summary("テストカルテデータ")

    assert "Gemini APIでエラーが発生しました" in str(exc_info.value)
