/**
 * 统一处理本地开发与已部署环境的后端地址。
 * VITE_API_BASE_URL 在 Cloudflare Pages 构建时注入；未设置时回退到本地 FastAPI。
 */
const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

export function apiUrl(path: string): string {
  return `${apiBaseUrl}${path}`;
}
