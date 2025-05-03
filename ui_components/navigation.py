import streamlit as st
from utils.auth import get_current_user, logout, password_change_ui, can_edit_prompts
from utils.prompt_manager import get_all_departments
from utils.config import GEMINI_MODEL, GEMINI_CREDENTIALS, GEMINI_FLASH_MODEL, CLAUDE_API_KEY, OPENAI_API_KEY, OPENAI_MODEL, SELECTED_AI_MODEL

def toggle_password_change():
    st.session_state.show_password_change = not st.session_state.show_password_change

def change_page(page):
    st.session_state.current_page = page

def render_sidebar():
    user = get_current_user()
    if user:
        st.sidebar.success(f"ログイン中: {user['username']}")

        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("パスワード変更", key="show_password_change_button"):
                toggle_password_change()
        with col2:
            if st.button("ログアウト"):
                logout()
                st.rerun()

        if st.session_state.show_password_change:
            with st.sidebar:
                password_change_ui()
                if st.button("キャンセル"):
                    st.session_state.show_password_change = False
                    st.rerun()

    departments = ["default"] + get_all_departments()
    selected_dept = st.sidebar.selectbox(
        "診療科",
        departments,
        index=departments.index(st.session_state.selected_department),
        format_func=lambda x: "全科共通" if x == "default" else x,
        key="department_selector"
    )
    st.session_state.selected_department = selected_dept

    st.session_state.available_models = []
    if GEMINI_MODEL and GEMINI_CREDENTIALS:
        st.session_state.available_models.append("Gemini_Pro")
    if GEMINI_FLASH_MODEL and GEMINI_CREDENTIALS:
        st.session_state.available_models.append("Gemini_Flash")
    if CLAUDE_API_KEY:
        st.session_state.available_models.append("Claude")
    if OPENAI_API_KEY:
        st.session_state.available_models.append("GPT4.1")

    if len(st.session_state.available_models) > 1:
        if "selected_model" not in st.session_state:
            default_model = SELECTED_AI_MODEL
            if default_model not in st.session_state.available_models and st.session_state.available_models:
                default_model = st.session_state.available_models[0]
            st.session_state.selected_model = default_model

        selected_model = st.sidebar.selectbox(
            "AIモデル",
            st.session_state.available_models,
            index=st.session_state.available_models.index(
                st.session_state.selected_model) if st.session_state.selected_model in st.session_state.available_models else 0,
            key="model_selector"
        )
        st.session_state.selected_model = selected_model

    elif len(st.session_state.available_models) == 1:
        st.session_state.selected_model = st.session_state.available_models[0]

    st.sidebar.markdown("・入力および出力テキストは保存されません")
    st.sidebar.markdown("・出力結果は必ず確認してください")

    if can_edit_prompts():
        if st.sidebar.button("診療科管理", key="department_management"):
            change_page("department_edit")
            st.rerun()
        if st.sidebar.button("プロンプト管理", key="prompt_management"):
            change_page("prompt_edit")
            st.rerun()

        if st.sidebar.button("統計情報", key="usage_statistics"):
            change_page("statistics")
            st.rerun()