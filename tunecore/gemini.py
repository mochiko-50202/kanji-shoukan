"""Gemini API クライアント — weekly_news.py:35-67 のフォールバックパターンを移植・拡張"""

import base64
import json
import os
import re
import subprocess
from urllib.parse import urlparse

import requests

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

# responseSchema 対応モデルのみ（gemini-2.0-flash / 1.5-flash は responseSchema 非対応）
MODELS_AUDIO = ["gemini-2.5-flash", "gemini-1.5-pro"]
MODELS_TEXT = ["gemini-2.5-flash", "gemini-1.5-pro"]

# TuneCoreフィールドのJSONスキーマ（Gemini responseSchema 用）
TUNECORE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "release_title_ja":        {"type": "STRING"},
        "release_title_yomigana":  {"type": "STRING"},
        "release_title_en":        {"type": "STRING"},
        "genre":                   {"type": "STRING"},
        "subgenre":                {"type": "STRING"},
        "language":                {"type": "STRING"},
        "recording_year":          {"type": "INTEGER"},
        "track_title_ja":          {"type": "STRING"},
        "track_title_yomigana":    {"type": "STRING"},
        "track_title_en":          {"type": "STRING"},
        "description_ja":          {"type": "STRING"},
        "description_en":          {"type": "STRING"},
        "mood_tags":               {"type": "ARRAY", "items": {"type": "STRING"}},
        "genre_reason":            {"type": "STRING"},
    },
    "required": [
        "release_title_ja", "release_title_yomigana", "release_title_en",
        "genre", "subgenre", "language", "recording_year",
        "track_title_ja", "track_title_yomigana", "track_title_en",
        "description_ja", "description_en", "mood_tags", "genre_reason",
    ],
}


def _build_prompt(title: str, notes: str, genres: list[str]) -> str:
    genre_list = "、".join(genres)
    notes_line = f"\nユーザーメモ: {notes}" if notes else ""
    return f"""あなたはTuneCore Japan登録のエキスパートです。
以下の楽曲情報をもとに、TuneCore Japan登録に必要なフィールドをJSON形式で返してください。

曲タイトル: {title}{notes_line}

制約:
- タイトルヨミガナはカタカナのみ（ひらがな・漢字不可）。長音は「ー」を使用。
- ジャンルは必ず以下のリストから1つ選択: {genre_list}
- サブジャンルも同リストから選択（ジャンルと異なるもの）。
- 説明文（日本語）は200字以内。
- 説明文（英語）は200文字以内。
- languageは "Japanese" 固定。
- recording_yearは現在の年（西暦整数）。
- mood_tagsは3〜5個の英語タグ（例: melancholic, cinematic）。
- genre_reasonはジャンルを選んだ理由（日本語1文）。"""


def _call_with_parts(parts: list[dict], models: list[str]) -> dict:
    """指定モデルリストを順に試してJSONを返す（weekly_news.py:35-67 パターン）"""
    last_error = None
    for model in models:
        url = f"{BASE_URL}/{model}:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 3000,
                "responseMimeType": "application/json",
                "responseSchema": TUNECORE_SCHEMA,
            },
        }
        try:
            resp = requests.post(url, json=payload, timeout=55)
            if resp.status_code == 404:
                print(f"  モデル {model} は存在しません。次を試します...")
                continue
            resp.raise_for_status()
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            print(f"  モデル {model} で生成成功")
            return json.loads(text)
        except Exception as e:
            last_error = e
            print(f"  モデル {model} でエラー: {e}")
            continue
    raise RuntimeError(f"全モデルで失敗。最後のエラー: {last_error}")


def generate_with_audio(
    title: str,
    notes: str,
    genres: list[str],
    audio_bytes: bytes,
    mime_type: str,
) -> dict:
    """音声ファイルをbase64エンコードしてGeminiに送信。audio partを先に置く。"""
    prompt = _build_prompt(title, notes, genres)
    parts = [
        {"inlineData": {"mimeType": mime_type, "data": base64.b64encode(audio_bytes).decode()}},
        {"text": prompt},
    ]
    return _call_with_parts(parts, MODELS_AUDIO)


def generate_text_only(title: str, notes: str, genres: list[str]) -> dict:
    """音声なし — テキストメモのみでフィールド生成。"""
    prompt = _build_prompt(title, notes, genres)
    parts = [{"text": prompt}]
    return _call_with_parts(parts, MODELS_TEXT)


# --- URL からの音声ダウンロード ---

MAX_BYTES = 15 * 1024 * 1024


def _is_google_drive(url: str) -> bool:
    return "drive.google.com" in url


def _is_yt_dlp_supported(url: str) -> bool:
    domains = ["youtube.com", "youtu.be", "soundcloud.com", "nicovideo.jp"]
    parsed = urlparse(url)
    return any(d in parsed.netloc for d in domains)


def download_audio_from_url(url: str) -> tuple[bytes, str]:
    """URLから音声バイト列とMIMEタイプを返す。失敗時は RuntimeError。"""
    if _is_google_drive(url):
        return _download_gdrive(url)
    if _is_yt_dlp_supported(url):
        return _download_ytdlp(url)
    # 不明なURLは直接 GET を試みる
    return _download_direct(url)


def _download_gdrive(url: str) -> tuple[bytes, str]:
    m = re.search(r"/d/([a-zA-Z0-9_-]+)", url) or re.search(r"id=([a-zA-Z0-9_-]+)", url)
    if not m:
        raise ValueError("Google Drive ファイルIDを抽出できません")
    file_id = m.group(1)
    dl_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    r = requests.get(dl_url, stream=True, timeout=60)
    r.raise_for_status()
    data = b"".join(chunk for chunk in r.iter_content(65536))
    if len(data) > MAX_BYTES:
        raise ValueError(f"ダウンロードしたファイルが15MBを超えています（{len(data) // 1024 // 1024}MB）")
    return data, "audio/mpeg"


def _download_ytdlp(url: str) -> tuple[bytes, str]:
    result = subprocess.run(
        ["yt-dlp", "-f", "bestaudio[filesize<15M]/bestaudio", "-x",
         "--audio-format", "mp3", "--audio-quality", "5", "-o", "-", url],
        capture_output=True,
        timeout=90,
    )
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp エラー: {result.stderr.decode(errors='replace')[:500]}")
    data = result.stdout
    if len(data) > MAX_BYTES:
        raise ValueError(f"ダウンロードしたファイルが15MBを超えています（{len(data) // 1024 // 1024}MB）")
    if not data:
        raise RuntimeError("yt-dlp が空のデータを返しました")
    return data, "audio/mpeg"


def _download_direct(url: str) -> tuple[bytes, str]:
    r = requests.get(url, stream=True, timeout=60)
    r.raise_for_status()
    mime = r.headers.get("Content-Type", "audio/mpeg").split(";")[0].strip()
    data = b"".join(chunk for chunk in r.iter_content(65536))
    if len(data) > MAX_BYTES:
        raise ValueError(f"ダウンロードしたファイルが15MBを超えています（{len(data) // 1024 // 1024}MB）")
    return data, mime
