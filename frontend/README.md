# Frontend

React + Vite + Tailwind + TypeScript 专家工作台。

## 功能

- 输入来信并选择多种人格风格
- 流式查看每种风格的草稿生成过程
- 查看 Planner 思路
- 选中某一草稿并继续润色
- 保存为结构化历史记录

## 启动

```bash
npm install
npm run dev
```

开发环境默认请求 `http://127.0.0.1:8000`。

## 远程部署

本地开发时，`/api` 请求依赖 Vite 代理，所以前后端都在本机时可以直接工作。

但如果你把项目部署到远程服务器，前端静态页面和后端 FastAPI 不一定还是同一个来源。这时需要在前端构建前指定后端地址：

```bash
VITE_API_BASE_URL=http://你的后端地址:8000 npm run build
```

例如：

```bash
VITE_API_BASE_URL=http://123.123.123.123:8000 npm run build
```

如果你已经用 Nginx 把同域名下的 `/api` 反向代理到 FastAPI，则这个变量可以不配。
