/**
 * 统一处理本地开发与已部署环境的后端地址。
 * VITE_API_BASE_URL 在 Cloudflare Pages 构建时注入；未设置时回退到本地 FastAPI。
 */
const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

export const MAX_UPLOAD_BYTES = 5 * 1024 * 1024;
export const MAX_UPLOAD_LABEL = "5 MB";

export function apiUrl(path: string): string {
  return `${apiBaseUrl}${path}`;
}

export function uploadSizeError(file: File): string | null {
  return file.size > MAX_UPLOAD_BYTES ? `上传文件不能超过 ${MAX_UPLOAD_LABEL}` : null;
}
