from pathlib import Path

from langchain.tools import tool

from deep_agent_search.api.context import get_session_context
from deep_agent_search.api.monitor import monitor
from deep_agent_search.core.converter_utils import convert_md_to_pdf_via_word
from deep_agent_search.core.logger_utils import logger
from deep_agent_search.core.path_utils import resolve_path


@tool
def convert_md_to_pdf(md_filename: str, pdf_filename: str | None = None) -> str:
    """
    将Markdown文档转换为PDF（基于Word引擎）
    核心优化：路径与资源管理逻辑分离，只保留Tool层的基础调用

    Args:
        md_filename (str): 要转换的Markdown文档路径（包含.md后缀）
        pdf_filename (str | None, optional): 输出的PDF文件路径（可选，默认与源文件同名）. Defaults to None.

    Returns:
        str: md文件转换pdf文件的成功或失败的反馈
    """
    monitor.report_tool("Markdown转PDF工具")
    try:
        # 1.路径预处理
        session_dir = get_session_context()
        md_path = Path(md_filename).with_suffix(".md")
        md_abs_path = Path(resolve_path(str(md_path), session_dir))

        # 2.检查源文件
        if not md_abs_path.exists():
            return f"错误：文件不存在{md_abs_path}"

        # 3.确定输出路径
        if pdf_filename:
            pdf_path = Path(pdf_filename).with_suffix(".pdf")
            pdf_abs_path = Path(resolve_path(str(pdf_path), session_dir))
        else:
            pdf_abs_path = md_abs_path.with_suffix(".pdf")

        # 4.调用核心转换逻辑
        return convert_md_to_pdf_via_word(md_abs_path, pdf_abs_path)
    except Exception as e:
        logger.error(f"转换失败：{e}",exc_info=True)
        return f"转换失败：{e!s}"


