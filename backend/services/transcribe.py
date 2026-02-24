"""音声ファイルを音符データ（MIDI）に変換するサービス"""

import tempfile
import os
import pathlib
from basic_pitch.inference import predict
from basic_pitch import ICASSP_2022_MODEL_PATH
import pretty_midi

# ONNXモデルを優先的に使用（TF SavedModelとの互換性問題を回避）
_MODEL_DIR = pathlib.Path(ICASSP_2022_MODEL_PATH).parent
_ONNX_MODEL = _MODEL_DIR / "nmp.onnx"
_MODEL_PATH = str(_ONNX_MODEL) if _ONNX_MODEL.exists() else ICASSP_2022_MODEL_PATH


def transcribe_audio(audio_path: str) -> pretty_midi.PrettyMIDI:
    """
    音声ファイルをMIDIデータに変換する。
    Basic Pitch (Spotify) を使用。

    Args:
        audio_path: 音声ファイルのパス（MP3, WAV）

    Returns:
        PrettyMIDI オブジェクト
    """
    _, midi_data, _ = predict(
        audio_path=audio_path,
        model_or_model_path=_MODEL_PATH,
    )
    return midi_data


def save_midi_to_temp(midi_data: pretty_midi.PrettyMIDI) -> str:
    """MIDIデータを一時ファイルに保存し、パスを返す"""
    fd, path = tempfile.mkstemp(suffix=".mid")
    os.close(fd)
    midi_data.write(path)
    return path
