import os
import ipaddress
import requests
import bcrypt
import flet as ft
from pymongo import MongoClient

from utils.config import get_config, MONGODB_URI, REQUIRE_LOGIN, IP_WHITELIST, IP_CHECK_ENABLED
from utils.constants import MESSAGES
from utils.db import DatabaseManager
from utils.env_loader import load_environment_variables
from utils.error_handlers import handle_error
from utils.exceptions import AuthError, DatabaseError

load_environment_variables()


def get_users_collection():
    """ユーザーコレクションを取得"""
    try:
        db_manager = DatabaseManager.get_instance()
        collection_name = os.environ.get("MONGODB_USERS_COLLECTION", "users")
        return db_manager.get_collection(collection_name)
    except Exception as e:
        raise DatabaseError(f"ユーザーコレクションの取得に失敗しました: {str(e)}")


def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())


def verify_password(password, hashed_password):
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password)


def register_user(username, password, is_admin=False):
    try:
        users_collection = get_users_collection()

        if users_collection.find_one({"username": username}):
            raise AuthError(MESSAGES["USER_EXISTS"])

        # 新規ユーザー情報の作成
        user_data = {
            "username": username,
            "password": hash_password(password),
            "is_admin": is_admin
        }

        users_collection.insert_one(user_data)
        return True, MESSAGES["REGISTRATION_SUCCESS"]
    except AuthError as e:
        return False, str(e)
    except Exception as e:
        raise DatabaseError(f"ユーザー登録に失敗しました: {str(e)}")


def change_password(username, current_password, new_password):
    try:
        users_collection = get_users_collection()
        user = users_collection.find_one({"username": username})

        if not user:
            raise AuthError("ユーザーが見つかりません")

        if not verify_password(current_password, user["password"]):
            raise AuthError("現在のパスワードが正しくありません")

        hashed_new_password = hash_password(new_password)
        users_collection.update_one(
            {"username": username},
            {"$set": {"password": hashed_new_password}}
        )

        return True, "パスワードが正常に変更されました"
    except AuthError as e:
        return False, str(e)
    except Exception as e:
        raise DatabaseError(f"パスワード変更に失敗しました: {str(e)}")


def authenticate_user(username, password):
    try:
        users_collection = get_users_collection()
        user = users_collection.find_one({"username": username})

        if not user:
            raise AuthError("ユーザー名またはパスワードが正しくありません")

        if verify_password(password, user["password"]):
            # セッションに保存するユーザーデータ
            user_data = {
                "username": user["username"],
                "is_admin": user.get("is_admin", False)
            }
            return True, user_data

        raise AuthError("ユーザー名またはパスワードが正しくありません")
    except AuthError as e:
        return False, str(e)
    except Exception as e:
        raise DatabaseError(f"認証中にエラーが発生しました: {str(e)}")


def login_ui(page, global_state, on_login_success):
    """ログイン画面のUI作成"""
    login_container = ft.Container(
        content=ft.Column(
            [
                ft.Text("退院時サマリ作成アプリ - ログイン", size=30, weight=ft.FontWeight.BOLD),
                ft.Tabs(
                    selected_index=0,
                    tabs=[
                        ft.Tab(
                            text="ログイン",
                            content=ft.Container(
                                margin=ft.margin.only(top=20),
                                content=login_form(page, global_state, on_login_success)
                            ),
                        ),
                        ft.Tab(
                            text="新規登録",
                            content=ft.Container(
                                margin=ft.margin.only(top=20),
                                content=register_form(page, global_state)
                            ),
                        ),
                    ],
                ),
            ]
        )
    )
    return login_container


def login_form(page, global_state, on_login_success):
    """ログインフォームの作成"""
    login_username = ft.TextField(label="ユーザー名", width=300)
    login_password = ft.TextField(label="パスワード", password=True, width=300)
    error_text = ft.Text("", color=ft.colors.RED)

    def handle_login(e):
        if not login_username.value or not login_password.value:
            error_text.value = "ユーザー名とパスワードを入力してください"
            page.update()
            return

        success, result = authenticate_user(login_username.value, login_password.value)
        if success:
            global_state["user"] = result
            on_login_success()
        else:
            error_text.value = result
            page.update()

    return ft.Column([
        login_username,
        login_password,
        error_text,
        ft.ElevatedButton("ログイン", on_click=handle_login)
    ], spacing=20)


def register_form(page, global_state):
    """新規登録フォームの作成"""
    register_username = ft.TextField(label="ユーザー名", width=300)
    register_password = ft.TextField(label="パスワード", password=True, width=300)
    confirm_password = ft.TextField(label="パスワード（確認）", password=True, width=300)
    message_text = ft.Text("", color=ft.colors.RED)

    def handle_register(e):
        if not register_username.value or not register_password.value:
            message_text.value = "ユーザー名とパスワードを入力してください"
            message_text.color = ft.colors.RED
            page.update()
            return

        if register_password.value != confirm_password.value:
            message_text.value = "パスワードが一致しません"
            message_text.color = ft.colors.RED
            page.update()
            return

        # 最初のユーザーを管理者として登録
        users_collection = get_users_collection()
        is_first_user = users_collection.count_documents({}) == 0

        success, msg = register_user(register_username.value, register_password.value, is_admin=is_first_user)
        if success:
            message_text.value = msg
            message_text.color = ft.colors.GREEN
            if is_first_user:
                message_text.value += "\nあなたに管理者権限が付与されました"
            # フォームをクリア
            register_username.value = ""
            register_password.value = ""
            confirm_password.value = ""
        else:
            message_text.value = msg
            message_text.color = ft.colors.RED
        page.update()

    return ft.Column([
        register_username,
        register_password,
        confirm_password,
        message_text,
        ft.ElevatedButton("登録", on_click=handle_register)
    ], spacing=20)


