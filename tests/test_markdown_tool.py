from pathlib import Path

from deep_agent_search.api.context import set_session_context
from deep_agent_search.tools.markdown_tool import generate_markdown

if __name__ == "__main__":
    set_session_context(Path(__file__).parent / "test_session_123" / "sub_dir")

    # ========== 极简测试逻辑（只传path/filename，session_dir已初始化） ==========
    test_content = "# 测试文档\n这是给session_dir配置固定值后的测试内容"
    test_filename = "测试文件2"  # 无.md后缀，测试自动补全
    test_path = ""  # 相对路径

    # 调用生成函数
    result = generate_markdown.invoke(
        {"content": test_content, "filename": test_filename, "path": test_path}
    )

    # 验证结果
    print(f"\n调用结果：{result}")
    if "已成功生成" in result:
        file_path = Path(result.split("'")[1])
        print(f"✅ 验证：文件 {file_path} {'存在' if file_path.exists() else '不存在'}")
