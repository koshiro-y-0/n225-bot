"""
generate_glossary.py
経済用語解説モジュール — 「解説:〇〇」コマンドに対応する用語解説を生成する
"""

from jinja2 import Environment, FileSystemLoader
from pathlib import Path

TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates"

# 用語解説データ
GLOSSARY = {
    "CPI": {
        "title": "CPI（消費者物価指数）",
        "sections": [
            {
                "heading": "CPIとは",
                "body": "消費者が購入する商品・サービスの価格変動を\n測る指数です。前年同月比で表示されます。",
            },
            {
                "heading": "3つの種類",
                "bullets": [
                    "総合CPI：すべての品目を含む",
                    "コアCPI：生鮮食品を除く（日銀が重視）",
                    "コアコアCPI：食料・エネルギーを除く",
                ],
            },
            {
                "heading": "なぜ重要？",
                "body": "日銀は「物価安定目標2%」を掲げており、\nCPIはその達成度を測る最重要指標です。\nCPIの動向は金融政策に直結します。",
            },
        ],
        "quote": "物価の安定は、あらゆる経済活動の\n基盤であると考えております。",
    },
    "短観": {
        "title": "日銀短観（全国企業短期経済観測調査）",
        "sections": [
            {
                "heading": "短観とは",
                "body": "日本銀行が四半期ごと（3・6・9・12月）に\n実施する企業向けアンケート調査です。\n約1万社の企業が回答します。",
            },
            {
                "heading": "DIの読み方",
                "bullets": [
                    "DI = 「良い」回答割合 − 「悪い」回答割合",
                    "DI > 0：景況感が良い企業が多い",
                    "DI < 0：景況感が悪い企業が多い",
                    "大企業製造業DIが最も注目される",
                ],
            },
            {
                "heading": "なぜ重要？",
                "body": "日銀の金融政策判断の重要な材料です。\n調査対象が広く、速報性が高いため\n景気の先行指標として世界中が注目します。",
            },
        ],
        "quote": "企業マインドの動向は、\n金融政策運営上、重要な判断材料です。",
    },
    "政策金利": {
        "title": "政策金利（無担保コール翌日物レート）",
        "sections": [
            {
                "heading": "政策金利とは",
                "body": "日本銀行が金融市場に対して誘導する\n短期金利の目標値です。\n正式名称は「無担保コール翌日物レート」。",
            },
            {
                "heading": "金利変更の影響",
                "bullets": [
                    "利上げ → 預金金利↑ 住宅ローン金利↑ 円高傾向",
                    "利下げ → 預金金利↓ 住宅ローン金利↓ 円安傾向",
                    "企業の借入コストに直結",
                    "株式市場にも大きな影響",
                ],
            },
            {
                "heading": "決定の仕組み",
                "body": "年8回開催される「金融政策決定会合」で\n9名の政策委員の多数決により決定されます。\n会合後に総裁が記者会見を行います。",
            },
        ],
        "quote": "金融政策の変更は、経済・物価情勢を\n総合的に判断した上で行います。",
    },
    "為替": {
        "title": "為替レート（USD/JPY）",
        "sections": [
            {
                "heading": "為替レートとは",
                "body": "異なる通貨の交換比率のことです。\nUSD/JPY = 150 は「1ドル = 150円」を意味します。",
            },
            {
                "heading": "円安・円高とは",
                "bullets": [
                    "円安：1ドルの価格が上昇（例: 140→150円）",
                    "円高：1ドルの価格が下落（例: 150→140円）",
                    "円安 → 輸出企業に有利、輸入品は値上がり",
                    "円高 → 輸入品が安くなる、輸出企業に不利",
                ],
            },
            {
                "heading": "為替変動の要因",
                "bullets": [
                    "日米の金利差（米国利上げ → 円安傾向）",
                    "貿易収支（輸出 > 輸入 → 円高傾向）",
                    "地政学リスク（リスクオフ → 円高傾向）",
                    "投機的な取引の影響",
                ],
            },
        ],
        "quote": "為替相場は経済のファンダメンタルズを\n反映して安定的に推移することが望ましい。",
    },
    "GDP": {
        "title": "GDP（国内総生産）",
        "sections": [
            {
                "heading": "GDPとは",
                "body": "一定期間に国内で生み出された\n付加価値の合計額です。\n経済の規模と成長を測る最も基本的な指標。",
            },
            {
                "heading": "実質と名目の違い",
                "bullets": [
                    "名目GDP：物価変動を含んだ金額ベース",
                    "実質GDP：物価変動を除いた数量ベース",
                    "実質GDPの成長率が「経済成長率」として注目される",
                    "四半期ごとに速報値・改定値が発表",
                ],
            },
            {
                "heading": "なぜ重要？",
                "body": "GDPがマイナス成長を2四半期連続で記録すると\n「テクニカル・リセッション（景気後退）」と\n判断されることがあります。",
            },
        ],
        "quote": "経済の持続的な成長のもとで、\n物価安定を実現することが重要です。",
    },
    "日銀": {
        "title": "日本銀行（BOJ）",
        "sections": [
            {
                "heading": "日本銀行とは",
                "body": "日本の中央銀行です。1882年に設立され、\n「物価の安定」と「金融システムの安定」を\n使命としています。",
            },
            {
                "heading": "主な役割",
                "bullets": [
                    "金融政策の決定・実行（金利操作など）",
                    "日本銀行券（紙幣）の発行",
                    "銀行の銀行（金融機関への資金供給）",
                    "政府の銀行（国庫金の出納）",
                ],
            },
            {
                "heading": "金融政策決定会合",
                "body": "年8回開催され、政策金利の変更や\n金融緩和・引締めの方針を決定します。\n総裁・副総裁2名・審議委員6名の計9名が参加。",
            },
        ],
        "quote": "中央銀行の責務は、国民経済の健全な発展に\n資することであると認識しております。",
    },
}

