from pathlib import Path

from deep_agent_search.api.context import set_session_context
from deep_agent_search.tools.upload_file_read_tool import read_file_content

if __name__ == "__main__":
    set_session_context(str(Path(__file__).parent / "test_session_123" / "sub_dir"))

    md_path = "sub_dir/测试文件.md"
    pdf_path = "sub_dir/测试文件.pdf"
    doc_path = "sub_dir/测试文件.docx"
    excel_path = "sub_dir/测试文件.xlsx"

    result = read_file_content.invoke({"filename": excel_path})
    print("===== 读取到文件结果 =====")
    print(result)
