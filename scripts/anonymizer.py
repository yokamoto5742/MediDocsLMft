import re
import time

def anonymize_text(input_text):

  pattern = re.compile(
      r"^([^\u3000\s]+[\u3000\s]+)"
      r".+?"
      r"[\u3000\s]+"
      r"(\d{1,2}:\d{2})$",
      re.MULTILINE
  )

  anonymized_text = pattern.sub(lambda m: f"{m.group(1)}{m.group(2)}", input_text)

  return anonymized_text

file_path = 'カルテ記事医師のみ.txt'
try:
    with open(file_path, 'r', encoding='utf-8') as f:
        original_text = f.read()

    start_time = time.time()

    processed_text = anonymize_text(original_text)

    end_time = time.time()

    processing_time = end_time - start_time

    # 結果を出力
    print("--- 元のテキスト ---")
    print("\n--- 匿名化後のテキスト ---")
    print(processed_text)
    print(f"\n--- 処理時間: {processing_time:.6f} 秒 ---")

    output_file_path = '匿名加工済みテキスト.txt'
    with open(output_file_path, 'w', encoding='utf-8') as f:
        f.write(processed_text)
    print(f"\n匿名化後のテキストを '{output_file_path}' に保存しました。")

except FileNotFoundError:
    print(f"エラー: ファイル '{file_path}' が見つかりません。")
except Exception as e:
    print(f"エラーが発生しました: {e}")
