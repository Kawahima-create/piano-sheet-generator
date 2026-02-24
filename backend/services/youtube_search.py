"""YouTube動画のメタデータ取得とピアノカバー検索サービス"""

import json
import os
import re
import subprocess
import sys

_YT_DLP = os.path.join(os.path.dirname(sys.executable), "yt-dlp")


def get_video_metadata(url: str) -> dict:
    """YouTube動画のメタデータ（タイトル・チャンネル・サムネイル等）を取得"""
    result = subprocess.run(
        [_YT_DLP, "--dump-json", "--no-download", "--no-playlist", url],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"メタデータの取得に失敗: {result.stderr[:200]}")

    info = json.loads(result.stdout)
    return {
        "video_id": info.get("id", ""),
        "title": info.get("title", ""),
        "channel": info.get("channel", info.get("uploader", "")),
        "thumbnail": info.get("thumbnail", ""),
        "duration_seconds": info.get("duration", 0) or 0,
    }


def search_piano_covers(title: str, max_results: int = 5) -> list[dict]:
    """曲タイトルでYouTubeから「piano cover」を検索"""
    clean = _clean_title(title)
    query = f"ytsearch{max_results}:{clean} piano cover"

    result = subprocess.run(
        [_YT_DLP, "--dump-json", "--no-download", "--flat-playlist", query],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        return []

    covers = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        try:
            info = json.loads(line)
            vid = info.get("id", "")
            if not vid:
                continue
            covers.append({
                "video_id": vid,
                "title": info.get("title", ""),
                "channel": info.get("channel", info.get("uploader", "")),
                "thumbnail": f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg",
                "duration_seconds": info.get("duration", 0) or 0,
                "url": f"https://www.youtube.com/watch?v={vid}",
            })
        except json.JSONDecodeError:
            continue

    return covers


def _clean_title(title: str) -> str:
    """動画タイトルからノイズ（【MV】, Official Video等）を除去"""
    noise = [
        r"【.*?】", r"\[.*?\]", r"\(.*?\)",
        r"Official\s*(Music\s*)?Video", r"Official\s*MV",
        r"\bMV\b", r"\bPV\b",
        r"Full\s*Ver\.?", r"Short\s*Ver\.?",
        r"Lyric\s*Video", r"\bAudio\b",
        r"feat\..*", r"ft\..*",
    ]
    cleaned = title
    for pat in noise:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[/\-|]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned
