# 项目根目录路径
import asyncio
import shutil
from pathlib import Path
from typing import Annotated, Any

import uvicorn
from fastapi import (
    FastAPI,
    File,
    Form,
    Query,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi import Path as FPath
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from deep_agent_search.agents.main_agent import run_deep_agent
from deep_agent_search.api.lifespan import lifespan
from deep_agent_search.api.monitor import manager
from deep_agent_search.core.logger_utils import logger

_project_root = Path(__file__).resolve().parents[3]


app = FastAPI(title="DeepAgents API", lifespan=lifespan)


# 假设输出目录位于项目根目录/data/output
_output_dir = _project_root / "data" / "output"
_output_dir.mkdir(parents=True, exist_ok=True)

# 挂载输出目录，以便前端生成的静态文件
app.mount("/outputs", StaticFiles(directory=str(_output_dir)), name="outputs")

# 定义上传目录
_upload_dir = _project_root / "data" / "upload"
_upload_dir.mkdir(parents=True, exist_ok=True)

# 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TaskRequest(BaseModel):
    query: Annotated[str, Field(..., description="用户的问题")]
    thread_id: Annotated[str, Field(..., description="会话id")]


@app.post("/api/task", description="任务启动接口")
async def run_task(request: TaskRequest) -> dict[str, Any]:
    """
    智能体任务启动接口（Run Agent Task）

    目标：
    1.接受用户的自然语言指令
    2.在后台异步启动Agent执行逻辑
    3.返回会话ID，供前端通过WebSocket订阅实时进度

    Args:
        request (TaskRequest): 任务请求参数

    Returns:
        dict[str,Any]: 返回启动的状态{"status":"started","thread_id":thread_id}
    """

    # 1.获取当前任务的会话id
    thread_id = request.thread_id
    # 2.后台异步执行Agent，不阻塞主线程
    asyncio.create_task(run_deep_agent(request.query, thread_id))
    # 3.立即响应，任务开始了
    return {"status": "started", "thread_id": thread_id}


@app.post("/api/upload", description="文件上传")
async def upload_files(
    files: Annotated[list[UploadFile], File(..., description="上传文件的对象列表")],
    thread_id: Annotated[str, Form(..., description="上传文件所在会话的会话id")],
) -> dict[str, Any]:
    """
    文件上传（支持批量）

    Returns:
        dict[str, Any]: 上传文件成功后的状态 {"status":"uploaded","files":["file_name1","file_name2"]}
    """

    # 1.上传的目标目录
    target_dir = _upload_dir / f"session_{thread_id}"
    target_dir.mkdir(parents=True, exist_ok=True)

    # 保存成功的文件名称
    saved_files = []

    # 2.保存
    for file in files:
        # 保存后的文件路径
        target_file_path = target_dir / file.filename

        with target_file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        saved_files.append(file.filename)

    # 3.返回成功保存的文件列表
    return {"status": "uploaded", "files": saved_files}


@app.get("/api/download", description="文件下载", response_model=None)
async def download_file(
    path: Annotated[str, Query(..., description="要下载的文件路径")],
) -> dict[str, Any] | FileResponse:
    """
    文件下载

    目标：
    1.根据绝对路径下载文件
    2.严格的安全检查，只能下载output目录下的文件，防止越权访问

    Returns:
        dict[str,Any] | FileResponse: 下载失败的状态/下载成功时的文件流
    """

    # 1.[安全检查]路径解析与越权校验
    try:
        abs_path = Path(path).resolve()
        output_abs = _output_dir.resolve()

        # 请求要下载的文件必须在output目录下
        if not abs_path.is_relative_to(output_abs):
            return {"error": "拒绝访问：只能下载输出目录下的文件"}
    except Exception:
        return {"error": "无效的路径参数"}
    # 2.存在性检查
    if not abs_path.exists():
        return {"error": "文件不存在"}

    # 3.返回文件流（浏览器自动触发下载）
    return FileResponse(abs_path, filename=abs_path.name,media_type="application/octet-stream")


@app.get("/api/files", description="文件列表查询")
async def list_files(
    path: Annotated[
        str, Query(..., description="目标文件的绝对路径(必须在output目录下)")
    ],
) -> dict[str, Any]:
    """
    文件列表查询接口

    目标:
    1.列出指定目录下的所有生成的文件
    2.提供文件元数据（大小、时间、下载链接）
    3.严格的安全检查，防止路径遍历攻击

    Returns:
        dict[str,Any]: 失败的状态信息：{"error":"xxx"} 或文件列表:{"files":files}
    """

    logger.debug(f"请求文件列表：{path}")

    try:
        # 1.解析获取绝对路径对象
        abs_path = Path(path).resolve()
        output_abs = _output_dir.resolve()

        # 2.安全检查路径是否越界
        if not abs_path.is_relative_to(output_abs):
            logger.error(f"拒接访问:{abs_path}不在{output_abs}目录下")
            return {"error": "拒绝访问：只能访问输出的目录下的文件"}
    except Exception as e:
        logger.error(f"路径解析失败：{e}")
        return {"error": f"路径无效：{e}"}

    # 3.检查目录是否存在
    if not abs_path.exists():
        return {"error": "目录不存在"}

    try:
        # 4.遍历递归查找目标目录的所有文件
        files = [
            {
                "name": file_path.name,
                "type": "file",
                "path": str(file_path),
                "url": f"/outputs/{file_path.relative_to(output_abs).as_posix()}",
                "size": file_path.stat().st_size,
                "mtime": file_path.stat().st_mtime,
            }
            for file_path in abs_path.rglob("*")
            if file_path.is_file()
        ]
    except Exception as e:
        logger.error(f"遍历文件失败：{e}")
        return {"error": str(e)}

    # 5.按照修改顺序倒序排序(最新的在前)
    files.sort(key=lambda x: x.get("mtime", 0), reverse=True)
    logger.debug(f"找到了{len(files)}个文件")
    return {"files": files}


# 当浏览器请求 ws://localhost:8000/ws/thread_123 时：
# 1. 路由匹配 ：FastAPI 发现这个 URL 匹配了你写的 @app.websocket("/ws/{thread_id}") 。
# 2. 创建对象 ：FastAPI (基于 Starlette) 会立刻在 主事件循环 中实例化一个 WebSocket 对象。
#    - 这个对象封装了底层的 TCP 连接、HTTP 握手信息、以及后续的消息收发方法 ( send_text , receive_text 等)。
# 3. 注入参数 ：FastAPI 自动把这个刚创建好的 WebSocket 对象，作为参数传给你的 websocket_endpoint(websocket, ...) 函数。


@app.websocket("/ws/{thread_id}")
async def websocket_endpoint(
    websocket: WebSocket, thread_id: Annotated[str, FPath(..., description="会话id")]
) -> None:
    """
    WebSocket 实时通讯核心接口(Real-time communication)

    目标：
    1.建立长连接，实现服务端与前端的双向通行
    2.绑定'thread_id'，实现会话级消息隔离
    3.维持心跳(Keep-Alive),防止连接超时

    Args:
        websocket (WebSocket): Websocket对象(由fast api创建)
        thread_id (Annotated[str,Field, optional): 会话id. Defaults to "会话id")].
    """

    # 1.[注册]建立连接并绑定到管理器
    await manager.connect(websocket, thread_id)
    try:
        # 2.[循环]保持连接活跃
        while True:
            # 3.[监听]接受前端消息(通常时ping心跳)
            data = await websocket.receive_text()
            # 4.[响应]回复pong消息
            await websocket.send_json(
                {"type": "pong", "message": f"服务端已收到：{data}"}
            )
    except WebSocketDisconnect:
        # 5.[清理] 客户端主动断开
        manager.disconnect(websocket, thread_id)
    except Exception as e:
        # 6.[异常] 发生错误时断开
        logger.error(f"[WebSocket]连接异常:{e}")
        manager.disconnect(websocket, thread_id)


def start_server():
    uvicorn.run(
        "deep_agent_search.api.server:app", host="0.0.0.0", port=8000, reload=False
    )
