"""YouTube URLから音声をダウンロードするサービス"""

import subprocess
import tempfile
import os
import re


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

    subprocess.run(
        [
            "yt-dlp",
            "-x",
            "--audio-format", "wav",
            "--audio-quality", "0",
            "-o", output_template,
            "--no-playlist",
            "--max-filesize", "50m",
            url,
        ],
        check=True,
        timeout=120,
        capture_output=True,
    )

    if not os.path.exists(output_path):
        raise RuntimeError("音声のダウンロードに失敗しました")

    return output_path
