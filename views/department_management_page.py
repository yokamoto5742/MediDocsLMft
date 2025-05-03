import flet as ft
from ui_components.navigation import render_sidebar
from utils.prompt_manager import get_all_departments, create_department, delete_department, update_department_order
from utils.error_handlers import handle_error


def department_management_ui(page, global_state, navigate_to):
    """診療科管理画面のUI"""

    # メッセージ表示用のテキスト
    message_text = ft.Text("", color=ft.colors.GREEN)
    error_text = ft.Text("", color=ft.colors.RED)

    # 新規診療科追加フォーム
    new_department = ft.TextField(
        label="診療科名",
        width=300
    )

    # 診療科リストデータ
    department_list = ft.ListView(
        spacing=10,
        padding=20,
        auto_scroll=False
    )

    # 診療科リストを読み込む
    def load_departments():
        department_list.controls = []
        departments = get_all_departments()

        for i, dept in enumerate(departments):
            # 診療科アイテム
            dept_card = ft.Card(
                content=ft.Container(
                    content=ft.Row([
                        ft.Text(dept, size=16),

                        # 順序変更ボタン
                        ft.Row([
                            ft.IconButton(
                                icon=ft.icons.ARROW_UPWARD,
                                icon_color=ft.colors.BLUE,
                                tooltip="上に移動",
                                disabled=i == 0,
                                on_click=lambda e, d=dept, idx=i: move_department_up(d, idx)
                            ),
                            ft.IconButton(
                                icon=ft.icons.ARROW_DOWNWARD,
                                icon_color=ft.colors.BLUE,
                                tooltip="下に移動",
                                disabled=i == len(departments) - 1,
                                on_click=lambda e, d=dept, idx=i: move_department_down(d, idx)
                            ),
                            ft.IconButton(
                                icon=ft.icons.DELETE,
                                icon_color=ft.colors.RED,
                                tooltip="削除",
                                on_click=lambda e, d=dept: confirm_delete_department(d)
                            )
                        ])
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=10
                )
            )
            department_list.controls.append(dept_card)

        page.update()

    # 初期データの読み込み
    load_departments()

    # 診療科追加ボタンのイベントハンドラ
    def add_department(e):
        try:
            if not new_department.value:
                error_text.value = "診療科名を入力してください"
                message_text.value = ""
                page.update()
                return

            success, msg = create_department(new_department.value)
            if success:
                message_text.value = msg
                error_text.value = ""
                new_department.value = ""
                load_departments()
            else:
                error_text.value = msg
                message_text.value = ""
                page.update()

        except Exception as e:
            error_text.value = f"診療科の追加中にエラーが発生しました: {str(e)}"
            message_text.value = ""
            page.update()

    # 診療科の順序を上に移動
    def move_department_up(department, current_index):
        try:
            # インデックスは0から始まるので、1つ前の順序は現在のインデックス - 1
            new_order = current_index - 1
            success, msg = update_department_order(department, new_order)

            if success:
                message_text.value = "診療科の順序を更新しました"
                error_text.value = ""
                load_departments()
            else:
                error_text.value = msg
                message_text.value = ""
                page.update()

        except Exception as e:
            error_text.value = f"診療科の順序変更中にエラーが発生しました: {str(e)}"
            message_text.value = ""
            page.update()

    # 診療科の順序を下に移動
    def move_department_down(department, current_index):
        try:
            # インデックスは0から始まるので、1つ後の順序は現在のインデックス + 1
            new_order = current_index + 1
            success, msg = update_department_order(department, new_order)

            if success:
                message_text.value = "診療科の順序を更新しました"
                error_text.value = ""
                load_departments()
            else:
                error_text.value = msg
                message_text.value = ""
                page.update()

        except Exception as e:
            error_text.value = f"診療科の順序変更中にエラーが発生しました: {str(e)}"
            message_text.value = ""
            page.update()

    # 診療科削除の確認ダイアログ
    def confirm_delete_department(department):
        def confirm_delete(e):
            dialog.open = False
            page.update()

            # 削除実行
            success, msg = delete_department(department)
            if success:
                message_text.value = msg
                error_text.value = ""
                load_departments()
            else:
                error_text.value = msg
                message_text.value = ""
                page.update()

        def cancel_delete(e):
            dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("診療科削除の確認"),
            content=ft.Text(f"診療科「{department}」を削除しますか？\nこの操作は元に戻せません。"),
            actions=[
                ft.TextButton("キャンセル", on_click=cancel_delete),
                ft.TextButton("削除", on_click=confirm_delete),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.dialog = dialog
        dialog.open = True
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
                    ft.Text("診療科管理", size=28, weight=ft.FontWeight.BOLD),
                    ft.ElevatedButton("メイン画面に戻る", on_click=back_to_main)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                margin=ft.margin.only(bottom=20)
            ),
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("新規診療科の追加", size=18, weight=ft.FontWeight.BOLD),
                        ft.Row([
                            new_department,
                            ft.ElevatedButton("追加", on_click=add_department)
                        ]),
                        message_text,
                        error_text
                    ]),
                    padding=20
                )
            ),
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("診療科一覧", size=18, weight=ft.FontWeight.BOLD),
                        ft.Container(
                            content=department_list,
                            height=400,
                            border=ft.border.all(1, ft.colors.BLACK12),
                            border_radius=5
                        )
                    ]),
                    padding=20
                ),
                expand=True
            )
        ], expand=True, spacing=20)
    ], expand=True)

    return content
