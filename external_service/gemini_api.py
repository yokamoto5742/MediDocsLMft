import json
import os

from google import genai
from google.genai import types

from utils.config import get_config, GEMINI_CREDENTIALS, GEMINI_MODEL, GEMINI_THINKING_BUDGET
from utils.constants import MESSAGES
from utils.prompt_manager import get_prompt_by_department
from utils.exceptions import APIError


def initialize_gemini():
    try:
        if GEMINI_CREDENTIALS:
            client = genai.Client(api_key=GEMINI_CREDENTIALS)
            return client
        else:
            raise APIError(MESSAGES["API_CREDENTIALS_MISSING"])

    except Exception as e:
        raise APIError(f"Gemini API初期化エラー: {str(e)}")


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


def gemini_generate_discharge_summary(medical_text, additional_info="", department="default", model_name=None):
    try:
        client = initialize_gemini()
        if not model_name:
            model_name = GEMINI_MODEL

        prompt = create_discharge_summary_prompt(medical_text, additional_info, department)

        if GEMINI_THINKING_BUDGET:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(
                        thinking_budget=GEMINI_THINKING_BUDGET
                    )
                )
            )
        else:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )

        if hasattr(response, 'text'):
            summary_text = response.text
        else:
            summary_text = str(response)

        input_tokens = 0
        output_tokens = 0

        if hasattr(response, 'usage_metadata'):
            input_tokens = response.usage_metadata.prompt_token_count
            output_tokens = response.usage_metadata.candidates_token_count

        return summary_text, input_tokens, output_tokens

    except APIError as e:
        raise e
    except Exception as e:
        raise APIError(f"Gemini APIでエラーが発生しました: {str(e)}")
