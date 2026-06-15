# Windows セットアップ手順

## 1. Python のインストール（まだの場合）
https://www.python.org/downloads/ からインストール
※「Add Python to PATH」に必ずチェックを入れる

## 2. 必要ライブラリのインストール
コマンドプロンプトを開いて以下を実行：
```
pip install requests
pip install pywin32
```

## 3. スクリプトをPCに保存
`print_weekly_news.py` を以下の場所に保存（例）：
```
C:\Users\あなたのユーザー名\Documents\weekly_news\print_weekly_news.py
```

## 4. NOTION_TOKEN を Windows 環境変数に設定
1. スタートメニューで「環境変数」と検索 →「システム環境変数の編集」
2.「環境変数」ボタン →「ユーザー環境変数」の「新規」
3. 変数名: `NOTION_TOKEN`
4. 変数値: GitHub Secrets に登録した Notion トークン（secret_xxx...）
5. OK → OK

## 5. タスクスケジューラの設定
1. スタートメニューで「タスクスケジューラ」を検索して開く
2.「基本タスクの作成」をクリック
3. 名前：`週刊ニュース印刷`
4. トリガー：毎週 → 月曜日 → 開始時刻 `08:30:00`
5. 操作：プログラムの開始
   - プログラム：`python`
   - 引数：`C:\Users\あなたのユーザー名\Documents\weekly_news\print_weekly_news.py`
6. 完了後、タスクを右クリック →「プロパティ」
7.「全般」タブ：
   - ☑「最高特権で実行する」にチェック
8.「条件」タブ：
   - ☑「タスクを実行するためにスリープを解除する」にチェック ← 重要！
9. OK

## 6. テスト実行
コマンドプロンプトで以下を実行して動作確認：
```
python C:\Users\あなたのユーザー名\Documents\weekly_news\print_weekly_news.py
```
`print_log.txt` に結果が記録されます。
