"""音符データをピアノ楽譜に編曲するサービス（初級・中級・上級）"""

import music21
from music21 import stream, note, chord, key, meter, clef, instrument


def midi_to_score(midi_path: str) -> tuple[music21.stream.Score, music21.key.Key]:
    """MIDIファイルをmusic21のScoreに変換し、キーを検出"""
    score = music21.converter.parse(midi_path)
    detected_key = score.analyze("key")
    return score, detected_key


def _extract_notes(score: music21.stream.Score) -> list[music21.note.Note]:
    """スコアから全てのノートを抽出"""
    return list(score.flatten().notes)


def _get_chord_for_scale_degree(degree: int, k: music21.key.Key) -> list[int]:
    """スケールの度数に対する基本的な三和音のMIDIピッチを返す"""
    scale_pitches = k.getScale().getPitches()
    root_idx = (degree - 1) % len(scale_pitches)
    root = scale_pitches[root_idx]
    third = scale_pitches[(root_idx + 2) % len(scale_pitches)]
    fifth = scale_pitches[(root_idx + 4) % len(scale_pitches)]
    return [root.midi, third.midi, fifth.midi]


def _simplify_to_beats(notes_list: list, min_duration: float = 1.0):
    """ノートの最小デュレーションを制限してリズムを簡略化"""
    simplified = []
    for n in notes_list:
        if isinstance(n, music21.note.Note):
            new_note = music21.note.Note(n.pitch)
            new_note.quarterLength = max(n.quarterLength, min_duration)
            new_note.offset = n.offset
            simplified.append(new_note)
    return simplified


def arrange_beginner(score: music21.stream.Score, detected_key: music21.key.Key) -> music21.stream.Score:
    """
    初級アレンジ：
    - 右手: 単音メロディ（四分音符以上、1オクターブ範囲）
    - 左手: シンプルな全音符コード
    """
    all_notes = _extract_notes(score)
    if not all_notes:
        return _empty_piano_score()

    # 右手: 最も高いピッチのノートをメロディとして抽出
    right_hand = stream.Part()
    right_hand.insert(0, clef.TrebleClef())
    right_hand.insert(0, instrument.Piano())
    right_hand.insert(0, meter.TimeSignature("4/4"))
    right_hand.insert(0, detected_key)

    # ノートをビート単位でグループ化し、最高音をメロディに
    melody_notes = []
    current_beat = 0.0
    beat_groups = {}
    for n in all_notes:
        beat = round(n.offset * 2) / 2  # 半拍単位でクオンタイズ
        if beat not in beat_groups:
            beat_groups[beat] = []
        beat_groups[beat].append(n)

    for beat in sorted(beat_groups.keys()):
        group = beat_groups[beat]
        highest = max(group, key=lambda x: x.pitch.midi if hasattr(x, 'pitch') else 0)
        if hasattr(highest, 'pitch'):
            new_note = note.Note(highest.pitch.nameWithOctave)
            new_note.quarterLength = max(1.0, highest.quarterLength)
            # C4-C5 の範囲に制限
            while new_note.pitch.midi > 72:  # C5
                new_note.pitch.midi -= 12
            while new_note.pitch.midi < 60:  # C4
                new_note.pitch.midi += 12
            melody_notes.append(new_note)

    for n in melody_notes:
        right_hand.append(n)

    # 左手: 4小節ごとにシンプルなコード
    left_hand = stream.Part()
    left_hand.insert(0, clef.BassClef())
    left_hand.insert(0, instrument.Piano())
    left_hand.insert(0, meter.TimeSignature("4/4"))
    left_hand.insert(0, detected_key)

    total_length = right_hand.highestTime if right_hand.highestTime > 0 else 16.0
    degrees = [1, 4, 5, 1]  # I-IV-V-I の基本進行

    current_offset = 0.0
    degree_idx = 0
    while current_offset < total_length:
        degree = degrees[degree_idx % len(degrees)]
        chord_pitches = _get_chord_for_scale_degree(degree, detected_key)
        # バス音域に移動（C2-C4）
        bass_pitches = []
        for p in chord_pitches:
            pitch_obj = music21.pitch.Pitch(p)
            while pitch_obj.midi > 60:
                pitch_obj.midi -= 12
            while pitch_obj.midi < 36:
                pitch_obj.midi += 12
            bass_pitches.append(pitch_obj)

        c = chord.Chord(bass_pitches)
        c.quarterLength = 4.0  # 全音符
        left_hand.insert(current_offset, c)
        current_offset += 4.0
        degree_idx += 1

    result = stream.Score()
    result.insert(0, right_hand)
    result.insert(0, left_hand)
    return result


