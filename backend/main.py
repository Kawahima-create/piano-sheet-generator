"""耳コピ支援アプリ - バックエンドAPI"""

import os
import tempfile
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import logging

from services.transcribe import transcribe_audio, save_midi_to_temp
from services.youtube import download_youtube_audio, validate_youtube_url
from services.youtube_search import get_video_metadata, search_piano_covers
from services.arrange import midi_to_score, arrange_beginner, arrange_intermediate, arrange_advanced
from services.abc_export import score_to_abc
from services.ensemble import merge_transcriptions

logger = logging.getLogger(__name__)

app = FastAPI(title="Piano Sheet Generator API")

# CORS設定（フロントエンドからのアクセスを許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # デプロイ時は具体的なドメインに制限する
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class YouTubeRequest(BaseModel):
    url: str
    mode: str = "direct"  # "direct" | "demucs"
    song_title: str = ""
    artist: str = ""


class YouTubeAnalyzeRequest(BaseModel):
    url: str


class VideoMetadata(BaseModel):
    video_id: str
    title: str
    channel: str
    thumbnail: str
    duration_seconds: int
    artist: str = ""
    song_title: str = ""


class VideoCoverCandidate(VideoMetadata):
    url: str


class YouTubeAnalyzeResponse(BaseModel):
    original: VideoMetadata
    piano_covers: list[VideoCoverCandidate]


class EnsembleRequest(BaseModel):
    urls: list[str]  # ピアノカバーのURL一覧
    song_title: str = ""
    artist: str = ""


class DemucsStatusResponse(BaseModel):
    available: bool
    model_name: str


class SheetMusicResponse(BaseModel):
    beginner: str
    intermediate: str
    advanced: str
    key: str


def _process_midi(midi_data, song_title: str = "", artist: str = "") -> SheetMusicResponse:
    """PrettyMIDIオブジェクトから3レベルの楽譜を生成"""
    midi_path = save_midi_to_temp(midi_data)
    try:
        score, detected_key = midi_to_score(midi_path)

        beginner_score = arrange_beginner(score, detected_key)
        intermediate_score = arrange_intermediate(score, detected_key)
        advanced_score = arrange_advanced(score, detected_key)

        key_name = f"{detected_key.tonic.name} {detected_key.mode}"
        base_title = song_title or "Piano Arrangement"

        return SheetMusicResponse(
            beginner=score_to_abc(beginner_score, title=f"{base_title} (Beginner)", key_sig=str(detected_key), composer=artist),
            intermediate=score_to_abc(intermediate_score, title=f"{base_title} (Intermediate)", key_sig=str(detected_key), composer=artist),
            advanced=score_to_abc(advanced_score, title=f"{base_title} (Advanced)", key_sig=str(detected_key), composer=artist),
            key=key_name,
        )
    finally:
        os.unlink(midi_path)


def _process_audio(audio_path: str, song_title: str = "", artist: str = "") -> SheetMusicResponse:
    """音声ファイルを処理して3レベルの楽譜を生成"""
    midi_data = transcribe_audio(audio_path)
    return _process_midi(midi_data, song_title=song_title, artist=artist)


@app.get("/")
def health_check():
    return {"status": "ok", "message": "Piano Sheet Generator API"}


