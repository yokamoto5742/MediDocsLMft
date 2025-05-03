import streamlit as st
from utils.exceptions import AppError, AuthError, APIError, DatabaseError

def handle_error(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AuthError as e:
            st.error(f"認証エラー: {str(e)}")
            return None
        except APIError as e:
            st.error(f"API接続エラー: {str(e)}")
            return None
        except DatabaseError as e:
            st.error(f"データベースエラー: {str(e)}")
            return None
        except AppError as e:
            st.error(f"エラーが発生しました: {str(e)}")
            return None
        except Exception as e:
            st.error(f"予期しないエラー: {str(e)}")
            return None
    return wrapper
