import datetime
import threading
import time
import queue
import pytz

import streamlit as st

from external_service.claude_api import claude_generate_discharge_summary
from external_service.gemini_api import gemini_generate_discharge_summary
from external_service.openai_api import openai_generate_discharge_summary
from utils.constants import APP_TYPE, DOCUMENT_NAME, MESSAGES
from utils.error_handlers import handle_error
from utils.exceptions import APIError
from utils.text_processor import format_discharge_summary, parse_discharge_summary
from utils.db import get_usage_collection
from utils.config import GEMINI_CREDENTIALS, CLAUDE_API_KEY, OPENAI_API_KEY, GEMINI_MODEL, GEMINI_FLASH_MODEL, OPENAI_MODEL, MAX_INPUT_TOKENS, MIN_INPUT_TOKENS

JST = pytz.timezone('Asia/Tokyo')


def generate_summary_task(input_text, selected_department, selected_model, result_queue, additional_info=""):
    try:
        if selected_model == "Claude" and CLAUDE_API_KEY:
            discharge_summary, input_tokens, output_tokens = claude_generate_discharge_summary(
                input_text,
                additional_info,
                selected_department,
            )
            model_detail = selected_model
        elif selected_model == "Gemini_Pro" and GEMINI_MODEL and GEMINI_CREDENTIALS:
            discharge_summary, input_tokens, output_tokens = gemini_generate_discharge_summary(
                input_text,
                additional_info,
                selected_department,
                GEMINI_MODEL,
            )
            model_detail = GEMINI_MODEL
        elif selected_model == "Gemini_Flash" and GEMINI_FLASH_MODEL and GEMINI_CREDENTIALS:
            discharge_summary, input_tokens, output_tokens = gemini_generate_discharge_summary(
                input_text,
                additional_info,
                selected_department,
                GEMINI_FLASH_MODEL,
            )
            model_detail = GEMINI_FLASH_MODEL
        elif selected_model == "GPT4.1" and OPENAI_API_KEY:
            try:
                discharge_summary, input_tokens, output_tokens = openai_generate_discharge_summary(
                    input_text,
                    additional_info,
                    selected_department,
                )
                model_detail = selected_model
            except Exception as e:
                error_str = str(e)
                if "insufficient_quota" in error_str or "exceeded your current quota" in error_str:
                    raise APIError("OpenAI APIのクォータを超過しています。請求情報を確認するか、管理者に連絡してください。")
                else:
                    raise e
        else:
            raise APIError(MESSAGES["NO_API_CREDENTIALS"])

        discharge_summary = format_discharge_summary(discharge_summary)
        parsed_summary = parse_discharge_summary(discharge_summary)

        result_queue.put({
            "success": True,
            "discharge_summary": discharge_summary,
            "parsed_summary": parsed_summary,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "model_detail": model_detail
        })

    except Exception as e:
        result_queue.put({"success": False, "error": e})


@handle_error
def process_discharge_summary(input_text, additional_info=""):
    if not GEMINI_CREDENTIALS and not CLAUDE_API_KEY:
        raise APIError(MESSAGES["NO_API_CREDENTIALS"])

    if not input_text:
        st.warning(MESSAGES["NO_INPUT"])
        return

    input_length = len(input_text.strip())
    if input_length < MIN_INPUT_TOKENS:
        st.warning(f"{MESSAGES['INPUT_TOO_SHORT']}")
        return

    if input_length > MAX_INPUT_TOKENS:
        st.warning(f"{MESSAGES['INPUT_TOO_LONG']}")
        return

    try:
        start_time = datetime.datetime.now()
        status_placeholder = st.empty()
        result_queue = queue.Queue()

        available_models = getattr(st.session_state, "available_models", [])
        selected_model = getattr(st.session_state, "selected_model",
                                 available_models[0] if available_models else None)
        selected_department = getattr(st.session_state, "selected_department", "default")

        summary_thread = threading.Thread(
            target=generate_summary_task,
            args=(input_text, selected_department, selected_model, result_queue, additional_info)
        )
        summary_thread.start()
        elapsed_time = 0

        with st.spinner("退院時サマリを作成中..."):
            status_placeholder.text(f"⏱️ 経過時間: {elapsed_time}秒")
            while summary_thread.is_alive():
                time.sleep(1)
                elapsed_time = int((datetime.datetime.now() - start_time).total_seconds())
                status_placeholder.text(f"⏱️ 経過時間: {elapsed_time}秒")

        summary_thread.join()
        status_placeholder.empty()
        result = result_queue.get()

        if result["success"]:
            st.session_state.discharge_summary = result["discharge_summary"]
            st.session_state.parsed_summary = result["parsed_summary"]

            input_tokens = result["input_tokens"]
            output_tokens = result["output_tokens"]
            model_detail = result["model_detail"]
            end_time = datetime.datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            st.session_state.summary_generation_time = processing_time

            try:
                usage_collection = get_usage_collection()
                now_jst = datetime.datetime.now().astimezone(JST)
                usage_data = {
                    "date": now_jst,
                    "app_type": APP_TYPE,
                    "document_name": DOCUMENT_NAME,
                    "model_detail": model_detail,
                    "department": selected_department,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                    "processing_time": round(processing_time)
                }
                usage_collection.insert_one(usage_data)
            except Exception as db_error:
                st.warning(f"利用状況のDB保存中にエラーが発生しました: {str(db_error)}")

        else:
            raise result['error']

    except Exception as e:
        raise APIError(f"退院時サマリの作成中にエラーが発生しました: {str(e)}")
