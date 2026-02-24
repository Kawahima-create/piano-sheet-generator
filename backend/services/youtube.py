"""YouTube URLから音声をダウンロードするサービス"""

import shutil
import subprocess
import sys
import tempfile
import os
import re

# venv内のyt-dlpバイナリのパスを取得
_YT_DLP = os.path.join(os.path.dirname(sys.executable), "yt-dlp")

# ffmpegのパスを検出（venv外のPATHも探す）
_FFMPEG_DIR = None
_ffmpeg = shutil.which("ffmpeg")
if not _ffmpeg:
    # Homebrew標準パスをフォールバック
    for candidate in ["/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg"]:
        if os.path.isfile(candidate):
            _ffmpeg = candidate
            break
if _ffmpeg:
    _FFMPEG_DIR = os.path.dirname(_ffmpeg)

# Node.jsランタイムのパスを検出（yt-dlpのYouTube JS認証に必要）
_NODE_PATH = shutil.which("node")
if not _NODE_PATH:
    for candidate in ["/opt/homebrew/bin/node", "/usr/local/bin/node"]:
        if os.path.isfile(candidate):
            _NODE_PATH = candidate
            break


def validate_youtube_url(url: str) -> bool:
    """YouTube URLの形式を検証"""
    pattern = r'^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[\w-]+'
    return bool(re.match(pattern, url))


def download_youtube_audio(url: str) -> str:
    """
    YouTube URLから音声をダウンロードしてWAVファイルとして保存。

    Args:
        url: YouTube URL

    Returns:
        ダウンロードしたWAVファイルのパス
    """
    if not validate_youtube_url(url):
        raise ValueError("無効なYouTube URLです")

    tmpdir = tempfile.mkdtemp()
    output_template = os.path.join(tmpdir, "audio.%(ext)s")
    output_path = os.path.join(tmpdir, "audio.wav")

    cmd = [
        _YT_DLP,
        "-x",
        "--audio-format", "wav",
        "--audio-quality", "0",
        "-o", output_template,
        "--no-playlist",
        "--max-filesize", "50m",
        "--remote-components", "ejs:github",
    ]
    if _NODE_PATH:
        cmd += ["--js-runtimes", f"node:{_NODE_PATH}"]
    if _FFMPEG_DIR:
        cmd += ["--ffmpeg-location", _FFMPEG_DIR]
    cmd.append(url)

    subprocess.run(
        cmd,
        check=True,
        timeout=120,
        capture_output=True,
    )

    if not os.path.exists(output_path):
        raise RuntimeError("音声のダウンロードに失敗しました")

    return output_path