def arrange_intermediate(score: music21.stream.Score, detected_key: music21.key.Key) -> music21.stream.Score:
    """
    中級アレンジ：
    - 右手: メロディ（八分音符以上、広い音域）
    - 左手: 分散和音パターン
    """
    all_notes = _extract_notes(score)
    if not all_notes:
        return _empty_piano_score()

    # 右手: メロディ抽出（八分音符OK）
    right_hand = stream.Part()
    right_hand.insert(0, clef.TrebleClef())
    right_hand.insert(0, instrument.Piano())
    right_hand.insert(0, meter.TimeSignature("4/4"))
    right_hand.insert(0, detected_key)

    beat_groups = {}
    for n in all_notes:
        beat = round(n.offset * 4) / 4  # 16分音符単位でクオンタイズ
        if beat not in beat_groups:
            beat_groups[beat] = []
        beat_groups[beat].append(n)

    for beat in sorted(beat_groups.keys()):
        group = beat_groups[beat]
        highest = max(group, key=lambda x: x.pitch.midi if hasattr(x, 'pitch') else 0)
        if hasattr(highest, 'pitch'):
            new_note = note.Note(highest.pitch.nameWithOctave)
            new_note.quarterLength = max(0.5, highest.quarterLength)
            # C3-C6 の範囲に制限
            while new_note.pitch.midi > 84:
                new_note.pitch.midi -= 12
            while new_note.pitch.midi < 48:
                new_note.pitch.midi += 12
            right_hand.append(new_note)

    # 左手: アルベルティ・バス（分散和音）
    left_hand = stream.Part()
    left_hand.insert(0, clef.BassClef())
    left_hand.insert(0, instrument.Piano())
    left_hand.insert(0, meter.TimeSignature("4/4"))
    left_hand.insert(0, detected_key)

    total_length = right_hand.highestTime if right_hand.highestTime > 0 else 16.0
    degrees = [1, 6, 4, 5]  # I-vi-IV-V 進行

    current_offset = 0.0
    degree_idx = 0
    while current_offset < total_length:
        degree = degrees[degree_idx % len(degrees)]
        chord_pitches = _get_chord_for_scale_degree(degree, detected_key)
        bass_pitches = []
        for p in chord_pitches:
            pitch_obj = music21.pitch.Pitch(p)
            while pitch_obj.midi > 55:
                pitch_obj.midi -= 12
            while pitch_obj.midi < 36:
                pitch_obj.midi += 12
            bass_pitches.append(pitch_obj)
        bass_pitches.sort(key=lambda p: p.midi)

        # アルベルティ・バスパターン: 低-高-中-高
        if len(bass_pitches) >= 3:
            pattern = [bass_pitches[0], bass_pitches[2], bass_pitches[1], bass_pitches[2]]
        else:
            pattern = bass_pitches * 2

        for i, p in enumerate(pattern[:4]):
            n = note.Note(p)
            n.quarterLength = 1.0
            left_hand.insert(current_offset + i, n)

        current_offset += 4.0
        degree_idx += 1

    result = stream.Score()
    result.insert(0, right_hand)
    result.insert(0, left_hand)
    return result


def arrange_advanced(score: music21.stream.Score, detected_key: music21.key.Key) -> music21.stream.Score:
    """
    上級アレンジ：
    - 原曲に忠実
    - ピッチで右手・左手に分割
    """
    all_notes = _extract_notes(score)
    if not all_notes:
        return _empty_piano_score()

    right_hand = stream.Part()
    right_hand.insert(0, clef.TrebleClef())
    right_hand.insert(0, instrument.Piano())
    right_hand.insert(0, meter.TimeSignature("4/4"))
    right_hand.insert(0, detected_key)

    left_hand = stream.Part()
    left_hand.insert(0, clef.BassClef())
    left_hand.insert(0, instrument.Piano())
    left_hand.insert(0, meter.TimeSignature("4/4"))
    left_hand.insert(0, detected_key)

    split_point = 60  # C4（真ん中のド）で分割

    for n in all_notes:
        if not hasattr(n, 'pitch'):
            # 和音の場合
            if hasattr(n, 'pitches'):
                high_pitches = [p for p in n.pitches if p.midi >= split_point]
                low_pitches = [p for p in n.pitches if p.midi < split_point]
                if high_pitches:
                    if len(high_pitches) == 1:
                        new_n = note.Note(high_pitches[0])
                    else:
                        new_n = chord.Chord(high_pitches)
                    new_n.quarterLength = n.quarterLength
                    right_hand.insert(n.offset, new_n)
                if low_pitches:
                    if len(low_pitches) == 1:
                        new_n = note.Note(low_pitches[0])
                    else:
                        new_n = chord.Chord(low_pitches)
                    new_n.quarterLength = n.quarterLength
                    left_hand.insert(n.offset, new_n)
            continue

        new_note = note.Note(n.pitch)
        new_note.quarterLength = n.quarterLength
        if n.pitch.midi >= split_point:
            right_hand.insert(n.offset, new_note)
        else:
            left_hand.insert(n.offset, new_note)

    result = stream.Score()
    result.insert(0, right_hand)
    result.insert(0, left_hand)
    return result


def _empty_piano_score() -> music21.stream.Score:
    """空のピアノスコアを返す"""
    right_hand = stream.Part()
    right_hand.insert(0, clef.TrebleClef())
    right_hand.append(note.Rest(quarterLength=4.0))
    left_hand = stream.Part()
    left_hand.insert(0, clef.BassClef())
    left_hand.append(note.Rest(quarterLength=4.0))
    result = stream.Score()
    result.insert(0, right_hand)
    result.insert(0, left_hand)
    return result
