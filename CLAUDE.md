# 漢字召喚

**このリポジトリは漢字召喚アプリ専用。** 他のプロジェクトのファイルをここに置かない。

漢字の学習用Webアプリ（PWA）。ブラウザだけで動く静的サイトで、サーバー処理は無い。

- 公開URL: https://mochiko-50202.github.io/kanji-shoukan/
- 公開方法: GitHub Pages（main ブランチの内容がそのまま公開される）
- オーナー: prettymaids0223@gmail.com

## ファイル構成

```
index.html      本体
dictionary.js   漢字データ（JMdict由来・約6MB）
sw.js           Service Worker（オフライン動作用）
manifest.json   PWA設定（ホーム画面に追加したときの見え方）
icon.png        アプリアイコン（Canva製の透過PNG）
icon.svg        アイコンの元データ
make-icon.html  アイコン生成用のツールページ
qr.html         スマホで開くためのQRコード表示ページ
qrcode.min.js   QRコード生成ライブラリ
```

## 開発ルール

- **main への push がそのまま公開になる。** 途中の状態を push しない
- 機能開発は `claude/` プレフィックスのブランチで行い、動作を確認してから main にマージする
- 変更したら公開URLを実際に開いて表示を確認する（反映まで1〜2分かかる）

## ここに無いもの（2026-08-18に整理）

このリポジトリには、漢字召喚と無関係のものが3つ同居していた。すべて外に出した。

| 元の場所 | 中身 | 移動先 |
|---|---|---|
| `tunecore/` | TuneCore登録ヘルパー（Railwayのデプロイは消滅済み） | `Documents\Claude\tunecore\` |
| `local-pc/` | 週刊ニュースの旧・印刷スクリプト（失効したNotionトークン前提で動かない） | 削除（この履歴に残る） |
| `.github/workflows/weekly-news.yml` | 週次ニュース自動保存。7/12から6回連続失敗しGitHubが自動停止 | 削除（控えは `マイドライブ\Tools\weekly_news\github_backup_20260818\`） |

ニュース関連の現役の仕組みは `マイドライブ\Tools\weekly_news\` にある。**このリポジトリには戻さない。**
