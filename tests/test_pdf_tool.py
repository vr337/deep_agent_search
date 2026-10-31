import uuid
from pathlib import Path

from deep_agent_search.api.context import set_session_context
from deep_agent_search.tools.pdf_tool import convert_md_to_pdf

if __name__ == "__main__":
    set_session_context(Path(__file__).parent / "test_session_123" / "sub_dir")
    # 创建测试文件

    print(
        convert_md_to_pdf.invoke(
            {
                "md_filename": "sub_dir/测试文件.md",
                "pdf_filename": f"测试文件_{uuid.uuid4().hex}.md",
            }
        )
    )
