"""複数のMIDI転写結果をアンサンブル（投票）で統合するサービス"""

import numpy as np
import pretty_midi


def merge_transcriptions(
    midi_list: list[pretty_midi.PrettyMIDI],
    min_vote_ratio: float = 0.3,
) -> pretty_midi.PrettyMIDI:
    """
    複数のBasic Pitch転写結果をピアノロールベースで統合。
    クロマ特徴量で時間整列し、投票で高精度な楽譜を生成する。

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

    # 最も長いカバーをリファレンスとして使用（最も完全な演奏の可能性が高い）
    ref_idx = max(range(len(piano_rolls)), key=lambda i: piano_rolls[i].shape[1])
    reference = piano_rolls[ref_idx]
    target_len = reference.shape[1]

    # リファレンスのクロマ特徴量を計算
    ref_chroma = _to_chroma(reference)

    # 各カバーをリファレンスに整列
    aligned = []
    for i, roll in enumerate(piano_rolls):
        if i == ref_idx:
            aligned.append((roll > 0).astype(np.float32))
            continue

        aligned_roll = _align_to_reference(ref_chroma, reference, roll, target_len, fs)
        aligned.append(aligned_roll)

    # 投票: 各ピッチ×時間フレームで、何個のカバーが「音あり」と言っているか
    n_sources = len(aligned)
    summed = np.sum(aligned, axis=0)  # shape: (128, target_len)

    # 適応的な投票閾値
    if n_sources <= 2:
        # 2ソース以下: 1票でOK（和集合）
        min_votes = 1
    else:
        # 3ソース以上: 30%以上で最低2票
        min_votes = max(2, int(n_sources * min_vote_ratio))

    consensus = (summed >= min_votes).astype(np.float32)

    return _piano_roll_to_midi(consensus, fs=fs)


def _to_chroma(piano_roll: np.ndarray) -> np.ndarray:
    """ピアノロール (128, T) → クロマ特徴量 (12, T)"""
    chroma = np.zeros((12, piano_roll.shape[1]), dtype=np.float32)
    for pitch in range(128):
        chroma[pitch % 12] += piano_roll[pitch]
    # 正規化
    max_val = chroma.max()
    if max_val > 0:
        chroma /= max_val
    return chroma


def _align_to_reference(
    ref_chroma: np.ndarray,
    reference: np.ndarray,
    other: np.ndarray,
    target_len: int,
    fs: int,
) -> np.ndarray:
    """
    クロマ相互相関でオフセットを検出し、テンポ伸縮でリファレンスに整列する。

    1. クロマ特徴量の相互相関で最適なオフセット（開始位置のずれ）を検出
    2. オフセット適用後、テンポ差を吸収するためにリサンプリング
    """
    other_chroma = _to_chroma(other)

    # --- Step 1: オフセット検出 ---
    # ダウンサンプルして高速化（10フレーム=200msごと）
    hop = 10
    ref_ds = ref_chroma[:, ::hop]  # (12, T_ref/hop)
    other_ds = other_chroma[:, ::hop]  # (12, T_other/hop)

    # 各ピッチクラスの相互相関を合算
    ref_energy = ref_ds.sum(axis=0)  # (T_ref/hop,)
    other_energy = other_ds.sum(axis=0)  # (T_other/hop,)

    # ref_energyの中でother_energyが最もマッチする位置を探す
    corr = np.correlate(ref_energy, other_energy, mode="full")
    best_idx = np.argmax(corr)
    # offset: リファレンスに対するotherの開始位置（フレーム単位）
    offset_ds = best_idx - (len(other_energy) - 1)
    offset = offset_ds * hop

    # --- Step 2: オフセット適用 + テンポリサンプリング ---
    other_binary = (other > 0).astype(np.float32)
    other_len = other.shape[1]

    # otherの有効区間をリファレンスのどの区間に配置するか
    if offset >= 0:
        # otherはリファレンスよりoffsetフレーム遅れて開始
        dst_start = offset
        src_start = 0
    else:
        # otherはリファレンスより先に開始（先頭をカット）
        dst_start = 0
        src_start = -offset

    # リファレンスの対応区間の長さ
    available_dst = target_len - dst_start
    available_src = other_len - src_start

    if available_dst <= 0 or available_src <= 0:
        # 整列不能（完全にはみ出す場合）→ 単純リサンプル
        return _simple_resample(other_binary, target_len)

    # otherの有効部分をリファレンスの対応区間にリサンプリング
    map_len = min(available_dst, target_len - dst_start)
    src_region = other_binary[:, src_start:src_start + available_src]

    if src_region.shape[1] == 0:
        return np.zeros((128, target_len), dtype=np.float32)

    # テンポ差を吸収: src_regionをmap_lenにリサンプル
    if src_region.shape[1] != map_len and map_len > 0:
        indices = np.linspace(0, src_region.shape[1] - 1, map_len).astype(int)
        src_region = src_region[:, indices]

    result = np.zeros((128, target_len), dtype=np.float32)
    copy_len = min(src_region.shape[1], target_len - dst_start)
    result[:, dst_start:dst_start + copy_len] = src_region[:, :copy_len]

    return result


def _simple_resample(binary_roll: np.ndarray, target_len: int) -> np.ndarray:
    """単純な線形リサンプリング（フォールバック用）"""
    if binary_roll.shape[1] == target_len:
        return binary_roll
    indices = np.linspace(0, binary_roll.shape[1] - 1, target_len).astype(int)
    return binary_roll[:, indices]


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
