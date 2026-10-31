import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from deep_agent_search.api.monitor import manager
from deep_agent_search.core.logger_utils import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 服务启动时
    # 获取当前运行的事件循环，并绑定到 WebSocket 管理器。
    # 确保后台线程能通过 run_coroutine_threadsafe 准确投递消息。
    loop = asyncio.get_running_loop()
    manager.set_loop(loop)
    logger.debug(f"[Server] WebSocket Manager bound to loop: {id(loop)}")
    yield
