"use client";

import { useEffect, useRef } from "react";

interface SheetMusicProps {
  abcNotation: string;
}

export default function SheetMusic({ abcNotation }: SheetMusicProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current || !abcNotation) return;

    // abcjs はクライアントサイドのみ
    import("abcjs").then((abcjs) => {
      abcjs.default.renderAbc(ref.current!, abcNotation, {
        responsive: "resize",
        staffwidth: 800,
        paddingtop: 20,
        paddingbottom: 20,
        add_classes: true,
      });
    });
  }, [abcNotation]);

  return (
    <div
      id="sheet-music-container"
      ref={ref}
      className="bg-white rounded-xl p-6 min-h-[200px] overflow-x-auto"
    />
  );
}
