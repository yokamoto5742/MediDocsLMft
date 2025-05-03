import flet as ft
from ui_components.navigation import render_sidebar
from services.summary_service import SummaryProcessor
from utils.error_handlers import handle_error


def main_page_app(page, global_state, navigate_to):
    """メイン画面の作成"""

    # カルテ入力用のテキストエリア
    input_text_area = ft.TextField(
        label="カルテ情報",
        multiline=True,
        min_lines=10,
        max_lines=20,
        expand=True
    )

    # 追加情報入力エリア
    additional_info_area = ft.TextField(
        label="追加情報（オプション）",
        multiline=True,
        min_lines=3,
        max_lines=5,
        expand=True
    )

    # サマリ生成ボタン
    summary_processor = SummaryProcessor(page, global_state)

    def generate_summary(e):
        """サマリ生成ボタンのクリックイベントハンドラ"""
        summary_processor.process_discharge_summary(
            input_text_area.value,
            additional_info_area.value,
            on_complete=lambda: page.update()
        )

    generate_button = ft.ElevatedButton(
        "退院時サマリを作成",
        on_click=generate_summary,
        style=ft.ButtonStyle(
            color=ft.colors.WHITE,
            bgcolor=ft.colors.BLUE
        )
    )

    # 結果表示用のテキストエリア
    result_text_area = ft.TextField(
        label="生成された退院時サマリ",
        value=global_state.get("discharge_summary", ""),
        multiline=True,
        min_lines=10,
        max_lines=30,
        read_only=True,
        expand=True
    )

    # サマリのセクション表示用のテーブル作成
    def create_sections_table():
        sections = global_state.get("parsed_summary", {})
        if not sections:
            return ft.Text("サマリが生成されるとここにセクション別の内容が表示されます")

        table_rows = []
        for section_name, section_content in sections.items():
            if section_content:
                row = ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(section_name, weight=ft.FontWeight.BOLD)),
                        ft.DataCell(ft.Text(section_content))
                    ]
                )
                table_rows.append(row)

        return ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("セクション")),
                ft.DataColumn(ft.Text("内容"))
            ],
            rows=table_rows
        )

    # 処理時間表示
    def get_processing_time():
        time = global_state.get("summary_generation_time")
        if time:
            return ft.Text(f"処理時間: {time:.1f}秒", color=ft.colors.BLUE)
        return None

    # タブの作成
    tabs = ft.Tabs(
        selected_index=0,
        tabs=[
            ft.Tab(
                text="テキスト全体",
                content=ft.Container(
                    content=result_text_area,
                    padding=10,
                    expand=True
                )
            ),
            ft.Tab(
                text="セクション別",
                content=ft.Container(
                    content=create_sections_table(),
                    padding=10,
                    expand=True
                )
            )
        ],
        expand=True
    )

    # コピーボタン
    def copy_to_clipboard(e):
        page.set_clipboard(global_state.get("discharge_summary", ""))
        page.show_snack_bar(ft.SnackBar(ft.Text("クリップボードにコピーしました")))

    copy_button = ft.ElevatedButton(
        "結果をコピー",
        on_click=copy_to_clipboard,
        disabled=not global_state.get("discharge_summary")
    )

    # サイドバーと本体のレイアウト
    content = ft.Row([
        render_sidebar(page, global_state, navigate_to),
        ft.VerticalDivider(width=1),
        ft.Column([
            ft.Container(
                content=ft.Text("退院時サマリ作成", size=28, weight=ft.FontWeight.BOLD),
                margin=ft.margin.only(bottom=20)
            ),
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        input_text_area,
                        additional_info_area,
                        ft.Row([
                            generate_button,
                            summary_processor.get_status_ui()
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                    ]),
                    padding=20
                ),
                expand=True
            ),
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text("生成結果", size=18, weight=ft.FontWeight.BOLD),
                            copy_button,
                            get_processing_time() if get_processing_time() else ft.Container()
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        tabs
                    ]),
                    padding=20
                ),
                expand=True
            )
        ], expand=True, spacing=20)
    ], expand=True)

    return content
