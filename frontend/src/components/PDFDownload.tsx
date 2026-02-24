"use client";

import { useCallback } from "react";

interface PDFDownloadProps {
  difficulty: string;
}

export default function PDFDownload({ difficulty }: PDFDownloadProps) {
  const handleDownload = useCallback(async () => {
    const element = document.getElementById("sheet-music-container");
    if (!element) return;

    const html2canvas = (await import("html2canvas")).default;
    const { jsPDF } = await import("jspdf");

    const canvas = await html2canvas(element, {
      scale: 2,
      backgroundColor: "#ffffff",
    });

    const imgData = canvas.toDataURL("image/png");
    const pdf = new jsPDF("p", "mm", "a4");

    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();
    const margin = 10;
    const maxWidth = pageWidth - margin * 2;

    const imgWidth = maxWidth;
    const imgHeight = (canvas.height * imgWidth) / canvas.width;

    // タイトル
    pdf.setFontSize(16);
    pdf.text(`Piano Sheet - ${difficulty}`, margin, margin + 5);

    // 楽譜画像
    const yOffset = margin + 12;
    if (imgHeight + yOffset > pageHeight - margin) {
      // ページに収まるようにスケーリング
      const scale = (pageHeight - yOffset - margin) / imgHeight;
      pdf.addImage(
        imgData,
        "PNG",
        margin,
        yOffset,
        imgWidth * scale,
        imgHeight * scale
      );
    } else {
      pdf.addImage(imgData, "PNG", margin, yOffset, imgWidth, imgHeight);
    }

    pdf.save(`piano-sheet-${difficulty}.pdf`);
  }, [difficulty]);

  return (
    <button
      onClick={handleDownload}
      className="px-6 py-3 bg-violet-600 text-white rounded-xl font-medium hover:bg-violet-700 transition-colors shadow-sm flex items-center gap-2"
    >
      <svg
        className="w-5 h-5"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
        />
      </svg>
      PDFダウンロード
    </button>
  );
}
