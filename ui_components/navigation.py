import flet as ft
from utils.auth import get_current_user, logout, password_change_ui, can_edit_prompts
from utils.prompt_manager import get_all_departments
from utils.config import GEMINI_MODEL, GEMINI_CREDENTIALS, GEMINI_FLASH_MODEL, CLAUDE_API_KEY, OPENAI_API_KEY, \
    OPENAI_MODEL, SELECTED_AI_MODEL


def render_sidebar(page, global_state, navigate_to):
    """サイドバーナビゲーションの作成"""
    sidebar_content = []

    # ユーザー情報と認証関連ボタン
    user = global_state["user"]
    if user:
        sidebar_content.append(ft.Text(f"ログイン中: {user['username']}", color=ft.colors.GREEN))

        # パスワード変更とログアウトボタン
        auth_buttons_row = ft.Row([
            ft.ElevatedButton("パスワード変更", on_click=lambda e: toggle_password_change(global_state, page)),
            ft.ElevatedButton("ログアウト", on_click=lambda e: handle_logout(global_state, page, navigate_to))
        ])
        sidebar_content.append(auth_buttons_row)

        # パスワード変更フォーム（表示/非表示切り替え）
        if global_state["show_password_change"]:
            password_change_container = ft.Container(
                content=password_change_ui(page, global_state),
                padding=10
            )
            sidebar_content.append(password_change_container)
            sidebar_content.append(
                ft.ElevatedButton("キャンセル", on_click=lambda e: cancel_password_change(global_state, page)))

    # 診療科選択ドロップダウン
    departments = ["default"] + get_all_departments()
    department_dropdown = ft.Dropdown(
        width=200,
        label="診療科",
        options=[
            ft.dropdown.Option(key=dept, text=("全科共通" if dept == "default" else dept))
            for dept in departments
        ],
        value=global_state["selected_department"]
    )

    # 診療科変更時のイベントハンドラ
    def on_department_change(e):
        global_state["selected_department"] = department_dropdown.value
        page.update()

    department_dropdown.on_change = on_department_change
    sidebar_content.append(department_dropdown)

    # 利用可能なAIモデルの取得
    global_state["available_models"] = []
    if GEMINI_MODEL and GEMINI_CREDENTIALS:
        global_state["available_models"].append("Gemini_Pro")
    if GEMINI_FLASH_MODEL and GEMINI_CREDENTIALS:
        global_state["available_models"].append("Gemini_Flash")
    if CLAUDE_API_KEY:
        global_state["available_models"].append("Claude")
    if OPENAI_API_KEY:
        global_state["available_models"].append("GPT4.1")

    # 複数のモデルが利用可能な場合、モデル選択ドロップダウンを表示
    if len(global_state["available_models"]) > 1:
        if "selected_model" not in global_state:
            default_model = SELECTED_AI_MODEL
            if default_model not in global_state["available_models"] and global_state["available_models"]:
                default_model = global_state["available_models"][0]
            global_state["selected_model"] = default_model

        model_dropdown = ft.Dropdown(
            width=200,
            label="AIモデル",
            options=[
                ft.dropdown.Option(key=model, text=model)
                for model in global_state["available_models"]
            ],
            value=global_state["selected_model"] if global_state["selected_model"] in global_state[
                "available_models"] else global_state["available_models"][0]
        )

        # モデル変更時のイベントハンドラ
        def on_model_change(e):
            global_state["selected_model"] = model_dropdown.value
            page.update()

        model_dropdown.on_change = on_model_change
        sidebar_content.append(model_dropdown)

    elif len(global_state["available_models"]) == 1:
        global_state["selected_model"] = global_state["available_models"][0]

    # 注意書き
    sidebar_content.append(ft.Text("・入力および出力テキストは保存されません"))
    sidebar_content.append(ft.Text("・出力結果は必ず確認してください"))

    # 管理者向けメニューボタン
    if can_edit_prompts(global_state):
        sidebar_content.append(ft.Divider())
        sidebar_content.append(ft.Text("管理者メニュー", weight=ft.FontWeight.BOLD))

        admin_buttons = [
            ft.ElevatedButton("診療科管理", on_click=lambda e: navigate_to("department_edit")),
            ft.ElevatedButton("プロンプト管理", on_click=lambda e: navigate_to("prompt_edit")),
            ft.ElevatedButton("統計情報", on_click=lambda e: navigate_to("statistics"))
        ]

        admin_menu = ft.Column([
            ft.Row([button], alignment=ft.MainAxisAlignment.START)
            for button in admin_buttons
        ])

        sidebar_content.append(admin_menu)

    # サイドバーコンテナの作成
    sidebar = ft.Card(
        content=ft.Container(
            padding=20,
            content=ft.Column(sidebar_content, spacing=20)
        ),
        width=250
    )

    return sidebar


def toggle_password_change(global_state, page):
    """パスワード変更フォームの表示/非表示を切り替え"""
    global_state["show_password_change"] = not global_state["show_password_change"]
    page.update()


def cancel_password_change(global_state, page):
    """パスワード変更フォームを閉じる"""
    global_state["show_password_change"] = False
    page.update()


def handle_logout(global_state, page, navigate_to):
    """ログアウト処理"""
    logout(global_state)
    navigate_to("main")
    page.update()
