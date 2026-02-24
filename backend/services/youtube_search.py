"""YouTube動画のメタデータ取得とピアノカバー検索サービス"""

import json
import os
import re
import subprocess
import sys
import unicodedata

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
    raw_title = info.get("title", "")
    channel = info.get("channel", info.get("uploader", ""))
    artist_name = info.get("artist", "") or ""
    track_name = info.get("track", "") or ""

    # yt-dlpがartist/trackを提供しない場合、タイトルから抽出
    if not artist_name or not track_name:
        extracted_artist, extracted_song = _extract_artist_and_song(raw_title, channel)
        if not artist_name:
            artist_name = extracted_artist
        if not track_name:
            track_name = extracted_song

    return {
        "video_id": info.get("id", ""),
        "title": raw_title,
        "channel": channel,
        "thumbnail": info.get("thumbnail", ""),
        "duration_seconds": info.get("duration", 0) or 0,
        "artist": artist_name,
        "song_title": track_name,
    }


def search_piano_covers(song_title: str, artist: str = "", max_results: int = 8) -> list[dict]:
    """曲タイトルとアーティスト名でYouTubeから「piano cover」を検索し、関連性でフィルタリング"""
    clean_song = _clean_title(song_title)
    query_parts = []
    if artist:
        query_parts.append(artist)
    query_parts.append(clean_song)
    query_parts.append("piano cover")
    query = f"ytsearch{max_results}:{' '.join(query_parts)}"

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
            cover_title = info.get("title", "")
            # 関連性チェック: 曲名のキーワードがカバー動画のタイトルに含まれているか
            if not _is_relevant(clean_song, artist, cover_title):
                continue
            covers.append({
                "video_id": vid,
                "title": cover_title,
                "channel": info.get("channel", info.get("uploader", "")),
                "thumbnail": f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg",
                "duration_seconds": info.get("duration", 0) or 0,
                "url": f"https://www.youtube.com/watch?v={vid}",
            })
        except json.JSONDecodeError:
            continue

    return covers[:5]


def _extract_artist_and_song(title: str, channel: str = "") -> tuple[str, str]:
    """動画タイトルからアーティスト名と曲名を分離抽出

    よくあるパターン:
    - "Artist - Song Title"
    - "Artist「Song Title」"
    - "Artist / Song Title"
    - "Song Title / Artist"  (判定しにくいのでチャンネル名で補助)
    """
    cleaned = title
    # ノイズ除去（MV, Official Video等）
    noise = [
        r"【.*?】", r"\[.*?\]", r"\(.*?\)",
        r"Official\s*(Music\s*)?Video", r"Official\s*MV",
        r"\bMV\b", r"\bPV\b",
        r"Full\s*Ver\.?", r"Short\s*Ver\.?",
        r"Lyric\s*Video", r"\bAudio\b",
    ]
    for pat in noise:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # パターン1: 「」で囲まれた曲名
    m = re.search(r"(.+?)\s*[「『](.+?)[」』]", cleaned)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # パターン2: " - " で区切り（最も一般的）
    if " - " in cleaned:
        parts = cleaned.split(" - ", 1)
        return parts[0].strip(), parts[1].strip()

    # パターン3: " / " で区切り
    if " / " in cleaned:
        parts = cleaned.split(" / ", 1)
        left, right = parts[0].strip(), parts[1].strip()
        # チャンネル名に近い方がアーティスト
        if channel and _normalize(channel) in _normalize(right):
            return right, left
        return left, right

    # パターン4: feat./ft. を含む場合
    m = re.match(r"(.+?)\s*(?:feat\.|ft\.)\s*(.+)", cleaned, re.IGNORECASE)
    if m:
        # チャンネル名をアーティストとして使う
        return channel or "", cleaned

    # 抽出できない場合はチャンネル名をアーティスト、クリーン済みタイトルを曲名
    return channel or "", cleaned


def _is_relevant(song_title: str, artist: str, cover_title: str) -> bool:
    """カバー動画が元の曲と関連しているかチェック"""
    cover_norm = _normalize(cover_title)

    # 曲名のキーワードを抽出（2文字以上の単語）
    song_keywords = _extract_keywords(song_title)
    if not song_keywords:
        return True  # キーワード抽出できない場合はフィルタしない

    # 曲名キーワードの一致率を計算
    matched = sum(1 for kw in song_keywords if kw in cover_norm)
    song_match_ratio = matched / len(song_keywords)

    # アーティスト名の一致チェック（あれば）
    artist_matched = False
    if artist:
        artist_keywords = _extract_keywords(artist)
        if artist_keywords:
            artist_matched = any(kw in cover_norm for kw in artist_keywords)

    # 判定: 曲名キーワードの半分以上が一致するか、
    # またはアーティスト名が一致 + 曲名キーワード1つ以上一致
    if song_match_ratio >= 0.5:
        return True
    if artist_matched and matched >= 1:
        return True

    return False


def _extract_keywords(text: str) -> list[str]:
    """テキストからキーワードを抽出（正規化済み、2文字以上）"""
    normalized = _normalize(text)
    # アルファベット・数字・日本語の連続を単語として抽出
    words = re.findall(r"[a-z0-9]+|[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]+", normalized)
    # ストップワードを除外
    stop_words = {"the", "a", "an", "of", "in", "on", "at", "to", "for", "and", "or",
                  "is", "it", "my", "no", "by", "de", "piano", "cover", "tutorial",
                  "ver", "version"}
    return [w for w in words if len(w) >= 2 and w not in stop_words]


def _normalize(text: str) -> str:
    """テキストを正規化（小文字化、全角→半角、記号除去）"""
    # NFKC正規化で全角英数字→半角
    text = unicodedata.normalize("NFKC", text)
    text = text.lower()
    # 記号を除去してスペースに
    text = re.sub(r"[^\w\s\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


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
