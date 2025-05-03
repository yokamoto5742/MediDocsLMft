import datetime
import json
import os
from pathlib import Path

from utils.env_loader import load_environment_variables
from utils.config import get_config
from utils.db import DatabaseManager
from utils.prompt_manager import get_all_departments, get_all_prompts, get_department_collection, get_prompt_collection


def get_mongodb_connection():
    return DatabaseManager.get_instance().get_client()


def get_backup_dir(backup_type):
    config = get_config()
    root_dir = Path(__file__).parent.parent

    if 'BACKUP' in config:
        if backup_type == 'prompts' and 'prompts_dir' in config['BACKUP']:
            dir_path = config['BACKUP']['prompts_dir']
            if not os.path.isabs(dir_path):
                dir_path = os.path.join(root_dir, dir_path)
            return dir_path

        elif backup_type == 'departments' and 'departments_dir' in config['BACKUP']:
            dir_path = config['BACKUP']['departments_dir']
            if not os.path.isabs(dir_path):
                dir_path = os.path.join(root_dir, dir_path)
            return dir_path

    default_dir = os.path.join(root_dir, 'backups', backup_type)
    return default_dir


def backup_data(data_type, backup_dir=None):
    """
    データベースに保存されているデータをJSONファイルにバックアップする関数
    """
    if backup_dir is None:
        backup_dir = get_backup_dir(data_type)

    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{data_type}_backup_{timestamp}.json"
    backup_path = os.path.join(backup_dir, filename)

    # データタイプに応じたコレクション取得
    if data_type == 'prompts':
        collection = get_prompt_collection()
        success_message = "プロンプトのバックアップが完了しました"
    elif data_type == 'departments':
        collection = get_department_collection()
        success_message = "診療科のバックアップが完了しました"
    else:
        raise ValueError(f"不明なデータタイプ: {data_type}")

    data = list(collection.find({}, {'_id': False}))

    # データをJSONファイルに書き込む
    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    print(f"{success_message}: {backup_path}")
    return backup_path


def backup_prompts(backup_dir=None):
    return backup_data('prompts', backup_dir)


def backup_departments(backup_dir=None):
    return backup_data('departments', backup_dir)


def restore_data(backup_file, data_type):
    """
    バックアップファイルからデータを復元する関数
    """
    if not os.path.exists(backup_file):
        print(f"エラー: バックアップファイルが見つかりません: {backup_file}")
        return False

    success_message = "データ"

    try:
        with open(backup_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # データタイプに応じたコレクション取得とメッセージ設定
        if data_type == 'prompts':
            collection = get_prompt_collection()
            id_field = "department"
            success_message = "プロンプト"
        elif data_type == 'departments':
            collection = get_department_collection()
            id_field = "name"
            success_message = "診療科"
        else:
            raise ValueError(f"不明なデータタイプ: {data_type}")

        # 既存のデータをすべて削除（この操作は取り消せません)
        if input(f"既存の{success_message}をすべて削除しますか？ (y/n): ").lower() == 'y':
            collection.delete_many({})
            print(f"既存の{success_message}をすべて削除しました")

        # バックアップデータを挿入
        for item in data:
            if 'created_at' in item and isinstance(item['created_at'], str):
                item['created_at'] = datetime.datetime.fromisoformat(item['created_at'].replace('Z', '+00:00'))
            if 'updated_at' in item and isinstance(item['updated_at'], str):
                item['updated_at'] = datetime.datetime.fromisoformat(item['updated_at'].replace('Z', '+00:00'))

            existing = collection.find_one({id_field: item[id_field]})

            if existing:
                collection.update_one(
                    {id_field: item[id_field]},
                    {"$set": item}
                )
            else:
                collection.insert_one(item)

        print(f"{len(data)}件の{success_message}を正常に復元しました")
        return True

    except Exception as e:
        print(f"{success_message}復元中にエラーが発生しました: {str(e)}")
        return False


def restore_prompts(backup_file):
    return restore_data(backup_file, 'prompts')


def restore_departments(backup_file):
    return restore_data(backup_file, 'departments')


def list_backup_files():
    """
    バックアップファイルの一覧を表示する関数
    """
    prompts_dir = get_backup_dir('prompts')
    departments_dir = get_backup_dir('departments')

    print("\n=== プロンプトバックアップファイル ===")
    if os.path.exists(prompts_dir):
        files = os.listdir(prompts_dir)
        if files:
            for idx, file in enumerate(sorted(files, reverse=True)):
                full_path = os.path.join(prompts_dir, file)
                size = os.path.getsize(full_path) // 1024  # KB単位
                mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(full_path))
                print(f"{idx + 1}. {file} ({size}KB) - {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("バックアップファイルが見つかりません")
    else:
        print("バックアップディレクトリが見つかりません")

    print("\n=== 診療科バックアップファイル ===")
    if os.path.exists(departments_dir):
        files = os.listdir(departments_dir)
        if files:
            for idx, file in enumerate(sorted(files, reverse=True)):
                full_path = os.path.join(departments_dir, file)
                size = os.path.getsize(full_path) // 1024  # KB単位
                mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(full_path))
                print(f"{idx + 1}. {file} ({size}KB) - {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("バックアップファイルが見つかりません")
    else:
        print("バックアップディレクトリが見つかりません")


if __name__ == "__main__":
    # 環境変数の読み込み
    load_environment_variables()

    print("データベースバックアップユーティリティ")
    print("1. バックアップの作成")
    print("2. バックアップの復元")
    print("3. バックアップファイルの一覧表示")
    print("0. 終了")

    action = input("操作を選択してください: ")

    if action == "1":
        print("バックアップを作成します...")
        prompt_file = backup_prompts()
        dept_file = backup_departments()
        print(f"\nバックアップが完了しました。")
        print(f"プロンプト: {prompt_file}")
        print(f"診療科: {dept_file}")

    elif action == "2":
        list_backup_files()

        print("\n--- プロンプトの復元 ---")
        prompt_file = input("プロンプトバックアップファイルのパスを入力: ")
        if prompt_file:
            restore_prompts(prompt_file)

        print("\n--- 診療科の復元 ---")
        dept_file = input("診療科バックアップファイルのパスを入力: ")
        if dept_file:
            restore_departments(dept_file)

    elif action == "3":
        list_backup_files()

    elif action == "0":
        print("プログラムを終了します。")
    else:
        print("無効な選択です。")
