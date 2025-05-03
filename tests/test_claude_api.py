import pytest
from unittest.mock import patch, MagicMock

from utils.claude_api import (
    initialize_claude, create_discharge_summary_prompt, generate_discharge_summary
)


@patch('utils.claude_api.CLAUDE_API_KEY')
def test_initialize_claude_success(mock_api_key):
    """Claude APIの初期化が成功するケースのテスト"""
    # 認証情報が設定されている場合
    mock_api_key.__bool__.return_value = True
    mock_api_key.__str__.return_value = "test_api_key"

    result = initialize_claude()

    assert result is True


@patch('utils.claude_api.CLAUDE_API_KEY')
def test_initialize_claude_no_credentials(mock_api_key):
    """認証情報がない場合のClaude API初期化テスト"""
    # 認証情報が設定されていない場合
    mock_api_key.__bool__.return_value = False
    mock_api_key.__str__.return_value = ""

    with pytest.raises(Exception) as exc_info:
        initialize_claude()

    assert "API初期化エラー" in str(exc_info.value)


@patch('utils.claude_api.get_prompt_by_department')
@patch('utils.claude_api.get_config')
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


@patch('utils.claude_api.get_prompt_by_department')
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


@patch('utils.claude_api.initialize_claude')
@patch('utils.claude_api.Anthropic')
@patch('utils.claude_api.create_discharge_summary_prompt')
def test_generate_discharge_summary_success(mock_create_prompt, mock_anthropic_class, mock_initialize):
    """退院時サマリ生成が成功するケースのテスト"""
    mock_initialize.return_value = True
    mock_create_prompt.return_value = "テストプロンプト"

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_content = MagicMock()
    mock_content.text = "生成された退院時サマリ"
    mock_response.content = [mock_content]
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 200

    mock_client.messages.create.return_value = mock_response
    mock_anthropic_class.return_value = mock_client
    with patch('utils.claude_api.CLAUDE_MODEL', "claude-3-opus-20240229"):
        result, input_tokens, output_tokens = generate_discharge_summary("テストカルテデータ", "内科")

    # 検証
    assert result == "生成された退院時サマリ"
    assert input_tokens == 100
    assert output_tokens == 200
    mock_initialize.assert_called_once()
    mock_create_prompt.assert_called_once_with("テストカルテデータ", "内科")
    mock_client.messages.create.assert_called_once()
    create_args = mock_client.messages.create.call_args[1]
    assert create_args["model"] == "claude-3-opus-20240229"


@patch('utils.claude_api.initialize_claude')
@patch('utils.claude_api.CLAUDE_MODEL')
@patch('utils.claude_api.Anthropic')
@patch('utils.claude_api.create_discharge_summary_prompt')
def test_generate_discharge_summary_empty_response(mock_create_prompt, mock_anthropic_class, mock_model_name, mock_initialize):
    """レスポンスが空の場合のテスト"""
    # 初期化成功
    mock_initialize.return_value = True

    # モデル名
    mock_model_name.__str__.return_value = "claude-3-opus-20240229"

    # プロンプト作成
    mock_create_prompt.return_value = "テストプロンプト"

    # モックのAnthropicクライアントとレスポンスの設定（空のレスポンス）
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = []
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 0

    mock_client.messages.create.return_value = mock_response
    mock_anthropic_class.return_value = mock_client

    # 関数を実行
    result, input_tokens, output_tokens = generate_discharge_summary("テストカルテデータ")

    # 検証
    assert result == "レスポンスが空でした"
    assert input_tokens == 100
    assert output_tokens == 0


@patch('utils.claude_api.initialize_claude')
def test_generate_discharge_summary_error(mock_initialize):
    """サマリ生成時にエラーが発生するケースのテスト"""
    mock_initialize.side_effect = Exception("APIエラー")

    with pytest.raises(Exception) as exc_info:
        generate_discharge_summary("テストカルテデータ")

    assert "Claude APIでエラーが発生しました" in str(exc_info.value)
