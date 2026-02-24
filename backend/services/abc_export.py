"""music21のScoreをABC記譜法に変換するサービス"""

import music21
from music21 import note, chord, stream


# music21のピッチ名 → ABC記譜法のマッピング
# ABC記譜法: C D E F G A B = C4-B4, c d e f g a b = C5-B5
_NOTE_MAP = {
    'C': 'C', 'D': 'D', 'E': 'E', 'F': 'F',
    'G': 'G', 'A': 'A', 'B': 'B',
}


def _pitch_to_abc(pitch: music21.pitch.Pitch) -> str:
    """music21のピッチをABC記譜法の文字に変換"""
    name = pitch.name.replace('-', 'b').replace('#', '^')
    # シャープ/フラットの処理
    accidental = ""
    if pitch.accidental:
        if pitch.accidental.name == 'sharp':
            accidental = "^"
        elif pitch.accidental.name == 'flat':
            accidental = "_"
        elif pitch.accidental.name == 'natural':
            accidental = "="

    base_name = pitch.step  # C, D, E, F, G, A, B
    octave = pitch.octave

    if octave <= 3:
        # C3以下: 大文字 + カンマ
        abc_note = accidental + base_name
        commas = 4 - octave
        abc_note += "," * commas
    elif octave == 4:
        # C4: 大文字
        abc_note = accidental + base_name
    elif octave == 5:
        # C5: 小文字
        abc_note = accidental + base_name.lower()
    else:
        # C6以上: 小文字 + アポストロフィ
        abc_note = accidental + base_name.lower()
        primes = octave - 5
        abc_note += "'" * primes

    return abc_note


def _duration_to_abc(quarter_length: float) -> str:
    """四分音符単位のデュレーションをABC記譜法のデュレーションに変換

    ABC記譜法のデフォルト音価 L:1/8 の場合:
    - 全音符 = 8
    - 二分音符 = 4
    - 四分音符 = 2
    - 八分音符 = 1（省略可）
    - 十六分音符 = /2
    """
    # quarter_length を八分音符単位に変換
    eighth_units = quarter_length * 2

    if eighth_units == 1:
        return ""  # デフォルト（八分音符）
    elif eighth_units == int(eighth_units):
        return str(int(eighth_units))
    elif eighth_units == 0.5:
        return "/2"
    elif eighth_units == 0.25:
        return "/4"
    else:
        # 近似値に丸める
        rounded = round(eighth_units)
        return str(max(1, rounded))


def _note_to_abc(n: music21.note.Note) -> str:
    """music21のNoteをABC文字列に変換"""
    return _pitch_to_abc(n.pitch) + _duration_to_abc(n.quarterLength)


def _chord_to_abc(c: music21.chord.Chord) -> str:
    """music21のChordをABC文字列に変換"""
    pitches = sorted(c.pitches, key=lambda p: p.midi)
    notes_str = "".join(_pitch_to_abc(p) for p in pitches)
    return "[" + notes_str + "]" + _duration_to_abc(c.quarterLength)


def _rest_to_abc(r: music21.note.Rest) -> str:
    """music21のRestをABC文字列に変換"""
    return "z" + _duration_to_abc(r.quarterLength)


def score_to_abc(
    score: music21.stream.Score,
    title: str = "Piano Arrangement",
    key_sig: str = "C",
) -> str:
    """
    music21のScoreをABC記譜法の文字列に変換。
    2パート（右手・左手）のピアノ楽譜を想定。
    """
    parts = list(score.parts) if hasattr(score, 'parts') else list(score.getElementsByClass(stream.Part))

    # キー検出
    try:
        detected_key = score.analyze('key')
        key_name = detected_key.tonic.name.replace('-', 'b')
        if detected_key.mode == 'minor':
            key_name += 'm'
    except Exception:
        key_name = key_sig

    # ヘッダー
    abc = f"X:1\n"
    abc += f"T:{title}\n"
    abc += f"M:4/4\n"
    abc += f"L:1/8\n"
    abc += f"Q:1/4=100\n"
    abc += f"K:{key_name}\n"

    if len(parts) >= 2:
        # 2パート（右手・左手）
        abc += "V:1 clef=treble name=\"Right Hand\"\n"
        abc += "V:2 clef=bass name=\"Left Hand\"\n"

        for voice_idx, part in enumerate(parts[:2]):
            abc += f"V:{voice_idx + 1}\n"
            abc += _part_to_abc(part)
            abc += "\n"
    elif len(parts) == 1:
        abc += _part_to_abc(parts[0])
    else:
        # パートがない場合、スコア全体をフラットに
        abc += _stream_to_abc_line(score)

    return abc


def _part_to_abc(part: music21.stream.Part, measures_per_line: int = 4) -> str:
    """パートをABC文字列に変換（数小節ごとに改行）"""
    result = ""
    beat_count = 0.0
    bar_count = 0

    for element in part.flatten().notesAndRests:
        if isinstance(element, note.Note):
            result += _note_to_abc(element) + " "
        elif isinstance(element, chord.Chord):
            result += _chord_to_abc(element) + " "
        elif isinstance(element, note.Rest):
            result += _rest_to_abc(element) + " "

        beat_count += element.quarterLength
        # 4拍で小節線
        if beat_count >= 4.0:
            bar_count += 1
            if bar_count % measures_per_line == 0:
                result += "|\n"
            else:
                result += "| "
            beat_count -= 4.0

    if not result.rstrip().endswith("|"):
        result += "|"

    return result


def _stream_to_abc_line(s, measures_per_line: int = 4) -> str:
    """任意のストリームをABC文字列に変換（数小節ごとに改行）"""
    result = ""
    beat_count = 0.0
    bar_count = 0

    for element in s.flatten().notesAndRests:
        if isinstance(element, note.Note):
            result += _note_to_abc(element) + " "
        elif isinstance(element, chord.Chord):
            result += _chord_to_abc(element) + " "
        elif isinstance(element, note.Rest):
            result += _rest_to_abc(element) + " "

        beat_count += element.quarterLength
        if beat_count >= 4.0:
            bar_count += 1
            if bar_count % measures_per_line == 0:
                result += "|\n"
            else:
                result += "| "
            beat_count -= 4.0

    return result
