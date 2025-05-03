import flet as ft
from utils.auth import login_ui, require_login, check_ip_access
from utils.config import REQUIRE_LOGIN, IP_CHECK_ENABLED, IP_WHITELIST
from utils.env_loader import load_environment_variables
from utils.error_handlers import handle_error
from utils.prompt_manager import initialize_database
from views.department_management_page import department_management_ui
from views.prompt_management_page import prompt_management_ui
from views.statistics_page import usage_statistics_ui
from views.main_page import main_page_app

# グローバル状態の初期化
GLOBAL_STATE = {
    "discharge_summary": "",
    "parsed_summary": {},
    "show_password_change": False,
    "selected_department": "default",
    "current_page": "main",
    "success_message": None,
    "available_models": [],
    "summary_generation_time": None,
    "user": None
}


def main(page: ft.Page):
    # アプリケーションの初期設定
    page.title = "退院時サマリ作成アプリ"
    page.window_width = 1200
    page.window_height = 800
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 20

    # ページコンテンツを保持するコンテナ
    content_container = ft.Container(
        expand=True,
        content=ft.Text("Loading...")
    )

    # IP制限チェック関数
    def check_ip_restrictions():
        if IP_CHECK_ENABLED:
            if not check_ip_access(IP_WHITELIST, page):
                content_container.content = ft.Column([
                    ft.Text("アクセスが制限されています", size=30, weight=ft.FontWeight.BOLD),
                    ft.Text("このIPアドレスからはアクセスできません。", color=ft.colors.RED),
                    ft.Text("このシステムはIPアドレスによるアクセス制限が設定されています。"),
                    ft.Text("システム管理者にお問い合わせください。")
                ])
                page.update()
                return False
        return True

    # ページ切り替え関数
    def navigate_to(route):
        GLOBAL_STATE["current_page"] = route
        update_ui()

    # メインアプリの表示
    def show_main_app():
        if GLOBAL_STATE["current_page"] == "prompt_edit":
            content_container.content = prompt_management_ui(page, GLOBAL_STATE, navigate_to)
        elif GLOBAL_STATE["current_page"] == "department_edit":
            content_container.content = department_management_ui(page, GLOBAL_STATE, navigate_to)
        elif GLOBAL_STATE["current_page"] == "statistics":
            content_container.content = usage_statistics_ui(page, GLOBAL_STATE, navigate_to)
        else:
            content_container.content = main_page_app(page, GLOBAL_STATE, navigate_to)
        page.update()

    # ログインUI表示
    def show_login():
        content_container.content = login_ui(page, GLOBAL_STATE, on_login_success)
        page.update()

    # ログイン成功時のコールバック
    def on_login_success():
        show_main_app()

    # UIの更新
    def update_ui():
        if REQUIRE_LOGIN:
            if not GLOBAL_STATE["user"]:
                show_login()
            else:
                show_main_app()
        else:
            show_main_app()

    # メインレイアウトの構築
    page.add(
        ft.Column([
            content_container
        ], expand=True)
    )

    # 初期化とアプリの起動
    if check_ip_restrictions():
        update_ui()


# アプリケーション実行関数
def run_app():
    load_environment_variables()
    initialize_database()
    ft.app(target=main)


if __name__ == "__main__":
    run_app()