# 解説コマンド → GLOSSARYキーのマッピング
GLOSSARY_ALIASES = {
    "CPI": "CPI",
    "cpi": "CPI",
    "消費者物価": "CPI",
    "物価": "CPI",
    "短観": "短観",
    "たんかん": "短観",
    "政策金利": "政策金利",
    "金利": "政策金利",
    "為替": "為替",
    "かわせ": "為替",
    "ドル円": "為替",
    "GDP": "GDP",
    "gdp": "GDP",
    "日銀": "日銀",
    "にちぎん": "日銀",
    "BOJ": "日銀",
    "boj": "日銀",
    "日本銀行": "日銀",
}


def parse_glossary_command(text: str) -> str | None:
    """
    ユーザーメッセージから用語解説カテゴリを抽出する
    Args:
        text: ユーザーの送信テキスト（例: "解説:CPI"）
    Returns:
        GLOSSARYのキー名（マッチしなければ None）、"一覧" の場合は "一覧"
    """
    if not text.startswith("解説:") and not text.startswith("解説："):
        return None
    # "解説:" or "解説：" の後の文字列を取得
    keyword = text.split(":", 1)[-1] if ":" in text else text.split("：", 1)[-1]
    keyword = keyword.strip()

    if keyword == "一覧":
        return "一覧"

    return GLOSSARY_ALIASES.get(keyword)


def generate_glossary_list() -> str:
    """
    選択可能な用語一覧を返す
    Returns:
        用語一覧のテキスト
    """
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("glossary.j2")
    return template.render(mode="list", glossary=GLOSSARY)


def generate_glossary_report(key: str) -> str:
    """
    指定された用語の解説レポートを生成する
    Args:
        key: GLOSSARYのキー（例: "CPI", "短観"）
    Returns:
        解説レポート文字列
    """
    if key not in GLOSSARY:
        return f"⚠️ 「{key}」は未対応の用語です。\n「解説:一覧」で利用可能な用語を確認できます。"

    entry = GLOSSARY[key]
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("glossary.j2")
    return template.render(mode="detail", entry=entry)


if __name__ == "__main__":
    print(generate_glossary_list())
    print("\n" + "=" * 50 + "\n")
    for key in GLOSSARY:
        print(generate_glossary_report(key))
        print("\n" + "=" * 50 + "\n")
