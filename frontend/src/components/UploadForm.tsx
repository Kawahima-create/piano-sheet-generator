"use client";

import { useState, useCallback, useEffect } from "react";
import {
  transcribeUpload,
  transcribeYoutube,
  transcribeEnsemble,
  analyzeYoutube,
  getDemucsStatus,
} from "@/lib/api";
import type {
  SheetMusicResponse,
  YouTubeAnalyzeResponse,
} from "@/lib/api";
import SourceSelector from "./SourceSelector";

interface UploadFormProps {
  onResult: (result: SheetMusicResponse) => void;
  onError: (error: string) => void;
}

export default function UploadForm({ onResult, onError }: UploadFormProps) {
  const [activeTab, setActiveTab] = useState<"file" | "youtube">("file");
  const [isLoading, setIsLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState("");
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [dragOver, setDragOver] = useState(false);

  // YouTube 2ステップフロー用
  const [analysis, setAnalysis] = useState<YouTubeAnalyzeResponse | null>(null);
  const [demucsAvailable, setDemucsAvailable] = useState(false);

  // Demucsの利用可否を確認
  useEffect(() => {
    getDemucsStatus().then((s) => setDemucsAvailable(s.available));
  }, []);

  const handleFile = useCallback(
    async (file: File) => {
      const validTypes = [
        "audio/mpeg",
        "audio/wav",
        "audio/x-wav",
        "audio/mp3",
      ];
      if (!validTypes.includes(file.type) && !file.name.match(/\.(mp3|wav)$/i)) {
        onError("MP3またはWAVファイルをアップロードしてください。");
        return;
      }
      if (file.size > 20 * 1024 * 1024) {
        onError("ファイルサイズは20MB以下にしてください。");
        return;
      }

      setIsLoading(true);
      setLoadingMessage("音声を分析しています...");

      try {
        setTimeout(() => setLoadingMessage("音符を検出しています..."), 5000);
        setTimeout(() => setLoadingMessage("楽譜を生成しています..."), 15000);
        const result = await transcribeUpload(file);
        onResult(result);
      } catch (e) {
        onError(e instanceof Error ? e.message : "エラーが発生しました");
      } finally {
        setIsLoading(false);
        setLoadingMessage("");
      }
    },
    [onResult, onError]
  );

  // Step 1: YouTube URLを分析 → カバーがあれば自動でアンサンブル転写
  const handleAnalyze = useCallback(async () => {
    if (!youtubeUrl.trim()) {
      onError("YouTube URLを入力してください。");
      return;
    }

    setIsLoading(true);
    setLoadingMessage("動画を分析しています...");

    try {
      const result = await analyzeYoutube(youtubeUrl.trim());
      setAnalysis(result);

      // カバーが見つかった場合は自動的にアンサンブル転写を開始
      if (result.piano_covers.length >= 1) {
        const urls = result.piano_covers.map((c) => c.url);
        const songTitle = result.original.song_title || "";
        const artist = result.original.artist || "";
        const count = result.piano_covers.length;

        setLoadingMessage(`${count}件のカバーをダウンロード中... (1/${count})`);

        let step = 1;
        const interval = setInterval(() => {
          step++;
          if (step <= count) {
            setLoadingMessage(`${count}件のカバーをダウンロード中... (${step}/${count})`);
          } else {
            setLoadingMessage("全カバーの音符を照合・統合しています...");
          }
        }, 30000);

        const ensembleResult = await transcribeEnsemble(urls, songTitle, artist);
        clearInterval(interval);
        onResult(ensembleResult);
        return;
      }
      // カバーが見つからなかった場合はSourceSelectorを表示
    } catch (e) {
      setAnalysis(null);
      onError(e instanceof Error ? e.message : "分析に失敗しました");
    } finally {
      setIsLoading(false);
      setLoadingMessage("");
    }
  }, [youtubeUrl, onError, onResult]);

  // Step 2: 元の動画を使って変換
  const handleSelectOriginal = useCallback(
    async (mode: "direct" | "demucs") => {
      setIsLoading(true);
      setLoadingMessage(
        mode === "demucs"
          ? "音源分離を実行中..."
          : "YouTube から音声をダウンロード中..."
      );

      try {
        setTimeout(() => setLoadingMessage("音声を分析しています..."), 10000);
        setTimeout(() => setLoadingMessage("音符を検出しています..."), 20000);
        setTimeout(() => setLoadingMessage("楽譜を生成しています..."), 30000);
        const songTitle = analysis?.original.song_title || "";
        const artist = analysis?.original.artist || "";
        const result = await transcribeYoutube(youtubeUrl.trim(), mode, songTitle, artist);
        onResult(result);
      } catch (e) {
        onError(e instanceof Error ? e.message : "エラーが発生しました");
      } finally {
        setIsLoading(false);
        setLoadingMessage("");
      }
    },
    [youtubeUrl, analysis, onResult, onError]
  );

  const handleBack = useCallback(() => {
    setAnalysis(null);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  // ローディング表示
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-6">
        <div className="relative">
          <div className="w-16 h-16 border-4 border-violet-200 rounded-full animate-spin border-t-violet-600" />
        </div>
        <p className="text-lg text-gray-600 animate-pulse">{loadingMessage}</p>
        <p className="text-sm text-gray-400">
          音声の長さによっては数十秒かかることがあります
        </p>
      </div>
    );
  }

  // YouTube Step 2: ソース選択画面
  if (analysis) {
    return (
      <SourceSelector
        analysis={analysis}
        demucsAvailable={demucsAvailable}
        onSelectOriginal={handleSelectOriginal}
        onBack={handleBack}
      />
    );
  }

  return (
    <div className="w-full max-w-2xl mx-auto">
      {/* タブ切り替え */}
      <div className="flex gap-1 bg-gray-100 rounded-xl p-1 mb-6">
        <button
          onClick={() => setActiveTab("file")}
          className={`flex-1 py-3 px-4 rounded-lg font-medium transition-all ${
            activeTab === "file"
              ? "bg-white text-violet-700 shadow-sm"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          ファイルアップロード
        </button>
        <button
          onClick={() => setActiveTab("youtube")}
          className={`flex-1 py-3 px-4 rounded-lg font-medium transition-all ${
            activeTab === "youtube"
              ? "bg-white text-violet-700 shadow-sm"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          YouTube URL
        </button>
      </div>

      {activeTab === "file" ? (
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-2xl p-12 text-center transition-all cursor-pointer ${
            dragOver
              ? "border-violet-500 bg-violet-50"
              : "border-gray-300 hover:border-violet-400 hover:bg-violet-50/50"
          }`}
          onClick={() => {
            const input = document.createElement("input");
            input.type = "file";
            input.accept = ".mp3,.wav,audio/mpeg,audio/wav";
            input.onchange = (e) => {
              const file = (e.target as HTMLInputElement).files?.[0];
              if (file) handleFile(file);
            };
            input.click();
          }}
        >
          <div className="text-5xl mb-4">🎵</div>
          <p className="text-lg font-medium text-gray-700 mb-2">
            音声ファイルをドラッグ&ドロップ
          </p>
          <p className="text-sm text-gray-400">
            またはクリックしてファイルを選択（MP3 / WAV、最大20MB）
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex gap-3">
            <input
              type="text"
              value={youtubeUrl}
              onChange={(e) => setYoutubeUrl(e.target.value)}
              placeholder="https://www.youtube.com/watch?v=..."
              className="flex-1 px-4 py-3 rounded-xl border border-gray-300 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent text-gray-700"
              onKeyDown={(e) => e.key === "Enter" && handleAnalyze()}
            />
            <button
              onClick={handleAnalyze}
              className="px-6 py-3 bg-violet-600 text-white rounded-xl font-medium hover:bg-violet-700 transition-colors shadow-sm"
            >
              分析
            </button>
          </div>
          <p className="text-sm text-gray-400 text-center">
            URLを入力すると、ピアノカバーの候補を自動検索します
          </p>
        </div>
      )}
    </div>
  );
}
