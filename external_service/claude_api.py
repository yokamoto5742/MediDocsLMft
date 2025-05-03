import os
import anthropic
from anthropic import Anthropic

from utils.config import get_config, CLAUDE_API_KEY, CLAUDE_MODEL
from utils.constants import MESSAGES
from utils.prompt_manager import get_prompt_by_department
from utils.exceptions import APIError


def initialize_claude():
    try:
        if CLAUDE_API_KEY:
            return True
        else:
            raise APIError(MESSAGES["API_CREDENTIALS_MISSING"])
    except Exception as e:
        raise APIError(f"Claude API初期化エラー: {str(e)}")


def create_discharge_summary_prompt(medical_text, additional_info="", department="default"):
    prompt_data = get_prompt_by_department(department)

    if not prompt_data:
        config = get_config()
        prompt_template = config['PROMPTS']['discharge_summary']
    else:
        prompt_template = prompt_data['content']

    prompt = f"{prompt_template}\n\n【カルテ情報】\n{medical_text}"
    if additional_info:
        prompt += f"\n{additional_info}"
    return prompt


def claude_generate_discharge_summary(medical_text, additional_info="", department="default"):
    try:
        initialize_claude()
        model_name = CLAUDE_MODEL
        client = Anthropic(api_key=CLAUDE_API_KEY)

        prompt = create_discharge_summary_prompt(medical_text, additional_info, department)

        response = client.messages.create(
            model=model_name,
            max_tokens=5000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        if response.content:
            summary_text = response.content[0].text
        else:
            summary_text = "レスポンスが空でした"

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

        return summary_text, input_tokens, output_tokens

    except APIError as e:
        raise e
    except Exception as e:
        raise APIError(f"Claude APIでエラーが発生しました: {str(e)}")
