from pathlib import Path

from langchain.tools import tool

from deep_agent_search.api.context import get_session_context
from deep_agent_search.api.monitor import monitor
from deep_agent_search.core.logger_utils import logger
from deep_agent_search.core.path_utils import resolve_path


@tool
def generate_markdown(
    content: str,
    filename: str,
    path: str = "",
) -> str:
    """
    根据提供的文本内容，生成对应的Markdown(.md)文件

    Args:
        content (str): 要写入Markdown文档的文本内容
        filename (str): MarkDown文档的文件名（不包含扩展名或包含.md）
        path (str, optional): 文件保存的绝对路径. Defaults to "".

    Returns:
        str: 生成markdown文件成功或失败的反馈
    """

    logger.info(f"路径是{path}")
    # 将调用工具的反馈给前端
    monitor.report_tool("Markdown文档生成工具", {"写入的文本内容": content})

    # 么有后缀.md，补充
    if not filename.endswith(".md"):
        filename += ".md"

    # 获取上下文中的会话目录
    session_dir = get_session_context()

    # ---路径清洗与重定向逻辑---
    if path and path != ".":
        # 绝对路径时
        # 完整的路径
        full_input_path = str(Path(path) / filename)
    else:
        full_input_path = filename

    full_path_str = resolve_path(full_input_path, session_dir)
    file_path = Path(full_path_str)

    # 获取父目录
    parent_dir = file_path.parent

    # 确保目录存在
    logger.debug(
        f"[MarkdownTool] Debug:parent_dir={parent_dir},filename={filename},full_path={file_path}"
    )

    try:
        if not parent_dir.exists():
            parent_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"[MarkdownTool] Created directory:{parent_dir}")

        # 使用path直接写入文本
        file_path.write_text(content, encoding="utf-8")
        logger.debug(f"[MarkdownTool] Successfully wrote to:{file_path}")
        return f"Markdown文件 '{file_path}' 已经=成功生成并保存"
    except Exception as e:
        logger.error(f"[MarkdownTool] Error writing file:{e}")
        return f"生成Markdown文件失败：{e!s}"
