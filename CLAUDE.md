# kanji-shoukan プロジェクト

## オーナー
prettymaids0223@gmail.com

---

## プロジェクト一覧

### 1. TuneCore 登録ヘルパー (`tunecore/`)

TuneCore Japan への楽曲登録作業を自動化するWebアプリ。MP3/WAVをアップロードするとGemini AIが全フィールドを生成し、コピペで登録できる。

**本番URL**: `https://kanji-shoukan-production.up.railway.app`

**アーティスト**:
- Jelly-fish（label: Jelly-fish / copyright: Jelly-fish）
- TANDORI-聖なる胃袋-（label: TANDORI-聖なる胃袋- / copyright: TANDORI-聖なる胃袋-）

**技術スタック**: FastAPI + Jinja2 + Alpine.js + Tailwind CSS CDN

**デプロイ**: Railway（GitHub main ブランチへのpushで自動デプロイ）
- Builder: Dockerfile（`tunecore/railway.toml` で自動検出）
- Root Directory: `tunecore`
- PORT: 8080（Railway自動注入）
- 環境変数: `GEMINI_API_KEY`（Railway Variables に設定済み）

**構成ファイル**:
```
tunecore/
├── main.py              # FastAPI エントリーポイント、/generate エンドポイント
├── gemini.py            # Gemini API クライアント（音声解析・テキスト生成）
├── config.py            # 設定管理（アーティスト・著作権フィールド組み立て）
├── tunecore_config.json # アーティスト・ジャンルリスト設定
├── templates/index.html # Web UI
├── Dockerfile
└── railway.toml
```

**ローカル起動**:
```bash
cd tunecore
pip install -r requirements.txt
GEMINI_API_KEY=xxx uvicorn main:app --reload
# → http://localhost:8000
```

**Gemini モデル**: `gemini-2.5-flash` → `gemini-1.5-pro`（フォールバック順）
- `gemini-2.0-flash` は responseSchema 非対応のため除外
- タイムアウト: 55秒（Railway プロキシの60秒制限内）

---

### 2. 週次ニュース自動生成 (`.github/workflows/weekly-news.yml`)

GitHub Actions で毎週自動実行。Gemini APIでニュースサマリーを生成してメール送信。

---

### 3. ローカルPC用スクリプト (`local-pc/`)

Windowsユーザー向けのPowerShellセットアップスクリプト。

---

## 開発ルール

- mainブランチへのpushでRailwayが自動デプロイ
- 機能開発は `claude/` プレフィックスのブランチで行い、mainにマージ
- `GEMINI_API_KEY` はコードにハードコードしない（環境変数で管理）

## よく使うコマンド

```bash
# ローカルでTuneCoreアプリを起動
cd tunecore && GEMINI_API_KEY=xxx uvicorn main:app --reload

# mainにpush（Railwayへの自動デプロイがトリガーされる）
git push origin main
```
