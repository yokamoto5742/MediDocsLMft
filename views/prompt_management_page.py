import streamlit as st
from utils.error_handlers import handle_error
from utils.exceptions import AppError
from utils.prompt_manager import get_all_departments, get_prompt_by_department, create_or_update_prompt, delete_prompt
from ui_components.navigation import change_page

@handle_error
def prompt_management_ui():
    if st.session_state.success_message:
        st.success(st.session_state.success_message)
        st.session_state.success_message = None

    if st.button("作成画面に戻る", key="back_to_main"):
        change_page("main")
        st.rerun()

    if "selected_dept_for_prompt" not in st.session_state:
        st.session_state.selected_dept_for_prompt = "default"

    departments = ["default"] + get_all_departments()
    selected_dept = st.selectbox(
        "診療科を選択",
        departments,
        index=departments.index(
            st.session_state.selected_dept_for_prompt) if st.session_state.selected_dept_for_prompt in departments else 0,
        format_func=lambda x: "全科共通" if x == "default" else x,
        key="prompt_department_selector"
    )

    st.session_state.selected_dept_for_prompt = selected_dept

    prompt_data = get_prompt_by_department(selected_dept)

    with st.form(key=f"edit_prompt_form_{selected_dept}"):
        prompt_name = st.text_input(
            "プロンプト名",
            value=prompt_data.get("name", "") if prompt_data else "退院時サマリ",
            key=f"prompt_name_{selected_dept}"
        )
        prompt_content = st.text_area(
            "内容",
            value=prompt_data.get("content", "") if prompt_data else "",
            height=200,
            key=f"prompt_content_{selected_dept}"
        )

        submit = st.form_submit_button("プロンプトを保存")

        if submit:
            success, message = create_or_update_prompt(selected_dept, prompt_name, prompt_content)
            if success:
                st.success(message)
            else:
                raise AppError(message)

    if selected_dept != "default":
        if st.button("プロンプトを削除", key=f"delete_prompt_{selected_dept}", type="primary"):
            success, message = delete_prompt(selected_dept)
            if success:
                st.session_state.success_message = message
                st.session_state.selected_dept_for_prompt = "default"
                st.rerun()
            else:
                raise AppError(message)
