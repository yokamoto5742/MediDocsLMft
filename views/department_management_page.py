import streamlit as st
from utils.error_handlers import handle_error
from utils.exceptions import AppError
from utils.prompt_manager import get_all_departments, create_department, delete_department, update_department_order
from ui_components.navigation import change_page

@handle_error
def department_management_ui():
    if st.button("作成画面に戻る", key="back_to_main_from_dept"):
        change_page("main")
        st.rerun()

    with st.form(key="add_department_form_unique"):
        new_dept = st.text_input("診療科", placeholder="追加する診療科を入力してください", label_visibility="collapsed")
        submit = st.form_submit_button("追加")

        if submit and new_dept:
            success, message = create_department(new_dept)
            if success:
                st.success(message)
            else:
                raise AppError(message)
            st.rerun()

    if "show_move_options" not in st.session_state:
        st.session_state.show_move_options = {}

    departments = get_all_departments()

    for i, dept in enumerate(departments):
        col1, col2, col3 = st.columns([4, 1, 1])
        with col1:
            st.write(dept)

        with col2:
            if dept not in st.session_state.show_move_options:
                if st.button("⇅", key=f"move_{dept}"):
                    st.session_state.show_move_options[dept] = True
                    st.rerun()
            else:
                move_options_container = st.container()
                with move_options_container:
                    move_col1, move_col2, move_col3 = st.columns(3)

                    with move_col1:
                        if i > 0 and st.button("↑", key=f"up_action_{dept}"):
                            success, message = update_department_order(dept, i - 1)
                            if success:
                                st.success(message)
                                del st.session_state.show_move_options[dept]
                            else:
                                raise AppError(message)
                            st.rerun()

                    with move_col2:
                        if i < len(departments) - 1 and st.button("↓", key=f"down_action_{dept}"):
                            success, message = update_department_order(dept, i + 1)
                            if success:
                                st.success(message)
                                del st.session_state.show_move_options[dept]
                            else:
                                raise AppError(message)
                            st.rerun()

                    with move_col3:
                        if st.button("✕", key=f"cancel_move_{dept}"):
                            del st.session_state.show_move_options[dept]
                            st.rerun()

        with col3:
            if dept not in ["内科"]:
                if st.button("削除", key=f"delete_{dept}"):
                    success, message = delete_department(dept)
                    if success:
                        st.success(message)
                    else:
                        raise AppError(message)
                    st.rerun()
