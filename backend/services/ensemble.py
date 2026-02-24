"""複数のMIDI転写結果をアンサンブル（投票）で統合するサービス"""

import numpy as np
import pretty_midi


def merge_transcriptions(
    midi_list: list[pretty_midi.PrettyMIDI],
    min_vote_ratio: float = 0.4,
) -> pretty_midi.PrettyMIDI:
    """
    複数のBasic Pitch転写結果をピアノロールベースで統合。
    各転写を時間軸で正規化し、同じ音が複数のカバーに出現するかを投票で判定。

    Args:
        midi_list: 各カバーのPrettyMIDIオブジェクト
        min_vote_ratio: この割合以上のカバーに出現する音を採用（0.0〜1.0）

    Returns:
        統合されたPrettyMIDI
    """
    if not midi_list:
        return pretty_midi.PrettyMIDI()
    if len(midi_list) == 1:
        return midi_list[0]

    fs = 50  # ピアノロールのサンプリングレート（50Hz = 20ms分解能）

    # 各MIDIからピアノロールを取得
    piano_rolls = []
    for midi in midi_list:
        roll = midi.get_piano_roll(fs=fs)  # shape: (128, T)
        if roll.shape[1] > 0:
            piano_rolls.append(roll)

    if not piano_rolls:
        return pretty_midi.PrettyMIDI()

    # 時間軸を正規化（全カバーを同じ長さにリサンプル）
    # テンポの違いを吸収するため、中央値の長さに合わせる
    lengths = [roll.shape[1] for roll in piano_rolls]
    target_len = int(np.median(lengths))

    resampled = []
    for roll in piano_rolls:
        if roll.shape[1] == target_len:
            binary = (roll > 0).astype(np.float32)
        else:
            # 線形リサンプリング
            indices = np.linspace(0, roll.shape[1] - 1, target_len).astype(int)
            binary = (roll[:, indices] > 0).astype(np.float32)
        resampled.append(binary)

    # 投票: 各ピッチ×時間フレームで、何個のカバーが「音あり」と言っているか
    n_sources = len(resampled)
    summed = np.sum(resampled, axis=0)  # shape: (128, target_len)

    # 閾値: 最低2票 or min_vote_ratio のどちらか大きい方
    min_votes = max(2, int(n_sources * min_vote_ratio))
    consensus = (summed >= min_votes).astype(np.float32)

    # コンセンサスのピアノロールをMIDIに変換
    return _piano_roll_to_midi(consensus, fs=fs)


def _piano_roll_to_midi(
    piano_roll: np.ndarray,
    fs: int = 50,
    min_note_duration: float = 0.05,
) -> pretty_midi.PrettyMIDI:
    """
    バイナリのピアノロール (128 x T) → PrettyMIDIオブジェクト

    Args:
        piano_roll: (128, T) のバイナリ配列
        fs: サンプリングレート
        min_note_duration: 最小ノート長（秒）
    """
    midi = pretty_midi.PrettyMIDI(initial_tempo=120.0)
    piano = pretty_midi.Instrument(program=0, name="Piano")

    for pitch in range(128):
        active = False
        start = 0.0
        for t in range(piano_roll.shape[1]):
            time = t / fs
            if piano_roll[pitch, t] > 0 and not active:
                start = time
                active = True
            elif (piano_roll[pitch, t] == 0 or t == piano_roll.shape[1] - 1) and active:
                end = time if piano_roll[pitch, t] == 0 else (t + 1) / fs
                if end - start >= min_note_duration:
                    piano.notes.append(
                        pretty_midi.Note(
                            velocity=80,
                            pitch=pitch,
                            start=start,
                            end=end,
                        )
                    )
                active = False

    piano.notes.sort(key=lambda n: (n.start, n.pitch))
    midi.instruments.append(piano)
    return midi
