#!/usr/bin/env python3
"""毎週月曜日: Gemini APIでニュース生成 → Notion APIに保存"""

import os
import sys
import json
import datetime
import requests

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
NOTION_TOKEN = os.environ["NOTION_TOKEN"]
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID", "335f337d-ddd6-80f7-87e7-d98f8a857545")

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

def get_target_monday() -> datetime.date:
    """コマンドライン引数があればその日付、なければ直近の月曜日"""
    if len(sys.argv) > 1:
        return datetime.date.fromisoformat(sys.argv[1])
    today = datetime.date.today()
    return today - datetime.timedelta(days=today.weekday())


def call_gemini(prompt: str) -> list[dict]:
    """Gemini APIを呼んでJSONリストを返す"""
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 3000,
            "responseMimeType": "application/json",
        },
    }
    resp = requests.post(url, json=payload, timeout=90)
    resp.raise_for_status()
    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)


def build_notion_blocks(items: list[dict]) -> list[dict]:
    """
    items は [{title, body, keywords, question}, ...] のリスト。
    Notion REST API 用のブロックリストに変換する。
    """
    blocks = []
    for item in items:
        # 見出し
        blocks.append({
            "object": "block",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{"type": "text", "text": {"content": item["title"]}}]
            },
        })
        # 本文
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": item["body"]}}]
            },
        })
        # キーワード（青色）
        keyword_text = "キーワード: " + "  ".join(item["keywords"])
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": keyword_text},
                        "annotations": {"bold": True, "color": "blue"},
                    }
                ]
            },
        })
        # 今週の問い（コールアウト）
        blocks.append({
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [
                    {"type": "text", "text": {"content": f"今週の問い: {item['question']}"}}
                ],
                "icon": {"type": "emoji", "emoji": "💡"},
            },
        })
        # 区切り線
        blocks.append({"object": "block", "type": "divider", "divider": {}})
    return blocks


def create_notion_page(title: str, date_str: str, blocks: list[dict]) -> str:
    url = "https://api.notion.com/v1/pages"
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "名前": {"title": [{"text": {"content": title}}]},
            "日付": {"date": {"start": date_str}},
        },
        "children": blocks[:100],
    }
    resp = requests.post(url, headers=NOTION_HEADERS, json=payload, timeout=30)
    resp.raise_for_status()
    page_id = resp.json()["id"]
    print(f"  作成完了: {title} (ID: {page_id})")
    return page_id


def main():
    monday = get_target_monday()
    date_str = monday.strftime("%Y-%m-%d")
    day_label = f"{monday.month:02d}月{monday.day:02d}日（月）"
    print(f"=== {date_str} ({day_label}) のニュースを生成中 ===")

    ai_prompt = f"""
あなたは障害福祉事業所の経営者向けAIニュースキュレーターです。
{date_str}時点の最新AIニュースを5件、以下のJSONスキーマで返してください。
JSONのみを返し、他のテキストは不要です。

[
  {{
    "title": "ニュースの見出し（30字以内）",
    "body": "2〜3文の説明。具体的な企業名・数値を含む。",
    "keywords": ["キーワード1", "キーワード2", "キーワード3", "キーワード4", "キーワード5"],
    "question": "障害福祉事業所として今週考えるべき実践的な問い（1文）"
  }}
]

OpenAI・Google・Anthropic・Microsoft・日本政府のAI政策など多様なトピックを取り上げてください。
"""

    welfare_prompt = f"""
あなたは障害福祉事業所の経営者向けニュースキュレーターです。
{date_str}時点の最新障害福祉ニュースを5件、以下のJSONスキーマで返してください。
JSONのみを返し、他のテキストは不要です。

[
  {{
    "title": "ニュースの見出し（30字以内）",
    "body": "2〜3文の説明。厚生労働省・自治体・報酬改定等の具体的な情報を含む。",
    "keywords": ["キーワード1", "キーワード2", "キーワード3", "キーワード4", "キーワード5"],
    "question": "事業所として今週取り組むべき具体的な問い（1文）"
  }}
]

報酬改定・就労支援・地域生活支援・人材確保・ICT化など多様なトピックを取り上げてください。
"""

    print("AIニュースを生成中...")
    ai_items = call_gemini(ai_prompt)
    ai_blocks = build_notion_blocks(ai_items)

    print("障害福祉ニュースを生成中...")
    welfare_items = call_gemini(welfare_prompt)
    welfare_blocks = build_notion_blocks(welfare_items)

    print("Notionに保存中...")
    create_notion_page(f"{day_label}のAIニュース", date_str, ai_blocks)
    create_notion_page(f"{day_label}の障害福祉ニュース", date_str, welfare_blocks)

    print("=== 完了 ===")


if __name__ == "__main__":
    main()
