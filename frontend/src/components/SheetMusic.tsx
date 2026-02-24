"use client";

import { useEffect, useRef, useState } from "react";

interface SheetMusicProps {
  abcNotation: string;
}

export default function SheetMusic({ abcNotation }: SheetMusicProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ref.current || !abcNotation) return;
    setError(null);

    import("abcjs")
      .then((mod) => {
        const abcjs = mod.default ?? mod;
        if (!ref.current) return;
        // コンテナをクリアしてから再描画
        ref.current.innerHTML = "";
        abcjs.renderAbc(ref.current, abcNotation, {
          responsive: "resize",
          staffwidth: 740,
          paddingtop: 15,
          paddingbottom: 15,
          add_classes: true,
          wrap: {
            minSpacing: 1.5,
            maxSpacing: 2.7,
            preferredMeasuresPerLine: 4,
          },
        });
      })
      .catch((err) => {
        console.error("abcjs rendering error:", err);
        setError("楽譜の描画に失敗しました");
      });
  }, [abcNotation]);

  return (
    <div>
      {error && (
        <div className="text-red-500 text-center py-4">{error}</div>
      )}
      <div
        id="sheet-music-container"
        ref={ref}
        className="bg-white rounded-xl p-6 min-h-[200px] overflow-x-auto"
      />
    </div>
  );
}
