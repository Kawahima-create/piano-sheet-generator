"use client";

import type { YouTubeAnalyzeResponse, VideoCoverCandidate } from "@/lib/api";

interface SourceSelectorProps {
  analysis: YouTubeAnalyzeResponse;
  demucsAvailable: boolean;
  onSelectCover: (cover: VideoCoverCandidate) => void;
  onSelectOriginal: (mode: "direct" | "demucs") => void;
  onBack: () => void;
}

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export default function SourceSelector({
  analysis,
  demucsAvailable,
  onSelectCover,
  onSelectOriginal,
  onBack,
}: SourceSelectorProps) {
  const { original, piano_covers } = analysis;

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
          <p className="font-medium text-gray-800 truncate">{original.title}</p>
          <p className="text-sm text-gray-500">{original.channel}</p>
        </div>
        <button
          onClick={onBack}
          className="text-sm text-gray-400 hover:text-gray-600 shrink-0"
        >
          変更
        </button>
      </div>

      {/* ピアノカバー候補 */}
      {piano_covers.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-600 mb-3">
            ピアノカバーを使う（推奨）
          </h3>
          <p className="text-xs text-gray-400 mb-3">
            ピアノ単体の音源を使うと、より正確な楽譜が生成されます
          </p>
          <div className="space-y-2">
            {piano_covers.map((cover) => (
              <button
                key={cover.video_id}
                onClick={() => onSelectCover(cover)}
                className="w-full flex items-center gap-3 p-3 bg-white border border-gray-200 rounded-xl hover:border-violet-400 hover:bg-violet-50/50 transition-all text-left group"
              >
                <img
                  src={cover.thumbnail}
                  alt={cover.title}
                  className="w-20 h-14 object-cover rounded-lg"
                />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-700 truncate group-hover:text-violet-700">
                    {cover.title}
                  </p>
                  <p className="text-xs text-gray-400">
                    {cover.channel}
                    {cover.duration_seconds > 0 &&
                      ` · ${formatDuration(cover.duration_seconds)}`}
                  </p>
                </div>
                <span className="text-violet-500 opacity-0 group-hover:opacity-100 transition-opacity text-sm shrink-0">
                  選択 →
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

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