def logout(global_state):
    """ログアウト処理"""
    global_state["user"] = None
    return True


def require_login(global_state):
    """ログインが必要かどうかをチェック"""
    return global_state["user"] is not None


def get_current_user(global_state):
    """現在のユーザー情報を取得"""
    return global_state["user"]


def is_admin(global_state):
    """現在のユーザーが管理者かどうかを確認"""
    user = get_current_user(global_state)
    if user:
        return user.get("is_admin", False)
    return False


def password_change_ui(page, global_state):
    """パスワード変更画面のUI作成"""
    current_password = ft.TextField(label="現在のパスワード", password=True, width=300)
    new_password = ft.TextField(label="新しいパスワード", password=True, width=300)
    confirm_new_password = ft.TextField(label="新しいパスワード（確認）", password=True, width=300)
    message_text = ft.Text("", color=ft.colors.RED)

    user = global_state["user"]
    if not user:
        return ft.Text("ログインが必要です", color=ft.colors.RED)

    def handle_password_change(e):
        if not current_password.value or not new_password.value or not confirm_new_password.value:
            message_text.value = "すべての項目を入力してください"
            message_text.color = ft.colors.RED
            page.update()
            return

        if new_password.value != confirm_new_password.value:
            message_text.value = "新しいパスワードが一致しません"
            message_text.color = ft.colors.RED
            page.update()
            return

        success, msg = change_password(user["username"], current_password.value, new_password.value)
        if success:
            message_text.value = msg
            message_text.color = ft.colors.GREEN
            # フォームをクリア
            current_password.value = ""
            new_password.value = ""
            confirm_new_password.value = ""
        else:
            message_text.value = msg
            message_text.color = ft.colors.RED
        page.update()

    return ft.Column([
        ft.Text("パスワード変更", size=20, weight=ft.FontWeight.BOLD),
        current_password,
        new_password,
        confirm_new_password,
        message_text,
        ft.ElevatedButton("パスワードを変更", on_click=handle_password_change)
    ], spacing=20)


def can_edit_prompts(global_state):
    """プロンプト編集権限があるかどうかをチェック"""
    # ログイン不要モードの場合は誰でも編集可能
    if not REQUIRE_LOGIN:
        return True
    # ログイン必須モードの場合は管理者のみ編集可能
    return is_admin(global_state)


def is_ip_allowed(ip, whitelist_str):
    """IPアドレスがホワイトリストに含まれているかをチェック"""
    if not whitelist_str.strip():
        return True

    whitelist = [addr.strip() for addr in whitelist_str.split(",")]

    try:
        client_ip = ipaddress.ip_address(ip)
        for item in whitelist:
            if "/" in item:  # CIDR表記
                if client_ip in ipaddress.ip_network(item):
                    return True
            else:  # 単一のIPアドレス
                if ip == item:
                    return True
        return False
    except ValueError:
        return False


def get_client_ip():
    """クライアントのIPアドレスを取得 - Heroku環境用に最適化"""
    # デバッグ用にすべての環境変数を記録
    env_vars = {k: v for k, v in os.environ.items() if 'IP' in k.upper() or 'FORWARD' in k.upper() or 'X_' in k.upper()}
    print(f"IP関連の環境変数: {env_vars}")

    # Herokuの場合、実際のIPアドレスは特定の環境変数やリクエストヘッダーに格納されています
    # 方法1: X-Forwarded-For環境変数から取得
    forwarded_for = os.environ.get("X_FORWARDED_FOR") or os.environ.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        ip = forwarded_for.split(',')[0].strip()
        print(f"X-Forwarded-For環境変数から取得したIP: {ip}")
        return ip

    # 方法2: 外部サービスを使用してIPを取得
    try:
        # 安全なIPアドレス確認サービスを使用
        response = requests.get('https://api.ipify.org', timeout=3)
        if response.status_code == 200:
            ip = response.text
            print(f"外部サービスから取得したIP: {ip}")
            return ip
    except Exception as e:
        print(f"外部サービスからのIP取得エラー: {str(e)}")

    # すべての方法が失敗した場合はデフォルト値を返す
    default_ip = os.environ.get("REMOTE_ADDR", "127.0.0.1")
    print(f"デフォルトIPを使用: {default_ip}")
    return default_ip


def check_ip_access(whitelist_str, page):
    """IPアドレスのアクセス制限をチェック"""
    client_ip = get_client_ip()

    # IPが直接一致するか確認（ホワイトリスト内に完全一致するIPがある場合）
    if client_ip in [ip.strip() for ip in whitelist_str.split(',')]:
        return True

    # CIDR表記との照合など、より複雑なチェックは is_ip_allowed 関数に任せる
    if not is_ip_allowed(client_ip, whitelist_str):
        return False

    return True
