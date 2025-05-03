import pytest
from utils.text_processor import format_discharge_summary, parse_discharge_summary


def test_format_discharge_summary():
    """format_discharge_summary関数のテスト"""
    # 特殊文字とスペースの削除
    assert format_discharge_summary("* テスト *") == "テスト"
    assert format_discharge_summary("＊ テスト ＊") == "テスト"
    assert format_discharge_summary("# テスト #") == "テスト"
    assert format_discharge_summary("  テスト  ") == "テスト"

    # 複合的な特殊文字
    complex_text = "* 入院期間: 2023年1月1日 ～ 2023年1月10日 *\n# 現病歴: テスト #"
    expected = "入院期間:2023年1月1日～2023年1月10日\n現病歴:テスト"
    assert format_discharge_summary(complex_text) == expected

    # 空のテキスト
    assert format_discharge_summary("") == ""

    # 特殊文字のみ
    assert format_discharge_summary("* # ＊  ") == ""


def test_parse_discharge_summary_basic():
    """parse_discharge_summary関数の基本的なテスト"""
    # 基本的なサマリー
    summary = "入院期間:2023年1月1日～2023年1月10日\n現病歴:発熱と咳\n入院時検査:血液検査異常なし\n" \
              "入院中の治療経過:抗生物質投与\n退院申し送り:自宅療養\n禁忌/アレルギー:なし"

    result = parse_discharge_summary(summary)

    assert result["入院期間"] == "2023年1月1日～2023年1月10日"
    assert result["現病歴"] == "発熱と咳"
    assert result["入院時検査"] == "血液検査異常なし"
    assert result["入院中の治療経過"] == "抗生物質投与"
    assert result["退院申し送り"] == "自宅療養"
    assert result["禁忌/アレルギー"] == "なし"


def test_parse_discharge_summary_multi_line():
    """複数行のセクションを含むサマリーの解析テスト"""
    summary = "入院期間:2023年1月1日～2023年1月10日\n" \
              "現病歴:発熱と咳\n" \
              "その後、呼吸困難も出現\n" \
              "入院時検査:血液検査\n" \
              "胸部レントゲン\n" \
              "入院中の治療経過:抗生物質投与\n" \
              "退院申し送り:自宅療養\n" \
              "禁忌/アレルギー:なし"

    result = parse_discharge_summary(summary)

    assert result["現病歴"] == "発熱と咳\nその後、呼吸困難も出現"
    assert result["入院時検査"] == "血液検査\n胸部レントゲン"


def test_parse_discharge_summary_section_variants():
    """セクション名のバリエーションのテスト"""
    # 「禁忌・アレルギー」と「禁忌/アレルギー」の両方をテスト
    summary1 = "禁忌/アレルギー:ペニシリン"
    result1 = parse_discharge_summary(summary1)
    assert result1["禁忌/アレルギー"] == "ペニシリン"

    summary2 = "禁忌・アレルギー:ペニシリン"
    result2 = parse_discharge_summary(summary2)
    assert result2["禁忌/アレルギー"] == "ペニシリン"


def test_parse_discharge_summary_missing_sections():
    """一部のセクションが欠けているサマリーの解析テスト"""
    # 一部のセクションがない場合
    summary = "入院期間:2023年1月1日～2023年1月10日\n現病歴:テスト病歴"

    result = parse_discharge_summary(summary)

    assert result["入院期間"] == "2023年1月1日～2023年1月10日"
    assert result["現病歴"] == "テスト病歴"
    assert result["入院時検査"] == ""
    assert result["入院中の治療経過"] == ""
    assert result["退院申し送り"] == ""
    assert result["禁忌/アレルギー"] == ""


def test_parse_discharge_summary_empty():
    """空のサマリーの解析テスト"""
    result = parse_discharge_summary("")

    assert result["入院期間"] == ""
    assert result["現病歴"] == ""
    assert result["入院時検査"] == ""
    assert result["入院中の治療経過"] == ""
    assert result["退院申し送り"] == ""
    assert result["禁忌/アレルギー"] == ""


def test_parse_discharge_summary_colon_variations():
    """コロンありなしの変換のテスト"""
    # コロンなしのケース
    summary1 = "入院期間 2023年1月1日～2023年1月10日"
    result1 = parse_discharge_summary(summary1)
    assert result1["入院期間"] == "2023年1月1日～2023年1月10日"

    # コロンありのケース
    summary2 = "入院期間:2023年1月1日～2023年1月10日"
    result2 = parse_discharge_summary(summary2)
    assert result2["入院期間"] == "2023年1月1日～2023年1月10日"


def test_parse_discharge_summary_with_extra_content():
    """関連しないコンテンツを含むサマリーの解析テスト"""
    summary = "患者ID: 12345\n" \
              "入院期間:2023年1月1日～2023年1月10日\n" \
              "担当医: 山田医師\n" \
              "現病歴:発熱と咳\n" \
              "入院時検査:血液検査"

    result = parse_discharge_summary(summary)

    # 関連しない行は適切な項目に含まれないことを確認
    assert "患者ID: 12345" not in result["入院期間"]
    assert "担当医: 山田医師" not in result["現病歴"]
    assert result["入院期間"] == "2023年1月1日～2023年1月10日\n担当医: 山田医師"
    assert result["現病歴"] == "発熱と咳"
    assert result["入院時検査"] == "血液検査"
