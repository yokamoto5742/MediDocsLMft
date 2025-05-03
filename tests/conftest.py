import os
import shutil
import pytest


@pytest.fixture(scope="session", autouse=True)
def cleanup_magicmock_dirs(request):
    yield

    root_dir = os.path.dirname(os.path.dirname(__file__))

    magicmock_dirs = [
        os.path.join(os.path.dirname(__file__), "MagicMock"),  # tests下のMagicMock
        os.path.join(root_dir, "MagicMock")  # プロジェクトルート直下のMagicMock
    ]

    for magicmock_dir in magicmock_dirs:
        if os.path.exists(magicmock_dir):
            print(f"\nクリーンアップ: {magicmock_dir} を削除します")
            try:
                shutil.rmtree(magicmock_dir)
                print(f"{magicmock_dir} の削除に成功しました")
            except Exception as e:
                print(f"{magicmock_dir} の削除中にエラーが発生しました: {e}")
