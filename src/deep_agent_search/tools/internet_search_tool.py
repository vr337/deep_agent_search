import os
from typing import Any, Literal

from dotenv import load_dotenv
from langchain_core.tools import tool
from tavily import TavilyClient

from deep_agent_search.api.monitor import monitor
from deep_agent_search.core.logger_utils import logger

# 加载.env配置
load_dotenv(override=True)
# 创建tavily网络请求的客户端
_tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


# 网络请求的工具
@tool
def internet_search(
    query: str,
    topic: Literal["general", "news", "finance"] = "general",
    max_results: int = 5,
    include_raw_content: bool = False,  # 是否返回详细数据
) -> Any:
    """
    进行网络搜索工具,可以查询数据库或者rag助手中不包含的数据

    Args:
        query (str): 查询内容
        topic (Literal[&quot;general&quot;, &quot;news&quot;, &quot;finance&quot;], optional): 查询类别. Defaults to "general".
        max_results (int, optional): 查询返回的条数. Defaults to 5.
        include_raw_content (bool, optional): 是否精简返回. Defaults to False#是否返回详细数据.

    Returns:
        Any: 查询的返回结果
    """
    # 1. 做好日志记录
    logger.debug(
        f"开始进行{internet_search}工具的调用!查询内容:{query} , 查询数量:{max_results}"
    )

    # 2. 向前端发送通知
    monitor.report_tool(
        tool_name="网络搜索工具",
        args={
            "query": query,
            "topic": topic,
            "max_results": max_results,
            "include_raw_content": include_raw_content,
        },
    )

    # 3. 调用tavily
    return _tavily_client.search(
        query=query,
        topic=topic,
        max_results=max_results,
        include_raw_content=include_raw_content,
    )
