# Cloudflare Pages + Render 免费部署指南

本项目将 React/Vite 前端部署到 Cloudflare Pages，将 FastAPI API 部署到 Render。首次上线无需购买域名：Cloudflare Pages 会提供 `项目名.pages.dev`，Render 会提供 `服务名.onrender.com`。自定义域名可在功能稳定后再绑定。

## 1. 部署 Render API

1. 登录 Render，选择 **New > Blueprint**，连接本 GitHub 仓库并选中 `main` 分支。仓库根目录的 `render.yaml` 会创建免费 Web Service。
2. 等待首次部署完成后，在该服务的 **Settings > Networking** 中生成公网域名，例如 `https://tendon-api.onrender.com`。
3. 打开服务的 **Environment**，将 `CORS_ORIGINS` 设置为下一节生成的 Cloudflare Pages 生产地址，例如 `https://tendon.pages.dev`。暂时未知该地址时可先部署；配置完成后手动重新部署 API。
4. 访问 `https://tendon-api.onrender.com/health`，应返回 `{"status":"ok"}`。

Render 免费服务在 15 分钟没有入站请求后会休眠；下一次 API 调用可能需要约一分钟启动。服务不保存上传文件或工程数据，因此临时文件系统不会影响当前功能。

## 2. 部署 Cloudflare Pages 前端

1. 登录 Cloudflare，进入 **Workers & Pages > Create application > Pages > Connect to Git**，连接同一 GitHub 仓库。
2. 使用以下构建设置：

   | 设置 | 值 |
   | --- | --- |
   | Production branch | `main` |
   | Root directory | `frontend` |
   | Build command | `npm run build` |
   | Build output directory | `dist` |

3. 在 **Settings > Environment variables > Production** 添加 `VITE_API_BASE_URL`，值为第 1 步的 Render API 地址，例如 `https://tendon-api.onrender.com`。不要在末尾添加 `/`。
4. 保存并重新部署。部署成功后会得到 `https://项目名.pages.dev`；将它回填为 Render 的 `CORS_ORIGINS`，然后重新部署 Render API。

`VITE_API_BASE_URL` 是公开的前端配置，只能存放 API 地址，不能存放密钥、口令或令牌。

## 3. 上线验证

1. 打开 Pages 地址，确认单根计算能返回结果。
2. 依次验证 DXF 导入、Excel 批量导入、批量计算和成果导出。
3. 若浏览器出现 CORS 错误，检查 `CORS_ORIGINS` 是否与 Pages 地址完全一致（协议、域名、无末尾 `/`）。

## 4. 访问边界

当前应用没有账号和鉴权。公开 Pages 地址意味着任何访问者均可调用 API 并上传允许类型的文件；请勿将敏感工程资料上传到测试站。若仅面向受邀试用者，应先增加访问保护与上传大小限制。

公测环境的 DXF 与 Excel 单个上传文件上限为 5 MB。前端会在选择文件时提示，后端也会强制拒绝超出上限的请求并返回 HTTP 413。
