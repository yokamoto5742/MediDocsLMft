import os
import ipaddress
import requests

import bcrypt
import streamlit as st
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


@handle_error
def login_ui():
    st.title("退院時サマリ作成アプリ - ログイン")

    if "user" not in st.session_state:
        st.session_state.user = None

    if st.session_state.user is not None:
        return True

    login_tab, register_tab = st.tabs(["ログイン", "新規登録"])

    with login_tab:
        username = st.text_input("ユーザー名", key="login_username")
        password = st.text_input("パスワード", type="password", key="login_password")

        if st.button("ログイン", key="login_button"):
            if not username or not password:
                st.error("ユーザー名とパスワードを入力してください")
                return False

            success, result = authenticate_user(username, password)
            if success:
                st.session_state.user = result
                st.rerun()
            else:
                st.error(result)
                return False

    with register_tab:
        new_username = st.text_input("ユーザー名", key="register_username")
        new_password = st.text_input("パスワード", type="password", key="register_password")
        confirm_password = st.text_input("パスワード（確認）", type="password", key="confirm_password")

        if st.button("登録", key="register_button"):
            if not new_username or not new_password:
                st.error("ユーザー名とパスワードを入力してください")
                return False

            if new_password != confirm_password:
                st.error("パスワードが一致しません")
                return False

            # 最初のユーザーを管理者として登録
            users_collection = get_users_collection()
            is_first_user = users_collection.count_documents({}) == 0

            success, message = register_user(new_username, new_password, is_admin=is_first_user)
            if success:
                st.success(message)
                if is_first_user:
                    st.info("あなたに管理者権限が付与されました")
                return False
            else:
                st.error(message)
                return False

    return False


def logout():
    if "user" in st.session_state:
        st.session_state.user = None
        return True
    return False


def require_login():
    """ログインが必要なページの保護"""
    if "user" not in st.session_state or st.session_state.user is None:
        login_ui()
        return False
    return True


def get_current_user():
    if "user" in st.session_state:
        return st.session_state.user
    return None


def is_admin():
    """現在のユーザーが管理者かどうかを確認"""
    user = get_current_user()
    if user:
        return user.get("is_admin", False)
    return False


@handle_error
def password_change_ui():
    st.subheader("パスワード変更")

    user = get_current_user()
    if not user:
        raise AuthError("ログインが必要です")

    current_password = st.text_input("現在のパスワード", type="password", key="current_password")
    new_password = st.text_input("新しいパスワード", type="password", key="new_password")
    confirm_new_password = st.text_input("新しいパスワード（確認）", type="password", key="confirm_new_password")

    if st.button("パスワードを変更", key="change_password_button"):
        if not current_password or not new_password or not confirm_new_password:
            st.error("すべての項目を入力してください")
            return

        if new_password != confirm_new_password:
            st.error("新しいパスワードが一致しません")
            return

        success, message = change_password(user["username"], current_password, new_password)
        if success:
            st.success(message)
        else:
            st.error(message)


def can_edit_prompts():
    # ログイン不要モードの場合は誰でも編集可能
    if not REQUIRE_LOGIN:
        return True

    # ログイン必須モードの場合は管理者のみ編集可能
    return is_admin()


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

    # 方法3: リクエストからIPを取得（Streamlitの制約上、動作しない可能性あり）
    try:
        import tornado.web
        handler = tornado.web.RequestHandler()
        ip = handler.request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        if ip:
            print(f"Tornadoリクエストから取得したIP: {ip}")
            return ip
    except Exception as e:
        print(f"TornadoリクエストからのIP取得エラー: {str(e)}")

    # すべての方法が失敗した場合はデフォルト値を返す
    default_ip = os.environ.get("REMOTE_ADDR", "127.0.0.1")
    print(f"デフォルトIPを使用: {default_ip}")
    return default_ip


# check_ip_access 関数にデバッグ情報を追加
def check_ip_access(whitelist_str):
    """IPアドレスのアクセス制限をチェック"""
    client_ip = get_client_ip()

    # デバッグ情報
    st.write(f"検出されたIPアドレス: {client_ip}")
    st.write(f"アクセス許可IPリスト: {whitelist_str}")

    # IPが直接一致するか確認（ホワイトリスト内に完全一致するIPがある場合）
    if client_ip in [ip.strip() for ip in whitelist_str.split(',')]:
        return True

    # CIDR表記との照合など、より複雑なチェックは is_ip_allowed 関数に任せる
    if not is_ip_allowed(client_ip, whitelist_str):
        st.title("アクセスが制限されています")
        st.error(f"このIPアドレス（{client_ip}）からはアクセスできません。")
        st.info("このシステムはIPアドレスによるアクセス制限が設定されています。")
        st.info("システム管理者にお問い合わせください。")
        return False
    return True