"""Demucs音声分離サービス（オプション）"""

import importlib
import os
import shutil
import subprocess
import sys
import tempfile

DEMUCS_MODEL = "htdemucs"


def is_demucs_available() -> bool:
    """Demucsがインストールされているか確認"""
    try:
        importlib.import_module("demucs")
        return True
    except ImportError:
        return False


def separate_audio(audio_path: str, stem: str = "other") -> str:
    """
    Demucsで音声を分離し、指定ステムのファイルパスを返す。

    Args:
        audio_path: 入力音声ファイルのパス
        stem: "other" = ボーカル以外（ピアノ・ギター・シンセ等）

    Returns:
        分離されたステムのWAVファイルパス
    """
    if not is_demucs_available():
        raise RuntimeError("Demucsがインストールされていません。")

    tmpdir = tempfile.mkdtemp(prefix="demucs_")

    cmd = [
        sys.executable, "-m", "demucs",
        "--two-stems", "vocals",
        "-n", DEMUCS_MODEL,
        "-o", tmpdir,
        audio_path,
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300,
    )

    if result.returncode != 0:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise RuntimeError(f"Demucs分離に失敗: {result.stderr[:500]}")

    input_name = os.path.splitext(os.path.basename(audio_path))[0]
    stem_path = os.path.join(tmpdir, DEMUCS_MODEL, input_name, "no_vocals.wav")

    if not os.path.exists(stem_path):
        # フォールバック: 出力ディレクトリ内のwavファイルを探す
        output_dir = os.path.join(tmpdir, DEMUCS_MODEL, input_name)
        if os.path.isdir(output_dir):
            for name in ["no_vocals.wav", "other.wav"]:
                candidate = os.path.join(output_dir, name)
                if os.path.exists(candidate):
                    stem_path = candidate
                    break

    if not os.path.exists(stem_path):
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise RuntimeError("分離されたステムファイルが見つかりません")

    return stem_path
