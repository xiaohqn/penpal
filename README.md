# Mindful Copilot

面向心理咨询/心理支持场景的专家协同工作台 v1。

这个版本聚焦三件事：

- 批量生成多种风格草稿
- 由专家挑选其中一版并按风格继续润色
- 把原始问题、候选草稿、最终润色稿结构化沉淀，为后续 RAG/检索增强做准备

## 目录

- `backend/`: FastAPI 后端，负责人格目录、流式生成、记录保存
- `frontend/`: React + Vite + Tailwind 专家工作台
- `data/`: SQLite 数据库与导出目录

## 架构说明

- 保留现有研究代码中的 `Planner + Generator + PERSONAS + STYLE_AXES_DEF`
- 去掉 `Evaluator / Rewriter` 在线链路，只保留专家主导闭环
- 默认以“内部单专家工作台”运行，不含登录和权限系统
- 默认支持 mock LLM，便于本地无 key 联调
- 现在支持三种回复模式：线上 API、直接本地模型、远程/本地 vLLM 服务
- 工作台支持切换生成来源模式：自动、API、vLLM、对比

## 快速开始

### 1. 启动后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

### 1.1 选择回复模式

API 回复：

```env
MOCK_LLM=false
PLANNER_MODE=api
GENERATOR_MODE=api
GPT_API_KEY=...
DOUBAO_API_KEY=...
```

本地模型回复：

```env
MOCK_LLM=false
PLANNER_MODE=mock
GENERATOR_MODE=local
LOCAL_MODEL_PATH=/absolute/path/to/local-model
LOCAL_DEVICE=auto
LOCAL_DTYPE=auto
```

如果你走本地模式，还需要额外安装 PyTorch：

```bash
pip install torch
```

vLLM 回复：

```env
MOCK_LLM=false
PLANNER_MODE=api
GENERATOR_MODE=vllm
GPT_API_KEY=...
VLLM_BASE_URL=http://127.0.0.1:8001/v1
VLLM_MODEL_NAME=qwen-local
```

如果想同时对比 API 与 vLLM：

```env
COMPARE_MODEL_OUTPUTS=true
DOUBAO_API_KEY=...
```

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev
```

### 2.1 远程服务器部署说明

本地开发时前端依赖 Vite 代理，请求 `/api/...` 会自动转发到本机后端。

但搬到远程服务器后，如果：

- 前端是静态文件部署
- 后端是单独的 FastAPI 服务
- 或者没有把 `/api` 反向代理到后端

前端页面就会请求不到真正的后端，典型现象包括：

- 人格列表为空
- 页面没有生成结果
- 浏览器控制台出现 `404`、`CORS` 或请求发到了错误域名

现在前端已支持显式指定后端地址。构建前这样做：

```bash
cd frontend
VITE_API_BASE_URL=http://你的后端IP或域名:8000 npm run build
```

例如：

```bash
VITE_API_BASE_URL=http://123.123.123.123:8000 npm run build
```

如果你用了同域名反向代理，让 `/api` 直接转发到 FastAPI，则不需要设置 `VITE_API_BASE_URL`。

### 2.2 GitHub 与私有数据

建议 GitHub 只提交代码和示例配置，不提交真实运行数据：

- `backend/.env`：保存模型 key、邀请码、私有路径，只在服务器手动创建。
- `data/*.db`：SQLite 数据库，只在服务器手动复制或新建。
- `data/seed.json`：真实 RAG 种子库，只在服务器手动复制。
- `data/seed.example.json`：可以提交，用来说明种子库格式。

注册已改为邀请制，后端 `.env` 至少需要配置：

```env
VISITOR_INVITE_CODES=用户邀请码1,用户邀请码2
COUNSELOR_INVITE_CODES=咨询师邀请码1
```

如果当前缺少咨询师，可以关闭用户端人工回复能力：

```env
COUNSELOR_FEATURES_ENABLED=false
```

关闭后，用户端不会展示“人工回复”；高风险来信仍会做安全识别和安全回应，但不会自动转人工。

## 核心接口

- `GET /api/v1/personas`
- `POST /api/v1/generations/stream`
- `POST /api/v1/records`
- `GET /api/v1/records`
- `GET /api/v1/records/{id}`
- `POST /api/v1/batch/import`
- `POST /api/v1/batch/generate/export`
- `GET /api/v1/batch/records/export`
- `POST /api/v1/research/events`：追加保存内部研究操作轨迹
- `GET /api/v1/research/events/export?scope=mine|all`：导出研究轨迹 Excel

研究轨迹以事件形式保存，不随最终记录修改而覆盖。当前记录人工编辑、局部批注添加/删除、局部批注重写、Planner 重生成、版本回退和最终提交；文本类事件自动保存操作前后全文及 `diff_json`。

## 数据沉淀

保存记录时会结构化落库以下核心字段：

- `user_input`
- `selected_persona_name`
- `selected_style_config_json`
- `planner_output_json`
- `draft_candidates_json`
- `ai_selected_raw_response`
- `expert_polished_response`
- `expert_annotation`

这些字段既能支撑历史回看，也能直接为后续 few-shot / RAG 提供高质量语料。

## 生成来源模式

工作台顶部现在支持四种生成来源模式：

- `自动`：按后端当前配置自动决定
- `API`：只生成 API 模型回复
- `vLLM`：只生成本地/远程 vLLM 回复
- `对比`：同一输入同时生成 API 与 vLLM 两类回复，便于专家横向比较

对比模式下，同一个人格会出现两份草稿，例如：

- 温暖倾听者 · API 模型
- 温暖倾听者 · 本地 vLLM

## Excel 批量功能

当前支持两类 Excel 工作流：

- 上传 `.xlsx` 批量导入来信列表，至少包含 `user_input` 列
- 导入后不会自动批量生成，而是按顺序逐条进入工作台
- 风格由专家在工作台逐条自由选择
- 专家逐条生成、润色、写批注，全部完成后导出最终结果 Excel
- 历史记录页可导出沉淀记录 Excel，包含专家批注

cloudflared tunnel --url http://127.0.0.1:5173