@app.post("/api/transcribe/upload", response_model=SheetMusicResponse)
async def transcribe_upload(file: UploadFile = File(...)):
    """音声ファイルをアップロードして楽譜を生成"""
    # ファイル形式の検証
    allowed_types = {"audio/mpeg", "audio/wav", "audio/x-wav", "audio/mp3"}
    if file.content_type and file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="対応していないファイル形式です。MP3またはWAVをアップロードしてください。",
        )

    # ファイルサイズ制限（20MB）
    contents = await file.read()
    if len(contents) > 20 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="ファイルサイズが大きすぎます（最大20MB）。",
        )

    # 一時ファイルに保存
    suffix = ".mp3" if file.filename and file.filename.endswith(".mp3") else ".wav"
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    try:
        os.write(fd, contents)
        os.close(fd)
        return _process_audio(tmp_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"処理中にエラーが発生しました: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.post("/api/youtube/analyze", response_model=YouTubeAnalyzeResponse)
async def analyze_youtube(request: YouTubeAnalyzeRequest):
    """YouTube URLのメタデータを取得し、ピアノカバーを検索"""
    if not validate_youtube_url(request.url):
        raise HTTPException(status_code=400, detail="無効なYouTube URLです。")

    try:
        metadata = get_video_metadata(request.url)
        covers = search_piano_covers(metadata["song_title"], metadata["artist"])
        return YouTubeAnalyzeResponse(
            original=VideoMetadata(**metadata),
            piano_covers=[VideoCoverCandidate(**c) for c in covers],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析中にエラーが発生しました: {str(e)}")


@app.post("/api/transcribe/youtube", response_model=SheetMusicResponse)
async def transcribe_youtube(request: YouTubeRequest):
    """YouTube URLから楽譜を生成（mode: direct/demucs）"""
    if not validate_youtube_url(request.url):
        raise HTTPException(status_code=400, detail="無効なYouTube URLです。")

    audio_path = None
    demucs_dir = None
    try:
        audio_path = download_youtube_audio(request.url)

        if request.mode == "demucs":
            from services.demucs_service import is_demucs_available, separate_audio
            if not is_demucs_available():
                raise HTTPException(status_code=400, detail="Demucsが利用できません。")
            stem_path = separate_audio(audio_path, stem="other")
            demucs_dir = os.path.dirname(os.path.dirname(os.path.dirname(stem_path)))
            return _process_audio(stem_path, song_title=request.song_title, artist=request.artist)

        return _process_audio(audio_path, song_title=request.song_title, artist=request.artist)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"処理中にエラーが発生しました: {str(e)}")
    finally:
        if audio_path and os.path.exists(audio_path):
            shutil.rmtree(os.path.dirname(audio_path), ignore_errors=True)
        if demucs_dir and os.path.exists(demucs_dir):
            shutil.rmtree(demucs_dir, ignore_errors=True)


@app.post("/api/transcribe/ensemble", response_model=SheetMusicResponse)
async def transcribe_ensemble(request: EnsembleRequest):
    """複数のピアノカバーを分析・統合して高精度な楽譜を生成"""
    if not request.urls:
        raise HTTPException(status_code=400, detail="URLが指定されていません。")
    if len(request.urls) > 5:
        raise HTTPException(status_code=400, detail="最大5件まで指定できます。")

    for url in request.urls:
        if not validate_youtube_url(url):
            raise HTTPException(status_code=400, detail=f"無効なYouTube URL: {url}")

    audio_dirs: list[str] = []
    try:
        # 各カバーをダウンロード→転写（失敗した個別カバーはスキップ）
        midi_list = []
        for i, url in enumerate(request.urls):
            try:
                logger.info(f"Ensemble: downloading {i+1}/{len(request.urls)}: {url}")
                audio_path = download_youtube_audio(url)
                audio_dirs.append(os.path.dirname(audio_path))
                logger.info(f"Ensemble: transcribing {i+1}/{len(request.urls)}")
                midi_data = transcribe_audio(audio_path)
                midi_list.append(midi_data)
            except Exception as e:
                logger.warning(f"Ensemble: skipping {i+1}/{len(request.urls)} ({url}): {e}")
                continue

        if not midi_list:
            raise RuntimeError("すべてのカバーのダウンロードに失敗しました")

        # アンサンブル統合
        logger.info(f"Ensemble: merging {len(midi_list)} transcriptions")
        merged_midi = merge_transcriptions(midi_list)

        return _process_midi(merged_midi, song_title=request.song_title, artist=request.artist)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"処理中にエラーが発生しました: {str(e)}")
    finally:
        for d in audio_dirs:
            if os.path.exists(d):
                shutil.rmtree(d, ignore_errors=True)


@app.get("/api/demucs/status", response_model=DemucsStatusResponse)
async def demucs_status():
    """Demucsの利用可否を確認"""
    try:
        from services.demucs_service import is_demucs_available
        return DemucsStatusResponse(available=is_demucs_available(), model_name="htdemucs")
    except Exception:
        return DemucsStatusResponse(available=False, model_name="htdemucs")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
