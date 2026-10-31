# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此仓库工作时提供指引。

## 项目概览

Deep Agent Search：基于 `deepagents` 的「深度搜索」智能体服务。主智能体编排 3 个子智能体（数据库 / 互联网 / RAGFlow 知识库），通过 FastAPI + WebSocket 向前端实时推送执行进度，并把生成文件落到会话目录。

- Python 3.12.14，包管理用 `uv`（`uv.lock` 已存在），构建后端 `uv_build`。
- Windows 为主要开发平台（依赖含 `pywin32`），路径处理需兼顾 `\` 与 `/`。
- 前端为独立 Vue 3 + TS 子项目 `frontend/`（未被 git 跟踪）。

## 常用命令

```bash
uv sync                                  # 安装依赖（国内可加清华源）
uv run main.py                           # 启动 API 服务，监听 0.0.0.0:8000

# 测试：当前是 __main__ 脚本风格，不是 pytest
uv run python tests/test_execute_sql_query.py
uv run python tests/test_llm.py

cd frontend && npm run dev               # 前端开发服务器
cd frontend && npm run build             # vue-tsc 类型检查 + vite build
```

MySQL 演示库需自行初始化：`sql/init.sql`（制药公司 `pharma_db`：drugs / 库存 / 销售）。

## 环境变量（`.env`，参考 `.env.example`）

`DASHSCOPE_BASE_URL`、`DASHSCOPE_API_KEY`、`LLM_NAME`、`TAVILY_API_KEY`、`RAGFLOW_API_URL`、`RAGFLOW_API_KEY`、`MYSQL_HOST/PORT/USER/PASSWORD/DATABASE`。

⚠️ **导入即读配置**：`tools/mysql_tools.py` 在模块级执行 `_db_config = get_db_config()`，`load_dotenv(override=True)` 找不到 `.env` 且环境变量缺失时会直接抛 `ValueError: 缺少必填关键项:user,password,database`。由于主智能体、db 子智能体和各测试都会 import 它，缺配置是**导入阶段就炸**，而不是等到调用工具。`agents/llm.py` 同在模块级 `init_chat_model`，但 api_key 为空时导入不报错，到实际请求才失败。新增工具若需外部配置，注意这两种模块级初始化的差别。

## 架构

### 1. 智能体层 `src/deep_agent_search/agents/`

`main_agent.py` 中 `main_agent = create_deep_agent(...)` 是**模块级单例**，服务启动时构建一次，进程内所有会话共用；子智能体同样在各自模块级构建。

- `sub_agents/db_sub_agent.py` → MySQL 工具：`list_sql_tables`、`get_table_data`、`execute_sql_query`
- `sub_agents/internet_sub_agent.py` → Tavily 搜索：`internet_search`
- `sub_agents/rag_sub_agent.py` → RAGFlow：`get_assistant_list`、`create_ask_delete`
- 主智能体自有工具：`generate_markdown`、`convert_md_to_pdf`、`read_file_content`

三个子智能体共用 `get_llm_client()` 返回的同一个模型实例。

### 2. 提示词外置 `configs/prompts.yaml` + `core/prompt_loader.py`

子智能体的 `name`、`description`、`system_prompt` 全部来自 `prompt_config`（OmegaConf 把 yaml merge 到 dataclass `PromptConfig` 上）。**改智能体行为/命名/路由描述时改 yaml，不要改 Python**。新增子智能体必须同时在 `prompt_loader.py` 的 dataclass（`SubAgent` 及其字段类）里加对应结构，否则 yaml 无法解析成对象。

### 3. 会话上下文 `api/context.py`（跨切面核心）

用 `ContextVar` 保存 `thread_id` 与 `session_dir`，供深层工具函数直接读取，避免层层传参。

`run_deep_agent(query, thread_id)` 的固定流程（`main_agent.py`）：
1. `set_thread_context` / `set_session_context` → 建目录 `data/output/session_{thread_id}`
2. 把 `data/upload/session_{thread_id}/*` **复制**进会话目录（不是移动），并生成「已上传文件」提示
3. 拼出 `【工作环境指令】`（工作目录、禁用绝对路径、读上传文件只传文件名等）**追加进 HumanMessage**，而不是塞进 system prompt
4. `main_agent.astream(...)` 流式遍历，每个 chunk 经 `_report_agent_process` 推给前端
5. `finally` 中 `reset_session_context` 清理两个 token

`core/path_utils.py:resolve_path()` 是文件类工具的路径地基：清洗虚拟前缀（`/workspace`、`/mnt/data`、`/home/user`）、`upload/` 特殊回落到 CWD、防 `session_x/session_x` 嵌套。**所有涉及文件读写的工具都必须走它**，函数 docstring 里那张表格就是行为契约，改它需要一起改表。

### 4. 实时进度通道 `api/monitor.py`

`monitor` 单例被工具函数和主智能体直接 import 调用（`report_tool` / `report_assistant` / `report_task_result` / `report_session_dir`）。

`_emit` 的三路输出与事件循环处理是本项目最容易踩坑的地方：
- WebSocket 定向推送：`ConnectionManager.loop` 在 `api/lifespan.py` 启动时显式绑定；当前循环 ≠ manager 循环时用 `asyncio.run_coroutine_threadsafe`，相同才 `create_task`（同步线程里调用工具时必须走前者）。
- 脚本模式：检测 `builtins.runtime.stream_writer`，供无服务的运行方式接收同一 payload。
- 兜底：`logger.debug`。

新增进度上报点请复用 `monitor`，不要自己持有 WebSocket。payload 结构统一为 `{"type":"monitor_event","event":...,"message":...,"data":...,"timestamp":...}`。

### 5. API 层 `api/server.py`

- `POST /api/task`：`asyncio.create_task(run_deep_agent(...))` **立即返回**，任务在后台跑，前端靠 WebSocket 看进度——不要在请求里 await 结果。
- `POST /api/upload`（批量，落到 `data/upload/session_{thread_id}`）
- `GET /api/download`、`GET /api/files`：**只能访问 `data/output` 目录**，用 `Path.resolve()` + `is_relative_to` 做越权校验；新增文件类接口要沿用同一校验，不要放宽到项目根。
- `GET /outputs/*`：`data/output` 的静态挂载，前端预览用
- `WS /ws/{thread_id}`：注册进 `ConnectionManager`，收文本回 `pong` 心跳

CORS 目前 `allow_origins=["*"]` 且 `allow_credentials=True`，属开发期配置。

### 6. 数据目录约定

```
data/upload/session_{thread_id}/   前端上传，待复制
data/output/session_{thread_id}/   会话工作区（生成物 + 上传文件副本），对外经 /outputs 暴露
```

## 测试现状与约定

`tests/` 下均为 `if __name__ == "__main__"` 手工脚本，直接调用工具并 `print` 结果，**依赖真实 MySQL / RAGFlow / Tavily / 网络**，没有断言也无法无人值守运行。`tests/test_session_123/` 是文件类工具的固定测试夹具（含中文名 md/pdf/docx/xlsx 与子目录）。

新增测试若要走 CI/批量验证，需先引入 pytest（当前 `pyproject.toml` 无此依赖）并与现有脚本风格区分开；否则沿用脚本风格并注明所需的外部条件。

## 需要注意的实现细节

- 工具一律用 `@tool` 装饰（`langchain_core.tools`），其 docstring 就是给 LLM 的接口说明，写清返回值措辞（LLM 靠它判断成败）。
- `pyproject.toml` 的 `deep-agent-search = "deep_agent_search:main"` 仍指向 `__init__.py` 里的脚手架 `print("Hello...")`，启动服务请用 `main.py`。
- `main_agent.py:_report_agent_process` 只消费 `chunk[value]["messages"][-1]`，并把 `task` 这个工具名特殊识别为「子智能体调用」；LLM 输出结构变动时这里会静默丢信息。
- `_report_agent_process` 中 `key == "tools"` 的分支目前被注释掉，工具返回值不推前端。
- `api/context.py` 顶部 `from google.auth import default` 与 `from concurrent.futures import thread` 为无用导入（`google-auth` 也非声明依赖），碰到时可提议清理。
- 主智能体执行失败会 `raise`，但任务由 `create_task` 托管，异常只落到日志，前端只收到 `error` 事件。
