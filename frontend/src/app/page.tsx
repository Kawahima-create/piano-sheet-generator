"use client";

import { useState } from "react";
import UploadForm from "@/components/UploadForm";
import DifficultyTabs from "@/components/DifficultyTabs";
import type { SheetMusicResponse } from "@/lib/api";

export default function Home() {
  const [result, setResult] = useState<SheetMusicResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleResult = (data: SheetMusicResponse) => {
    setResult(data);
    setError(null);
  };

  const handleError = (message: string) => {
    setError(message);
    setResult(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-violet-50 via-white to-fuchsia-50">
      {/* ヘッダー */}
      <header className="pt-12 pb-8 text-center">
        <h1 className="text-4xl font-bold bg-gradient-to-r from-violet-600 to-fuchsia-600 bg-clip-text text-transparent mb-3">
          Piano Sheet Generator
        </h1>
        <p className="text-gray-500 text-lg max-w-md mx-auto">
          曲をアップロードするだけで、ピアノ楽譜を自動生成。
          <br />
          初級・中級・上級の3レベルに対応。
        </p>
      </header>

      <main className="max-w-5xl mx-auto px-4 pb-16">
        {/* エラーメッセージ */}
        {error && (
          <div className="max-w-2xl mx-auto mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-600 text-center">
            {error}
          </div>
        )}

        {/* アップロードフォーム（結果がない場合に表示） */}
        {!result && (
          <div className="mt-8">
            <UploadForm onResult={handleResult} onError={handleError} />
          </div>
        )}

        {/* 楽譜結果 */}
        {result && (
          <div className="mt-8">
            <DifficultyTabs result={result} onReset={() => setResult(null)} />
          </div>
        )}
      </main>

      {/* フッター */}
      <footer className="text-center py-8 text-sm text-gray-400 border-t border-gray-100">
        <p>
          Powered by Basic Pitch (Spotify) + music21 + abcjs
        </p>
      </footer>
    </div>
  );
}
