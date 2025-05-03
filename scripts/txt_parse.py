import re
import json
import io

def parse_medical_text(text):
    """
    カルテ形式のテキストを解析し、構造化されたデータのリスト（JSON形式に適したもの）を返す。

    Args:
        text (str): 解析対象のテキストデータ。

    Returns:
        list: 各エントリを辞書として格納したリスト。
              各辞書には 'date', 'days_in_hospital', 'department',
              'time', 'soap_section', 'content' が含まれる。（'doctor', 'insurance'は削除される）
    """
    records = []
    current_date = None
    current_days_in_hospital = None
    current_entry_info = {}
    current_soap_section = None
    content_buffer = ""

    # 正規表現パターン
    # 日付行: 例 "2025/04/18(金)　（入院 71 日目）"
    date_pattern = re.compile(r"(\d{4}/\d{2}/\d{2}\(.?\))\s*（入院\s*(\d+)\s*日目）")
    # エントリ情報行: 例 "内科　　波部　孝弘　　国保　　12:41"
    # doctorとinsuranceをキャプチャするが、後で削除する
    entry_pattern = re.compile(r"(.+?)\s+(.+?)\s+(.+?)\s+(\d{2}:\d{2})")
    # SOAPセクション行: 例 "A >"
    soap_pattern = re.compile(r"([SOAPF])\s*>")

    # テキストを行ごとに処理
    for line in io.StringIO(text):
        line = line.strip()
        if not line:
            continue

        date_match = date_pattern.match(line)
        entry_match = entry_pattern.match(line)
        soap_match = soap_pattern.match(line)

        # 新しい日付が見つかった場合
        if date_match:
            # 前のセクションの内容を保存
            if current_entry_info and current_soap_section and content_buffer.strip():
                record = current_entry_info.copy()
                record['soap_section'] = current_soap_section
                record['content'] = content_buffer.strip()
                # doctorとinsuranceを削除
                if 'doctor' in record: del record['doctor']
                if 'insurance' in record: del record['insurance']
                records.append(record)

            current_date = date_match.group(1)
            current_days_in_hospital = int(date_match.group(2))
            current_entry_info = {} # 新しい日付でエントリ情報をリセット
            current_soap_section = None
            content_buffer = ""
            continue # 次の行へ

        # 新しいエントリ情報が見つかった場合
        elif entry_match and current_date: # 日付が設定されている場合のみ
             # 前のセクションの内容を保存
            if current_entry_info and current_soap_section and content_buffer.strip():
                record = current_entry_info.copy()
                record['soap_section'] = current_soap_section
                record['content'] = content_buffer.strip()
                 # doctorとinsuranceを削除
                if 'doctor' in record: del record['doctor']
                if 'insurance' in record: del record['insurance']
                records.append(record)

            # 一時的にdoctorとinsuranceを含めて情報を格納
            current_entry_info = {
                'date': current_date,
                'days_in_hospital': current_days_in_hospital,
                'department': entry_match.group(1).strip(),
                '_doctor_temp': entry_match.group(2).strip(), # 一時キー
                '_insurance_temp': entry_match.group(3).strip(), # 一時キー
                'time': entry_match.group(4).strip()
            }
            current_soap_section = None # 新しいエントリでSOAPセクションをリセット
            content_buffer = ""
            continue # 次の行へ

        # 新しいSOAPセクションが見つかった場合
        elif soap_match and current_entry_info: # エントリ情報がある場合のみ
             # 前のセクションの内容を保存
            if current_soap_section and content_buffer.strip():
                record = current_entry_info.copy()
                record['soap_section'] = current_soap_section
                record['content'] = content_buffer.strip()
                # doctorとinsuranceを削除 (一時キーも削除)
                if '_doctor_temp' in record: del record['_doctor_temp']
                if '_insurance_temp' in record: del record['_insurance_temp']
                if 'doctor' in record: del record['doctor'] # 念のため
                if 'insurance' in record: del record['insurance'] # 念のため
                records.append(record)

            current_soap_section = soap_match.group(1)
            content_buffer = "" # 新しいセクションでバッファをクリア
            continue # 次の行へ

        # SOAPセクションの内容行の場合
        elif current_soap_section and current_entry_info:
            content_buffer += line + "\n" # 内容をバッファに追加（改行を含む）

    # ループ終了後、最後のセクションの内容を保存
    if current_entry_info and current_soap_section and content_buffer.strip():
        record = current_entry_info.copy()
        record['soap_section'] = current_soap_section
        record['content'] = content_buffer.strip()
        # doctorとinsuranceを削除 (一時キーも削除)
        if '_doctor_temp' in record: del record['_doctor_temp']
        if '_insurance_temp' in record: del record['_insurance_temp']
        if 'doctor' in record: del record['doctor'] # 念のため
        if 'insurance' in record: del record['insurance'] # 念のため
        records.append(record)

    # ******* 変更点 *******
    # recordsリスト内の各辞書からdoctorとinsuranceを最終的に削除
    final_records = []
    for record in records:
        # doctorとinsuranceが存在すれば削除
        record.pop('doctor', None)
        record.pop('insurance', None)
        # 一時キーも確実に削除
        record.pop('_doctor_temp', None)
        record.pop('_insurance_temp', None)
        final_records.append(record)
    # ***********************

    return final_records # 削除処理後のリストを返す

# --- メイン処理 ---
# ファイルからテキストを読み込む (ファイルパスは適宜変更してください)
file_path = 'カルテ記事医師のみ.txt'
try:
    with open(file_path, 'r', encoding='utf-8') as f:
        sample_text = f.read()

    # テキストを解析 (この時点でdoctor, insuranceは削除されている)
    parsed_data = parse_medical_text(sample_text) #

    # 結果をJSON形式で出力（整形して表示）
    json_output = json.dumps(parsed_data, indent=2, ensure_ascii=False) #
    print(json_output)

    # JSONファイルとして保存する場合
    output_file_path = 'parsed_medical_data.json' # 出力ファイル名を変更
    with open(output_file_path, 'w', encoding='utf-8') as outfile:
        json.dump(parsed_data, outfile, indent=2, ensure_ascii=False) #
    print(f"\n修正された解析結果を {output_file_path} に保存しました。")

except FileNotFoundError:
    print(f"エラー: ファイル '{file_path}' が見つかりません。") #
except Exception as e:
    print(f"エラーが発生しました: {e}") #
