import flet as ft
import datetime
from ui_components.navigation import render_sidebar
from utils.db import get_usage_collection
from utils.constants import DOCUMENT_NAME_OPTIONS


def usage_statistics_ui(page, global_state, navigate_to):
    """統計情報表示画面のUI"""

    # 日付範囲指定用のコントロール
    now = datetime.datetime.now()
    start_date = now - datetime.timedelta(days=30)

    start_date_picker = ft.DatePicker(
        first_date=datetime.datetime(2023, 1, 1),
        last_date=now,
        value=start_date.strftime("%Y-%m-%d")
    )

    end_date_picker = ft.DatePicker(
        first_date=datetime.datetime(2023, 1, 1),
        last_date=now + datetime.timedelta(days=1),
        value=now.strftime("%Y-%m-%d")
    )

    page.overlay.append(start_date_picker)
    page.overlay.append(end_date_picker)

    start_date_button = ft.ElevatedButton(
        "開始日を選択",
        icon=ft.icons.CALENDAR_TODAY,
        on_click=lambda _: start_date_picker.pick_date()
    )

    end_date_button = ft.ElevatedButton(
        "終了日を選択",
        icon=ft.icons.CALENDAR_TODAY,
        on_click=lambda _: end_date_picker.pick_date()
    )

    # 統計タイプセレクター
    stats_type = ft.Tabs(
        selected_index=0,
        tabs=[
            ft.Tab(text="日別集計"),
            ft.Tab(text="診療科別集計"),
            ft.Tab(text="モデル別集計")
        ]
    )

    # ドキュメントタイプセレクター
    doc_type_dropdown = ft.Dropdown(
        label="文書タイプ",
        options=[
            ft.dropdown.Option(key=doc_type, text=doc_type)
            for doc_type in DOCUMENT_NAME_OPTIONS
        ],
        value=DOCUMENT_NAME_OPTIONS[0]
    )

    # 統計データ表示エリア
    stats_display = ft.Container(
        content=ft.Text("統計情報を読み込んでいます..."),
        expand=True
    )

    # エラー表示
    error_text = ft.Text("", color=ft.colors.RED)

    # 統計データの取得・表示
    def load_statistics():
        try:
            start_str = start_date_picker.value
            end_str = end_date_picker.value

            if not start_str or not end_str:
                error_text.value = "日付範囲を指定してください"
                page.update()
                return

            start = datetime.datetime.strptime(start_str, "%Y-%m-%d")
            end = datetime.datetime.strptime(end_str, "%Y-%m-%d") + datetime.timedelta(days=1)

            # 日付の前後チェック
            if start > end:
                error_text.value = "開始日は終了日より前の日付を指定してください"
                page.update()
                return

            doc_type = doc_type_dropdown.value
            tab_index = stats_type.selected_index

            # MongoDB からデータ取得
            usage_collection = get_usage_collection()

            # クエリの構築
            query = {
                "date": {"$gte": start, "$lt": end}
            }

            if doc_type != "すべて":
                query["document_name"] = doc_type

            # データ取得
            data = list(usage_collection.find(query))

            if not data:
                stats_display.content = ft.Text("データがありません")
                error_text.value = ""
                page.update()
                return

            # データフレームに変換して集計
            df = pd.DataFrame(data)

            if tab_index == 0:  # 日別集計
                display_daily_stats(df)
            elif tab_index == 1:  # 診療科別集計
                display_department_stats(df)
            else:  # モデル別集計
                display_model_stats(df)

            error_text.value = ""
            page.update()

        except Exception as e:
            error_text.value = f"統計情報の取得中にエラーが発生しました: {str(e)}"
            page.update()

    # 日別統計の表示
    def display_daily_stats(df):
        try:
            # 日付ごとに集計
            df['date_str'] = df['date'].dt.strftime('%Y-%m-%d')
            daily_stats = df.groupby('date_str').agg({
                'input_tokens': 'sum',
                'output_tokens': 'sum',
                'total_tokens': 'sum',
                'processing_time': 'mean',
                'document_name': 'count'
            }).reset_index()

            daily_stats = daily_stats.rename(columns={'document_name': 'count'})
            daily_stats['processing_time'] = daily_stats['processing_time'].round(1)

            # 表の作成
            table_rows = []
            for _, row in daily_stats.iterrows():
                table_row = ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(row['date_str'])),
                        ft.DataCell(ft.Text(str(row['count']))),
                        ft.DataCell(ft.Text(f"{row['input_tokens']:,}")),
                        ft.DataCell(ft.Text(f"{row['output_tokens']:,}")),
                        ft.DataCell(ft.Text(f"{row['total_tokens']:,}")),
                        ft.DataCell(ft.Text(f"{row['processing_time']:.1f}秒"))
                    ]
                )
                table_rows.append(table_row)

            # 合計行の追加
            total_count = daily_stats['count'].sum()
            total_input = daily_stats['input_tokens'].sum()
            total_output = daily_stats['output_tokens'].sum()
            total_tokens = daily_stats['total_tokens'].sum()
            avg_time = daily_stats['processing_time'].mean()

            total_row = ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text("合計/平均", weight=ft.FontWeight.BOLD)),
                    ft.DataCell(ft.Text(str(total_count), weight=ft.FontWeight.BOLD)),
                    ft.DataCell(ft.Text(f"{total_input:,}", weight=ft.FontWeight.BOLD)),
                    ft.DataCell(ft.Text(f"{total_output:,}", weight=ft.FontWeight.BOLD)),
                    ft.DataCell(ft.Text(f"{total_tokens:,}", weight=ft.FontWeight.BOLD)),
                    ft.DataCell(ft.Text(f"{avg_time:.1f}秒", weight=ft.FontWeight.BOLD))
                ]
            )
            table_rows.append(total_row)

            # テーブルの作成
            table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("日付")),
                    ft.DataColumn(ft.Text("処理数")),
                    ft.DataColumn(ft.Text("入力トークン")),
                    ft.DataColumn(ft.Text("出力トークン")),
                    ft.DataColumn(ft.Text("合計トークン")),
                    ft.DataColumn(ft.Text("平均処理時間"))
                ],
                rows=table_rows
            )

            stats_display.content = table

        except Exception as e:
            stats_display.content = ft.Text(f"データの集計中にエラーが発生しました: {str(e)}")

    # 診療科別統計の表示
    def display_department_stats(df):
        try:
            # 診療科ごとに集計
            dept_stats = df.groupby('department').agg({
                'input_tokens': 'sum',
                'output_tokens': 'sum',
                'total_tokens': 'sum',
                'processing_time': 'mean',
                'document_name': 'count'
            }).reset_index()

            dept_stats = dept_stats.rename(columns={'document_name': 'count'})
            dept_stats['processing_time'] = dept_stats['processing_time'].round(1)

            # デフォルト診療科の表示名を変更
            dept_stats['department'] = dept_stats['department'].replace('default', '全科共通')

            # 表の作成
            table_rows = []
            for _, row in dept_stats.iterrows():
                table_row = ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(row['department'])),
                        ft.DataCell(ft.Text(str(row['count']))),
                        ft.DataCell(ft.Text(f"{row['input_tokens']:,}")),
                        ft.DataCell(ft.Text(f"{row['output_tokens']:,}")),
                        ft.DataCell(ft.Text(f"{row['total_tokens']:,}")),
                        ft.DataCell(ft.Text(f"{row['processing_time']:.1f}秒"))
                    ]
                )
                table_rows.append(table_row)

            # 合計行の追加
            total_count = dept_stats['count'].sum()
            total_input = dept_stats['input_tokens'].sum()
            total_output = dept_stats['output_tokens'].sum()
            total_tokens = dept_stats['total_tokens'].sum()
            avg_time = dept_stats['processing_time'].mean()

            total_row = ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text("合計/平均", weight=ft.FontWeight.BOLD)),
                    ft.DataCell(ft.Text(str(total_count), weight=ft.FontWeight.BOLD)),
                    ft.DataCell(ft.Text(f"{total_input:,}", weight=ft.FontWeight.BOLD)),
                    ft.DataCell(ft.Text(f"{total_output:,}", weight=ft.FontWeight.BOLD)),
                    ft.DataCell(ft.Text(f"{total_tokens:,}", weight=ft.FontWeight.BOLD)),
                    ft.DataCell(ft.Text(f"{avg_time:.1f}秒", weight=ft.FontWeight.BOLD))
                ]
            )
            table_rows.append(total_row)

            # テーブルの作成
            table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("診療科")),
                    ft.DataColumn(ft.Text("処理数")),
                    ft.DataColumn(ft.Text("入力トークン")),
                    ft.DataColumn(ft.Text("出力トークン")),
                    ft.DataColumn(ft.Text("合計トークン")),
                    ft.DataColumn(ft.Text("平均処理時間"))
                ],
                rows=table_rows
            )

            stats_display.content = table

        except Exception as e:
            stats_display.content = ft.Text(f"データの集計中にエラーが発生しました: {str(e)}")

    # モデル別統計の表示
    def display_model_stats(df):
        try:
            # モデルごとに集計
            model_stats = df.groupby('model_detail').agg({
                'input_tokens': 'sum',
                'output_tokens': 'sum',
                'total_tokens': 'sum',
                'processing_time': 'mean',
                'document_name': 'count'
            }).reset_index()

            model_stats = model_stats.rename(columns={'document_name': 'count'})
            model_stats['processing_time'] = model_stats['processing_time'].round(1)

            # 表の作成
            table_rows = []
            for _, row in model_stats.iterrows():
                table_row = ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(row['model_detail'])),
                        ft.DataCell(ft.Text(str(row['count']))),
                        ft.DataCell(ft.Text(f"{row['input_tokens']:,}")),
                        ft.DataCell(ft.Text(f"{row['output_tokens']:,}")),
                        ft.DataCell(ft.Text(f"{row['total_tokens']:,}")),
                        ft.DataCell(ft.Text(f"{row['processing_time']:.1f}秒"))
                    ]
                )
                table_rows.append(table_row)

            # 合計行の追加
            total_count = model_stats['count'].sum()
            total_input = model_stats['input_tokens'].sum()
            total_output = model_stats['output_tokens'].sum()
            total_tokens = model_stats['total_tokens'].sum()
            avg_time = model_stats['processing_time'].mean()

            total_row = ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text("合計/平均", weight=ft.FontWeight.BOLD)),
                    ft.DataCell(ft.Text(str(total_count), weight=ft.FontWeight.BOLD)),
                    ft.DataCell(ft.Text(f"{total_input:,}", weight=ft.FontWeight.BOLD)),
                    ft.DataCell(ft.Text(f"{total_output:,}", weight=ft.FontWeight.BOLD)),
                    ft.DataCell(ft.Text(f"{total_tokens:,}", weight=ft.FontWeight.BOLD)),
                    ft.DataCell(ft.Text(f"{avg_time:.1f}秒", weight=ft.FontWeight.BOLD))
                ]
            )
            table_rows.append(total_row)

            # テーブルの作成
            table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("AIモデル")),
                    ft.DataColumn(ft.Text("処理数")),
                    ft.DataColumn(ft.Text("入力トークン")),
                    ft.DataColumn(ft.Text("出力トークン")),
                    ft.DataColumn(ft.Text("合計トークン")),
                    ft.DataColumn(ft.Text("平均処理時間"))
                ],
                rows=table_rows
            )

            stats_display.content = table

        except Exception as e:
            stats_display.content = ft.Text(f"データの集計中にエラーが発生しました: {str(e)}")

    # 検索ボタンのイベントハンドラ
    def on_search(e):
        load_statistics()

    # タブ切り替え時のイベントハンドラ
    def on_tab_change(e):
        load_statistics()

    stats_type.on_change = on_tab_change

    # メイン画面に戻るボタン
    def back_to_main(e):
        navigate_to("main")

    # 初期データの読み込み
    load_statistics()

    # サイドバーと本体のレイアウト
    content = ft.Row([
        render_sidebar(page, global_state, navigate_to),
        ft.VerticalDivider(width=1),
        ft.Column([
            ft.Container(
                content=ft.Row([
                    ft.Text("統計情報", size=28, weight=ft.FontWeight.BOLD),
                    ft.ElevatedButton("メイン画面に戻る", on_click=back_to_main)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                margin=ft.margin.only(bottom=20)
            ),
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Column([
                                ft.Text("期間を選択", size=16),
                                ft.Row([
                                    start_date_button,
                                    end_date_button,
                                ])
                            ]),
                            ft.Column([
                                ft.Text("表示項目", size=16),
                                ft.Row([
                                    doc_type_dropdown,
                                    ft.ElevatedButton("検索", on_click=on_search)
                                ])
                            ])
                        ]),
                        stats_type,
                        error_text
                    ]),
                    padding=20
                )
            ),
            ft.Card(
                content=ft.Container(
                    content=stats_display,
                    padding=20
                ),
                expand=True
            )
        ], expand=True, spacing=20)
    ], expand=True)

    return content
