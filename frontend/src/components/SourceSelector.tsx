"use client";

import type { YouTubeAnalyzeResponse } from "@/lib/api";

interface SourceSelectorProps {
  analysis: YouTubeAnalyzeResponse;
  demucsAvailable: boolean;
  onSelectOriginal: (mode: "direct" | "demucs") => void;
  onBack: () => void;
}

export default function SourceSelector({
  analysis,
  demucsAvailable,
  onSelectOriginal,
  onBack,
}: SourceSelectorProps) {
  const { original } = analysis;

  return (
    <div className="w-full max-w-2xl mx-auto space-y-6">
      {/* 元の動画情報 */}
      <div className="flex items-center gap-4 p-4 bg-gray-50 rounded-xl">
        <img
          src={original.thumbnail}
          alt={original.title}
          className="w-24 h-16 object-cover rounded-lg"
        />
        <div className="flex-1 min-w-0">
          {original.song_title ? (
            <>
              <p className="font-medium text-gray-800 truncate">{original.song_title}</p>
              <p className="text-sm text-gray-500">{original.artist || original.channel}</p>
            </>
          ) : (
            <>
              <p className="font-medium text-gray-800 truncate">{original.title}</p>
              <p className="text-sm text-gray-500">{original.channel}</p>
            </>
          )}
        </div>
        <button
          onClick={onBack}
          className="text-sm text-gray-400 hover:text-gray-600 shrink-0"
        >
          変更
        </button>
      </div>

      {/* ピアノカバーが見つからなかった旨を表示 */}
      <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl">
        <p className="text-sm text-amber-700">
          ピアノカバーが見つかりませんでした。元の動画から直接楽譜を生成できます。
        </p>
      </div>

      {/* 元の動画をそのまま使うセクション */}
      <div>
        <h3 className="text-sm font-semibold text-gray-600 mb-3">
          元の動画を使う
        </h3>
        <div className="space-y-2">
          {demucsAvailable && (
            <button
              onClick={() => onSelectOriginal("demucs")}
              className="w-full p-3 bg-white border border-gray-200 rounded-xl hover:border-violet-400 hover:bg-violet-50/50 transition-all text-left"
            >
              <p className="text-sm font-medium text-gray-700">
                音源分離してから変換
              </p>
              <p className="text-xs text-gray-400">
                AIでピアノパートを抽出してから楽譜化（処理に数分かかります）
              </p>
            </button>
          )}
          <button
            onClick={() => onSelectOriginal("direct")}
            className="w-full p-3 bg-white border border-gray-200 rounded-xl hover:border-gray-300 hover:bg-gray-50 transition-all text-left"
          >
            <p className="text-sm font-medium text-gray-700">
              そのまま変換
            </p>
            <p className="text-xs text-gray-400">
              元の動画の音声をそのまま楽譜化（精度が低い場合があります）
            </p>
          </button>
        </div>
      </div>
    </div>
  );
}
