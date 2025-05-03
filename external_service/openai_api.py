import os
from openai import OpenAI

from utils.config import get_config, OPENAI_API_KEY, OPENAI_MODEL
from utils.constants import MESSAGES
from utils.prompt_manager import get_prompt_by_department
from utils.exceptions import APIError


def initialize_openai():
    try:
        if OPENAI_API_KEY:
            return True
        else:
            raise APIError(MESSAGES["API_CREDENTIALS_MISSING"])
    except Exception as e:
        raise APIError(f"OpenAI API初期化エラー: {str(e)}")


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


def openai_generate_discharge_summary(medical_text, additional_info="", department="default"):
    try:
        initialize_openai()
        model_name = OPENAI_MODEL
        client = OpenAI(api_key=OPENAI_API_KEY)

        prompt = create_discharge_summary_prompt(medical_text, additional_info, department)

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "あなたは経験豊富な医療文書作成の専門家です。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=10000,
        )

        if response.choices and response.choices[0].message.content:
            summary_text = response.choices[0].message.content
        else:
            summary_text = "レスポンスが空でした"

        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens

        return summary_text, input_tokens, output_tokens

    except APIError as e:
        raise e
    except Exception as e:
        raise APIError(f"OpenAI APIでエラーが発生しました: {str(e)}")
