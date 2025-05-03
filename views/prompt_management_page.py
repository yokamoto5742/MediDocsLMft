import flet as ft
from ui_components.navigation import render_sidebar
from utils.prompt_manager import get_all_departments, get_prompt_by_department, create_or_update_prompt, delete_prompt
from utils.error_handlers import handle_error


def prompt_management_ui(page, global_state, navigate_to):
    """プロンプト管理画面のUI"""

    # メッセージ表示用のテキスト
    message_text = ft.Text("", color=ft.colors.GREEN)
    error_text = ft.Text("", color=ft.colors.RED)

    # 診療科リストの取得
    departments = ["default"] + get_all_departments()

    # 選択された診療科のプロンプトを表示
    selected_department = global_state.get("selected_department", "default")
    dept_dropdown = ft.Dropdown(
        label="診療科",
        value=selected_department,
        options=[
            ft.dropdown.Option(key=dept, text=("全科共通" if dept == "default" else dept))
            for dept in departments
        ],
        width=300
    )

    # プロンプト名と内容のテキストフィールド
    prompt_name = ft.TextField(
        label="プロンプト名",
        value="退院時サマリ",
        width=300
    )

    prompt_content = ft.TextField(
        label="プロンプト内容",
        multiline=True,
        min_lines=15,
        max_lines=20,
        expand=True
    )

    # 現在のプロンプトを読み込む
    def load_current_prompt(department):
        try:
            prompt_data = get_prompt_by_department(department)
            if prompt_data:
                prompt_name.value = prompt_data.get("name", "退院時サマリ")
                prompt_content.value = prompt_data.get("content", "")
            else:
                prompt_name.value = "退院時サマリ"
                prompt_content.value = ""

            message_text.value = ""
            error_text.value = ""
            page.update()
        except Exception as e:
            error_text.value = f"プロンプトの読み込み中にエラーが発生しました: {str(e)}"
            page.update()

    # 診療科変更時のイベントハンドラ
    def on_department_change(e):
        load_current_prompt(dept_dropdown.value)

    dept_dropdown.on_change = on_department_change

    # 初期プロンプトの読み込み
    load_current_prompt(selected_department)

    # プロンプト保存ボタンのイベントハンドラ
    def save_prompt(e):
        try:
            department = dept_dropdown.value
            name = prompt_name.value
            content = prompt_content.value

            if not department or not name or not content:
                error_text.value = "すべての項目を入力してください"
                message_text.value = ""
                page.update()
                return

            success, msg = create_or_update_prompt(department, name, content)
            if success:
                message_text.value = msg
                error_text.value = ""
                # 診療科リストを再取得
                departments = ["default"] + get_all_departments()
                dept_dropdown.options = [
                    ft.dropdown.Option(key=dept, text=("全科共通" if dept == "default" else dept))
                    for dept in departments
                ]
            else:
                error_text.value = msg
                message_text.value = ""
            page.update()
        except Exception as e:
            error_text.value = f"プロンプトの保存中にエラーが発生しました: {str(e)}"
            message_text.value = ""
            page.update()

    # プロンプト削除ボタンのイベントハンドラ
    def delete_department_prompt(e):
        try:
            department = dept_dropdown.value

            if department == "default":
                error_text.value = "デフォルトプロンプトは削除できません"
                message_text.value = ""
                page.update()
                return

            # 確認ダイアログ
            def confirm_delete(e):
                dialog.open = False
                page.update()

                # 削除実行
                success, msg = delete_prompt(department)
                if success:
                    message_text.value = msg
                    error_text.value = ""

                    # 診療科リストを再取得
                    depts = ["default"] + get_all_departments()
                    dept_dropdown.options = [
                        ft.dropdown.Option(key=dept, text=("全科共通" if dept == "default" else dept))
                        for dept in depts
                    ]
                    dept_dropdown.value = "default"
                    load_current_prompt("default")
                else:
                    error_text.value = msg
                    message_text.value = ""
                page.update()

            def cancel_delete(e):
                dialog.open = False
                page.update()

            dialog = ft.AlertDialog(
                title=ft.Text("プロンプト削除の確認"),
                content=ft.Text(f"診療科「{department}」のプロンプトを削除しますか？\nこの操作は元に戻せません。"),
                actions=[
                    ft.TextButton("キャンセル", on_click=cancel_delete),
                    ft.TextButton("削除", on_click=confirm_delete),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )

            page.dialog = dialog
            dialog.open = True
            page.update()

        except Exception as e:
            error_text.value = f"プロンプトの削除中にエラーが発生しました: {str(e)}"
            message_text.value = ""
            page.update()

    # メイン画面に戻るボタン
    def back_to_main(e):
        navigate_to("main")

    # サイドバーと本体のレイアウト
    content = ft.Row([
        render_sidebar(page, global_state, navigate_to),
        ft.VerticalDivider(width=1),
        ft.Column([
            ft.Container(
                content=ft.Row([
                    ft.Text("プロンプト管理", size=28, weight=ft.FontWeight.BOLD),
                    ft.ElevatedButton("メイン画面に戻る", on_click=back_to_main)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                margin=ft.margin.only(bottom=20)
            ),
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            dept_dropdown,
                            prompt_name
                        ]),
                        prompt_content,
                        ft.Row([
                            ft.ElevatedButton("保存", on_click=save_prompt,
                                              style=ft.ButtonStyle(bgcolor=ft.colors.BLUE, color=ft.colors.WHITE)),
                            ft.ElevatedButton("削除", on_click=delete_department_prompt,
                                              style=ft.ButtonStyle(bgcolor=ft.colors.RED, color=ft.colors.WHITE))
                        ], alignment=ft.MainAxisAlignment.START),
                        message_text,
                        error_text
                    ]),
                    padding=20
                ),
                expand=True
            )
        ], expand=True, spacing=20)
    ], expand=True)

    return content
