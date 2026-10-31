from pathlib import Path

import docx
import pandas as pd
from langchain_core.tools import tool

from deep_agent_search.api.context import get_session_context
from deep_agent_search.api.monitor import monitor
from deep_agent_search.core.path_utils import resolve_path

# def read_file_content(filename: str, instruction: str = "提取全部内容") -> str:
#     """
#     读取指定文件的内容。支持 Markdown(.md)、Word(.docx)、PDF(.pdf) 和 Excel(.xlsx/.xls)。
#     对于 Excel 文件，会自动提供数据统计信息（head 和 describe）。

#     Args:
#         filename: 要读取的文件名或路径（支持 .md, .docx, .pdf, .xlsx, .xls）
#         instruction: 对提取内容的具体指令（例如：'提取摘要', '统计数据'）


@tool
def read_file_content(filename: str, instruction: str = "提取全部内容") -> str:
    """
    读取指定文件的内容。支持 Markdown(.md)、Word(.docx)、PDF(.pdf) 和 Excel(.xlsx/.xls)。
    对于 Excel 文件，会自动提供数据统计信息（head 和 describe）。

    Args:
        filename (str): 要读取的文件名或路径（支持 .md, .docx, .pdf, .xlsx, .xls）"]
        instruction (str): 对提取内容的具体指令（例如：'提取摘要', '统计数据'）"] = "提取全部内容

    Returns:
        str: 读取文件内容成功或失败的反馈
    """

    monitor.report_tool(
        "文件内容读取工具", {"filename": filename, "instruction": instruction}
    )

    # 1.Path重构路径解析
    session_dir = get_session_context()
    file_path = Path(resolve_path(filename, session_dir))

    # 检查文件是否存在（替代os.path.exists）
    if not file_path.exists():
        return f"错误：文件 '{filename}'不存在(路径解析：{file_path})"

    # 获取后缀名（替代os.path.splitext,自动转小写）
    ext = file_path.suffix.lower()

    try:
        if ext in [".md", ".txt"]:
            # Path直接读取文本（替代open+os.path）
            return file_path.read_text(encoding="utf-8")
        elif ext == ".docx":
            doc = docx.Document(str(file_path))  # 转字符串传给docx
            full_text = [para.text for para in doc.paragraphs]
            return "\n".join(full_text)
        elif ext in [".xlsx", ".xls"]:
            try:
                df = pd.read_excel(str(file_path))  # 转字符串给pandas
            except Exception as e:
                raise f"读取Excel失败:{e!s}"
            result = [
                f"文件: {filename}",
                f"行数: {len(df)}, 列数: {len(df.columns)}",
                f"列名: {', '.join(df.columns.astype(str))}",
                "\n[前5行数据预览]:",
                df.head().to_string(index=False),
                "\n[统计描述]:",
                df.describe().to_string(),
            ]
            return "\n".join(result)
        else:
            # 尝试作为纯文本读取
            try:
                return file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                return f"错误：不支持的文件格式'{ext}',且无法作为文本读取"
    except Exception as e:
        return f"读取文件出错：{e!s}"
