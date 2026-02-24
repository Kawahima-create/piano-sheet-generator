"use client";

import { useState } from "react";
import SheetMusic from "./SheetMusic";
import PDFDownload from "./PDFDownload";
import type { SheetMusicResponse } from "@/lib/api";

type Difficulty = "beginner" | "intermediate" | "advanced";

const LABELS: Record<Difficulty, { label: string; description: string }> = {
  beginner: { label: "初級", description: "シンプルなメロディ + 基本コード" },
  intermediate: {
    label: "中級",
    description: "メロディ + 分散和音パターン",
  },
  advanced: { label: "上級", description: "原曲に忠実なアレンジ" },
};

interface DifficultyTabsProps {
  result: SheetMusicResponse;
}

export default function DifficultyTabs({ result }: DifficultyTabsProps) {
  const [active, setActive] = useState<Difficulty>("beginner");

  const currentAbc = result[active];

  return (
    <div className="w-full max-w-4xl mx-auto">
      {/* キー情報 */}
      <div className="text-center mb-4">
        <span className="inline-block px-3 py-1 bg-violet-100 text-violet-700 rounded-full text-sm font-medium">
          検出キー: {result.key}
        </span>
      </div>

      {/* 難易度タブ */}
      <div className="flex gap-2 justify-center mb-6">
        {(Object.keys(LABELS) as Difficulty[]).map((diff) => (
          <button
            key={diff}
            onClick={() => setActive(diff)}
            className={`px-6 py-3 rounded-xl font-medium transition-all ${
              active === diff
                ? "bg-violet-600 text-white shadow-lg shadow-violet-200"
                : "bg-white text-gray-600 hover:bg-violet-50 border border-gray-200"
            }`}
          >
            <div>{LABELS[diff].label}</div>
            <div
              className={`text-xs mt-0.5 ${
                active === diff ? "text-violet-200" : "text-gray-400"
              }`}
            >
              {LABELS[diff].description}
            </div>
          </button>
        ))}
      </div>

      {/* 楽譜表示 */}
      <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
        <div className="p-2">
          <SheetMusic abcNotation={currentAbc} />
        </div>
      </div>

      {/* ダウンロードボタン */}
      <div className="flex justify-center gap-4 mt-6">
        <PDFDownload difficulty={LABELS[active].label} />
        <button
          onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
          className="px-6 py-3 bg-gray-100 text-gray-600 rounded-xl font-medium hover:bg-gray-200 transition-colors"
        >
          別の曲を変換
        </button>
      </div>
    </div>
  );
}
