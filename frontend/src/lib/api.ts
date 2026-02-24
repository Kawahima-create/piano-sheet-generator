const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface SheetMusicResponse {
  beginner: string;
  intermediate: string;
  advanced: string;
  key: string;
}

export async function transcribeUpload(
  file: File
): Promise<SheetMusicResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_URL}/api/transcribe/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "不明なエラー" }));
    throw new Error(error.detail || "楽譜の生成に失敗しました");
  }

  return res.json();
}

export async function transcribeYoutube(
  url: string
): Promise<SheetMusicResponse> {
  const res = await fetch(`${API_URL}/api/transcribe/youtube`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "不明なエラー" }));
    throw new Error(error.detail || "楽譜の生成に失敗しました");
  }

  return res.json();
}
