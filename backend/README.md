# Backend

FastAPI 服务，提供以下能力：

- 暴露人格目录与风格轴
- 接收来信并并发生成多种风格草稿
- 以 `text/event-stream` 方式持续返回生成事件
- 保存专家最终选择和润色结果
- 导入/导出 Excel，支持批量工作流和历史记录导出

## 环境变量

复制 `.env.example` 为 `.env` 后再启动。

如果不配置真实模型 key，系统会自动进入 mock 模式，仍可本地演示完整流程。

### 回复模式

现在后端支持三种回复来源：

- `API`：走你配置的线上模型接口
- `Local`：走本地 Hugging Face 模型目录
- `vLLM`：走独立启动的本地/远程 vLLM 推理服务

推荐按下面两种方式配置：

#### 1. API 模式

```env
MOCK_LLM=false
PLANNER_MODE=api
GENERATOR_MODE=api
GPT_API_KEY=你的 Planner API Key
DOUBAO_API_KEY=你的 Generator API Key
```

#### 2. 本地回复模式

```env
MOCK_LLM=false
PLANNER_MODE=mock
GENERATOR_MODE=local
LOCAL_MODEL_PATH=/absolute/path/to/your/model
LOCAL_DEVICE=auto
LOCAL_DTYPE=auto
```

如果你希望单独给生成回复指定模型，也可以不用 `LOCAL_MODEL_PATH`，改成：

```env
LOCAL_GENERATOR_MODEL_PATH=/absolute/path/to/your/generator-model
```

本地模式会优先使用 `LOCAL_GENERATOR_MODEL_PATH`，没有的话再回退到 `LOCAL_MODEL_PATH`。

#### 3. vLLM 回复模式

```env
MOCK_LLM=false
PLANNER_MODE=api
GENERATOR_MODE=vllm
GPT_API_KEY=你的 Planner API Key
VLLM_BASE_URL=http://127.0.0.1:8001/v1
VLLM_MODEL_NAME=qwen-local
```

如果你想同一输入同时对比 `API` 和 `vLLM`，再加：

```env
COMPARE_MODEL_OUTPUTS=true
DOUBAO_API_KEY=你的 API 模型 Key
```

这样前端在“生成来源模式”切到“对比”时，会同时返回两类结果。

### 安全链路单独模式

安全检测与安全回复现在也支持独立 env 配置，不必完全跟随普通草稿生成主链路。

可选值：

- `SAFETY_MODE=api`
  默认推荐值。安全检测、高风险回复和安全高亮都走真实 API。
- `SAFETY_MODE=mock`
  只测试安全页面切换、历史保存和安全回复工作流，不调用真实模型。
- `SAFETY_MODE=local`
  安全链路强制走本地安全模型分支。

例如，如果你只想测真实安全内容，但普通草稿仍然保持 API 主链路，可以这样配：

```env
MOCK_LLM=false
PLANNER_MODE=api
GENERATOR_MODE=api
SAFETY_MODE=api
GPT_API_KEY=你的 Planner API Key
DOUBAO_API_KEY=你的安全与生成 API Key
```

如果你只想演示安全流程，而不关心真实模型效果，可以这样配：

```env
MOCK_LLM=false
PLANNER_MODE=api
GENERATOR_MODE=api
SAFETY_MODE=mock
GPT_API_KEY=你的 Planner API Key
DOUBAO_API_KEY=你的 Generator API Key
```

### 本地模型依赖

本地模型模式除了 `requirements.txt` 里的依赖外，还需要安装 PyTorch。常见安装方式：

```bash
pip install torch
```

如果你是 CUDA、MPS 或特定平台环境，建议按 PyTorch 官方方式安装对应版本。

### 远程服务器上使用 vLLM

更推荐在远程服务器上把 vLLM 作为独立服务启动，再让 FastAPI 去调用它。

典型前提：

- Linux 服务器
- NVIDIA GPU
- 已安装 CUDA
- 模型目录为 Hugging Face 格式

示例启动：

```bash
CUDA_VISIBLE_DEVICES=0 \
VLLM_USE_FLASHINFER_SAMPLER=0 \
VLLM_ATTENTION_BACKEND=FLASH_ATTN \
python -m vllm.entrypoints.openai.api_server \
  --model /home/mtji/code/letter/generate/sft_models/merge/qwen3-8B-sft-ckpt600 \
  --served-model-name qwen-local \
  --host 127.0.0.1 \
  --port 8006 \
  --gpu-memory-utilization 0.9 \
  --max-model-len 8192
```

如果你是多卡机器，可以再加：

```bash
--tensor-parallel-size 2
```

如果你是单卡 24GB 左右显存，通常建议先从 7B 或 8B instruct 模型开始。

补充说明：

- `VLLM_BASE_URL` 一般写成 `http://127.0.0.1:8001/v1`
- `VLLM_MODEL_NAME` 要和 `--served-model-name` 保持一致
- vLLM 主要适合 NVIDIA CUDA 环境；如果是纯 CPU 或 Apple Silicon，本地 `transformers` 往往更现实

## 启动

```bash
uvicorn app.main:app --reload
```

## 测试

```bash
pytest
```

## Excel 接口

- `POST /api/v1/batch/import`
  上传 `.xlsx`，至少包含 `user_input` 列；风格不从 Excel 读取
- `POST /api/v1/batch/generate/export`
  保留的批量生成导出接口
- `GET /api/v1/batch/records/export`
  导出历史记录 Excel，包含专家批注
- `POST /api/v1/batch/reviewed/export`
  导出专家逐条处理完成后的最终结果 Excel

## 健康检查

启动后可访问：

```bash
curl http://127.0.0.1:8000/api/v1/health
```

返回里会看到：

- `planner_mode`
- `generator_mode`
- `local_generator_configured`

这样你能快速确认当前到底跑的是 API、Local 还是 Mock。
