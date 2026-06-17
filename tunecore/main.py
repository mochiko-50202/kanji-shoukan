"""TuneCore 登録ヘルパー — FastAPI エントリーポイント"""

import os
from datetime import date
from pathlib import Path

import magic
from fastapi import FastAPI, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

import config as cfg
import gemini

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="TuneCore 登録ヘルパー")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

MAX_BYTES = 15 * 1024 * 1024
ALLOWED_MIME_PREFIXES = ("audio/",)


class TuneCoreFields(BaseModel):
    release_title_ja: str
    release_title_yomigana: str
    release_title_en: str
    genre: str
    subgenre: str
    language: str
    recording_year: int
    copyright_notice: str
    phonogram_copyright: str
    track_title_ja: str
    track_title_yomigana: str
    track_title_en: str
    explicit_content: bool
    description_ja: str
    description_en: str
    mood_tags: list[str]
    genre_reason: str
    audio_analyzed: bool
    warnings: list[str]


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    app_config = cfg.load()
    return templates.TemplateResponse(
        request,
        "index.html",
        {"artists": app_config["artists"]},
    )


@app.post("/generate")
@limiter.limit("5/minute")
async def generate(
    request: Request,
    title: str = Form(...),
    artist_id: str = Form(...),
    artist_custom_ja: str = Form(""),
    artist_custom_en: str = Form(""),
    notes: str = Form(""),
    audio_file: UploadFile | None = None,
    audio_url: str = Form(""),
) -> JSONResponse:
    # --- アーティスト解決 ---
    if artist_id == "custom":
        if not artist_custom_ja.strip():
            raise HTTPException(422, "アーティスト名（日本語）を入力してください")
        artist = {
            "name_ja": artist_custom_ja.strip(),
            "name_en": artist_custom_en.strip() or artist_custom_ja.strip(),
        }
    else:
        artist = cfg.get_artist(artist_id)
        if artist is None:
            raise HTTPException(422, f"不明なアーティストID: {artist_id}")

    genres = cfg.get_genres()
    year = date.today().year
    warnings: list[str] = []
    audio_analyzed = False
    audio_bytes: bytes | None = None
    mime_type: str | None = None

    # --- 音源の取得 ---
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_BYTES + 65536:
        raise HTTPException(413, "ファイルサイズが15MBを超えています")

    if audio_file and audio_file.filename:
        audio_bytes = await audio_file.read()
        if len(audio_bytes) > MAX_BYTES:
            raise HTTPException(413, "ファイルサイズが15MBを超えています")
        detected = magic.from_buffer(audio_bytes[:2048], mime=True)
        if not any(detected.startswith(p) for p in ALLOWED_MIME_PREFIXES):
            raise HTTPException(415, f"音声ファイル（MP3/WAV等）のみ対応しています（検出: {detected}）")
        mime_type = detected

    elif audio_url.strip():
        try:
            audio_bytes, mime_type = gemini.download_audio_from_url(audio_url.strip())
            # ダウンロード済み音声にも MIME 検証
            detected = magic.from_buffer(audio_bytes[:2048], mime=True)
            if not any(detected.startswith(p) for p in ALLOWED_MIME_PREFIXES):
                audio_bytes = None
                warnings.append(f"URLからのダウンロード成功しましたが音声ファイルではありません（{detected}）。テキストモードで生成します。")
            else:
                mime_type = detected
        except Exception as e:
            warnings.append(f"URL音源の取得に失敗しました（{e}）。テキストメモのみで生成します。")
            audio_bytes = None

    # --- Gemini 呼び出し ---
    try:
        if audio_bytes and mime_type:
            raw = gemini.generate_with_audio(title, notes, genres, audio_bytes, mime_type)
            audio_analyzed = True
        else:
            raw = gemini.generate_text_only(title, notes, genres)
    except Exception as e:
        if audio_bytes:
            # 音声解析失敗 → テキストモードフォールバック
            warnings.append(f"音声解析に失敗しました（{e}）。テキストメモのみで再生成しました。")
            try:
                raw = gemini.generate_text_only(title, notes, genres)
            except Exception as e2:
                raise HTTPException(502, f"AI生成に失敗しました: {e2}") from e2
        else:
            raise HTTPException(502, f"AI生成に失敗しました: {e}") from e

    # --- フィールド組み立て ---
    # ヨミガナ検証（カタカナ以外が含まれている場合は警告）
    for field_key in ("release_title_yomigana", "track_title_yomigana"):
        val = raw.get(field_key, "")
        import re
        if val and not re.fullmatch(r"[ァ-ヿ\s・ー]+", val):
            warnings.append(f"{field_key} にカタカナ以外の文字が含まれています（要確認）: {val}")

    # ジャンル検証
    if raw.get("genre") and raw["genre"] not in genres:
        warnings.append(f"ジャンル「{raw['genre']}」はTuneCoreのリストにない可能性があります（要確認）")

    # 著作権フィールドはサーバー側で組み立て（Geminiに任せない）
    copyright_notice = cfg.build_copyright(year, artist)
    phonogram_copyright = cfg.build_phonogram(year, artist)
    if not copyright_notice:
        warnings.append("tunecore_config.json の copyright_holder が未設定です")
    if not phonogram_copyright:
        warnings.append("tunecore_config.json の label_name が未設定です")

    fields = TuneCoreFields(
        release_title_ja=raw.get("release_title_ja", title),
        release_title_yomigana=raw.get("release_title_yomigana", ""),
        release_title_en=raw.get("release_title_en", ""),
        genre=raw.get("genre", ""),
        subgenre=raw.get("subgenre", ""),
        language=raw.get("language", "Japanese"),
        recording_year=raw.get("recording_year", year),
        copyright_notice=copyright_notice,
        phonogram_copyright=phonogram_copyright,
        track_title_ja=raw.get("track_title_ja", title),
        track_title_yomigana=raw.get("track_title_yomigana", ""),
        track_title_en=raw.get("track_title_en", ""),
        explicit_content=cfg.load().get("explicit_content", False),
        description_ja=raw.get("description_ja", ""),
        description_en=raw.get("description_en", ""),
        mood_tags=raw.get("mood_tags", []),
        genre_reason=raw.get("genre_reason", ""),
        audio_analyzed=audio_analyzed,
        warnings=warnings,
    )

    return JSONResponse(fields.model_dump())


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/config")
async def get_config():
    """フロントエンド用: アーティストリストを返す"""
    app_config = cfg.load()
    return {"artists": app_config["artists"]}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
