const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface SheetMusicResponse {
  beginner: string;
  intermediate: string;
  advanced: string;
  key: string;
}

export interface VideoMetadata {
  video_id: string;
  title: string;
  channel: string;
  thumbnail: string;
  duration_seconds: number;
}

export interface VideoCoverCandidate extends VideoMetadata {
  url: string;
}

export interface YouTubeAnalyzeResponse {
  original: VideoMetadata;
  piano_covers: VideoCoverCandidate[];
}

export interface DemucsStatusResponse {
  available: boolean;
  model_name: string;
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
  url: string,
  mode: "direct" | "demucs" = "direct"
): Promise<SheetMusicResponse> {
  const res = await fetch(`${API_URL}/api/transcribe/youtube`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, mode }),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "不明なエラー" }));
    throw new Error(error.detail || "楽譜の生成に失敗しました");
  }

  return res.json();
}

export async function analyzeYoutube(
  url: string
): Promise<YouTubeAnalyzeResponse> {
  const res = await fetch(`${API_URL}/api/youtube/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "不明なエラー" }));
    throw new Error(error.detail || "動画の分析に失敗しました");
  }

  return res.json();
}

export async function getDemucsStatus(): Promise<DemucsStatusResponse> {
  const res = await fetch(`${API_URL}/api/demucs/status`);

  if (!res.ok) {
    return { available: false, model_name: "htdemucs" };
  }

  return res.json();
}
