#!/usr/bin/env python3
"""
週刊ニュース自動印刷スクリプト
- Windowsタスクスケジューラから毎週月曜 08:30 に自動実行
- Notionから今週のニュースを取得して EP-881A に印刷
- 失敗時は最大3回リトライ
"""

import requests
import datetime
import time
import os
import tempfile
import subprocess
import sys

# ==============================
# 設定（ここだけ変更してください）
# ==============================
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")  # 環境変数から読む
DATABASE_ID  = "335f337d-ddd6-80f7-87e7-d98f8a857545"
PRINTER_NAME = "EPSON EP-881A Series"  # Windowsのプリンター名（そのまま）
MAX_RETRIES  = 3
RETRY_WAIT   = 180   # 失敗後の待機秒数（3分）
NOTION_WAIT  = 120   # Notionにまだページがない場合の待機秒数（2分）
# ==============================

LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "print_log.txt")
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


def log(msg: str):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def get_monday() -> str:
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())
    return monday.strftime("%Y-%m-%d")


def fetch_pages(date_str: str) -> list:
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    payload = {
        "filter": {
            "property": "日付",
            "date": {"equals": date_str}
        },
        "sorts": [{"property": "名前", "direction": "ascending"}],
    }
    resp = requests.post(url, headers=NOTION_HEADERS, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()["results"]


def fetch_blocks(page_id: str) -> list:
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    resp = requests.get(url, headers=NOTION_HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()["results"]


def blocks_to_html(blocks: list) -> str:
    html = ""
    for b in blocks:
        t = b["type"]
        if t == "heading_3":
            text = "".join(r["plain_text"] for r in b["heading_3"]["rich_text"])
            html += f"<h3>{text}</h3>\n"
        elif t == "paragraph":
            text = "".join(r["plain_text"] for r in b["paragraph"]["rich_text"])
            if text.strip():
                html += f"<p>{text}</p>\n"
        elif t == "callout":
            text = "".join(r["plain_text"] for r in b["callout"]["rich_text"])
            html += f'<div class="callout">💡 {text}</div>\n'
        elif t == "divider":
            html += "<hr>\n"
    return html


def make_html(title: str, body: str) -> str:
    date_str = get_monday()
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
  @media print {{
    @page {{ margin: 15mm; }}
    body {{ margin: 0; }}
  }}
  body {{
    font-family: 'Meiryo UI', 'Yu Gothic UI', 'MS Gothic', sans-serif;
    font-size: 10.5pt; color: #111; margin: 15mm;
  }}
  h1  {{ font-size: 13pt; border-bottom: 2px solid #333;
         padding-bottom: 4px; margin-bottom: 12px; }}
  h3  {{ font-size: 11pt; color: #222; margin: 14px 0 4px; }}
  p   {{ margin: 4px 0; line-height: 1.65; }}
  .callout {{
    background: #f5f5f5; border-left: 3px solid #888;
    padding: 5px 10px; margin: 6px 0; font-size: 10pt;
  }}
  hr  {{ border: 0; border-top: 1px solid #ccc; margin: 10px 0; }}
  .footer {{ font-size: 8pt; color: #888; text-align: right;
             margin-top: 12px; border-top: 1px solid #ddd; padding-top: 4px; }}
</style>
</head>
<body>
<h1>{title}</h1>
{body}
<div class="footer">印刷日: {datetime.datetime.now().strftime('%Y年%m月%d日 %H:%M')}</div>
</body>
</html>"""


def print_file(html_path: str):
    """Windowsでサイレント印刷"""
    # まず pywin32 を試みる（インストール済みの場合）
    try:
        import win32api
        win32api.ShellExecute(
            0, "printto", html_path, f'"{PRINTER_NAME}"', ".", 0
        )
        return
    except ImportError:
        pass

    # PowerShell フォールバック（Edgeを使用）
    edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    if not os.path.exists(edge_path):
        edge_path = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"

    if os.path.exists(edge_path):
        subprocess.run([
            edge_path,
            "--headless",
            f"--print-to-pdf={html_path.replace('.html', '.pdf')}",
            f"file:///{html_path.replace(os.sep, '/')}",
        ], check=True, timeout=30)
        pdf_path = html_path.replace(".html", ".pdf")
        if os.path.exists(pdf_path):
            subprocess.run([
                "powershell", "-Command",
                f'Start-Process -FilePath "{pdf_path}" -Verb PrintTo -ArgumentList "{PRINTER_NAME}" -Wait'
            ], check=True, timeout=60)
            os.unlink(pdf_path)
    else:
        # 最終フォールバック: デフォルトブラウザで印刷ダイアログ
        subprocess.run([
            "powershell", "-Command",
            f'Start-Process "{html_path}" -Verb Print'
        ], check=True)


def main():
    if not NOTION_TOKEN:
        log("エラー: NOTION_TOKEN 環境変数が設定されていません")
        sys.exit(1)

    log("=" * 40)
    log("週刊ニュース自動印刷 開始")
    log("=" * 40)

    date_str = get_monday()
    log(f"対象日: {date_str}")

    tmp_files = []

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            log(f"試行 {attempt}/{MAX_RETRIES}")

            pages = fetch_pages(date_str)

            if not pages:
                log(f"Notionにまだページがありません。{NOTION_WAIT // 60}分後に再試行...")
                time.sleep(NOTION_WAIT)
                continue

            log(f"{len(pages)} ページを発見")

            for page in pages:
                title_parts = page["properties"]["名前"]["title"]
                title = title_parts[0]["plain_text"] if title_parts else "ニュース"
                page_id = page["id"]

                log(f"取得中: {title}")
                blocks = fetch_blocks(page_id)
                body   = blocks_to_html(blocks)
                html   = make_html(title, body)

                tmp = tempfile.NamedTemporaryFile(
                    mode="w", suffix=".html", encoding="utf-8",
                    delete=False, prefix="news_"
                )
                tmp.write(html)
                tmp.close()
                tmp_files.append(tmp.name)

                log(f"印刷送信: {title}")
                print_file(tmp.name)
                time.sleep(20)  # プリンター処理待ち

            # 後片付け
            time.sleep(30)
            for f in tmp_files:
                try:
                    os.unlink(f)
                except Exception:
                    pass

            log("=== 印刷完了 ===")
            return  # 成功終了

        except Exception as e:
            log(f"エラー: {e}")
            if attempt < MAX_RETRIES:
                log(f"{RETRY_WAIT // 60}分後に再試行します...")
                time.sleep(RETRY_WAIT)

    log("=== 3回失敗しました。print_log.txt を確認してください ===")
    sys.exit(1)


if __name__ == "__main__":
    main()
