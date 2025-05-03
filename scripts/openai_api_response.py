import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI


def load_environment_variables():
    """
    環境変数を読み込む関数
    1. システム環境変数が設定されている場合はそれを優先
    2. .envファイルが存在する場合はそこから読み込む
    """
    # システム環境変数の存在確認
    openai_api_key = os.environ.get("OPENAI_API_KEY")

    # システム環境変数がすでに設定されている場合
    if openai_api_key:
        print("システム環境変数からAPIキーを読み込みました")
        return

    # .envファイルのパスを取得
    base_dir = Path(__file__).parent
    env_path = os.path.join(base_dir, '.env')

    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(".envファイルから環境変数を読み込みました")
    else:
        print("警告: .envファイルが見つかりません。")

        # 上位ディレクトリも検索
        parent_dir = base_dir.parent
        parent_env_path = os.path.join(parent_dir, '.env')
        if os.path.exists(parent_env_path):
            load_dotenv(parent_env_path)
            print("親ディレクトリの.envファイルから環境変数を読み込みました")
        else:
            print("警告: 親ディレクトリにも.envファイルが見つかりません。")


def test_openai_api_key():
    """
    OpenAI APIキーが正しく動作するかテストする関数
    """
    # 環境変数の読み込み
    load_environment_variables()

    # APIキーの取得
    api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        print("❌ OPENAI_API_KEYが環境変数に設定されていません")
        return False

    # APIキーが5文字以上あるか確認（セキュリティのため完全なキーは表示しない）
    if len(api_key) > 5:
        key_preview = f"{api_key[:3]}...{api_key[-3:]}"
        print(f"ℹ️ APIキー: {key_preview} (セキュリティのため一部のみ表示)")
    else:
        print("❌ APIキーの形式が不正です")
        return False

    try:
        # APIクライアントの初期化
        client = OpenAI(api_key=api_key)

        # 簡単なリクエストでテスト
        print("🔄 OpenAI APIに接続しています...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "短く返答してください。"},
                {"role": "user", "content": "こんにちは"}
            ],
            max_tokens=5
        )

        # レスポンスを確認
        if response.choices and response.choices[0].message.content:
            print("✅ APIキーは正常に動作しています")
            print(f"📝 応答: {response.choices[0].message.content}")
            print(f"🔢 使用トークン数: 入力={response.usage.prompt_tokens}, 出力={response.usage.completion_tokens}")
            return True
        else:
            print("❌ APIからの応答はありますが、内容が空です")
            return False

    except Exception as e:
        print(f"❌ APIキーテストエラー: {str(e)}")
        return False


if __name__ == "__main__":
    test_openai_api_key()