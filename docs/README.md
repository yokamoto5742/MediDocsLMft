# 退院時サマリ作成アプリ

## 概要

このアプリケーションは、医療従事者向けの退院時サマリ自動生成ツールです。カルテ情報を入力すると、Google Gemini APIを利用してAIが退院時サマリを自動的に生成します。

## 主な機能

- カルテ情報からAIを使用した退院時サマリの自動生成
- 診療科ごとにカスタマイズ可能なプロンプト設定
- ユーザー認証システム（管理者権限を含む）（オプション）
- セクションごとに整理されたサマリ表示
- IPアドレスによるアクセス制限（オプション）
- データのバックアップと復元機能

## システム要件

- Python 3.11以上
- MongoDB
- Google Gemini API アクセス

## インストール方法

1. リポジトリをクローン

```bash
git clone [リポジトリURL]
cd discharge-summary-app
```

2. 必要なパッケージをインストール

```bash
pip install -r requirements.txt
```

3. 環境設定ファイルの作成

`.env`ファイルをプロジェクトのルートディレクトリに作成し、以下の情報を設定します：

```
MONGODB_URI=mongodb+srv://[username]:[password]@[host]/[database]?retryWrites=true&w=majority
MONGODB_DB_NAME=discharge_summary_app
MONGODB_USERS_COLLECTION=users
MONGODB_PROMPTS_COLLECTION=prompts
MONGODB_DEPARTMENTS_COLLECTION=departments

GEMINI_CREDENTIALS=[your_gemini_api_key]
GEMINI_MODEL=[gemini_model_name]

REQUIRE_LOGIN=True
IP_CHECK_ENABLED=True
IP_WHITELIST=127.0.0.1,…
```

## 起動方法

```bash
streamlit run app.py
```

## 使用方法

### 一般ユーザー

1. アプリにアクセスし、ユーザー登録またはログインを行います
2. カルテ情報を入力欄に貼り付けます
3. 「退院時サマリ作成」ボタンをクリックします
4. 生成されたサマリを各タブで確認します
5. 必要に応じてテキストをコピーして使用します

### 管理者（最初に登録したユーザーに自動付与）

管理者は以下の追加機能を利用できます：

1. **診療科管理**：診療科の追加・削除
2. **プロンプト管理**：診療科ごとのAIプロンプトをカスタマイズ

## データバックアップ

バックアップユーティリティを使用してデータをバックアップおよび復元できます：

```bash
python -m utils.backup_manager
```

このツールは以下の操作をサポートしています：
- プロンプトと診療科データのバックアップ作成
- バックアップからのデータ復元
- バックアップファイルの一覧表示

## 注意事項

- 生成されたサマリの内容は必ず確認してください
- 入力および出力テキストはサーバーに保存されません
- IP制限機能を有効にする場合は、正しいIPアドレスまたはCIDR表記を設定してください

## 技術情報

- **フロントエンド**: Streamlit
- **データベース**: MongoDB
- **認証**: bcrypt
- **生成AIモデル**: Google Gemini API

## トラブルシューティング

- **API接続エラー**: Gemini APIのクレデンシャルと環境変数の設定を確認してください
- **データベース接続エラー**: MongoDB URIと接続情報を確認してください
- **アクセス制限**: IP制限が有効な場合、許可されたIPからアクセスしていることを確認してください

## ライセンス

LICENSEファイルを参照してください