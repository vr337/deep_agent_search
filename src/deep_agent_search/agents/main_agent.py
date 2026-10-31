import shutil
from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from langchain.messages import HumanMessage

from deep_agent_search.agents.llm import get_llm_client
from deep_agent_search.agents.sub_agents.db_sub_agent import db_sub_agent
from deep_agent_search.agents.sub_agents.internet_sub_agent import internet_sub_agent
from deep_agent_search.agents.sub_agents.rag_sub_agent import rag_sub_agent
from deep_agent_search.api.context import (
    reset_session_context,
    set_session_context,
    set_thread_context,
)
from deep_agent_search.api.monitor import monitor
from deep_agent_search.core.logger_utils import logger
from deep_agent_search.core.prompt_loader import prompt_config
from deep_agent_search.tools.markdown_tool import generate_markdown
from deep_agent_search.tools.pdf_tool import convert_md_to_pdf
from deep_agent_search.tools.upload_file_read_tool import read_file_content

main_agent_config = prompt_config.main_agent
main_agent = create_deep_agent(
    model=get_llm_client(),
    system_prompt=main_agent_config.system_prompt,
    subagents=[db_sub_agent, internet_sub_agent, rag_sub_agent],
    tools=[generate_markdown, convert_md_to_pdf, read_file_content],
)


def _report_agent_process(chunk: dict[str, Any]) -> None:
    """
    向前端汇报agent处理的进度

    Args:
        chunk (dict[str,Any]): 流式处理的每个chunk
    """

    for key, value in chunk.items():
        # print(f"=={key}==")
        # print(value)
        if not value or "messages" not in value:
            continue
        message = value["messages"][-1]
        if key == "model":
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    # 区分子智能体和工具
                    if tool_call["name"] == "task":
                        # print( f"--准备调用子智能体{tool_call['args']['subagent_type']}, 参数：{tool_call['args']['description']}")
                        monitor.report_assistant(
                            tool_call["args"]["subagent_type"],
                            tool_call["args"]["description"],
                        )
                    else:
                        # print(f"--智能体准备调用工具{tool_call['name']}, 参数：{tool_call['args']}")
                        monitor.report_tool(tool_call["name"], tool_call["args"])
            elif message.content:
                # print(f"--智能体返回最终结果: {message.content}")
                monitor.report_task_result(message.content)
        # elif key == "tools":
        #     if message.name == "task":
        #         print(f"--调用子智能体返回的结果为：{message.content}")
        #     else:
        #         print(f"--调用工具{message.name}返回的结果为：{message.content}")


async def run_deep_agent(query: str, thread_id: str) -> None:
    # 在调用agent之间，保存thread_id，session_dir_str
    # 保存thread_id
    thread_token = set_thread_context(thread_id)
    # 生成session_dir_str,再保存session_dir_str,并向前端发送session_dir_str
    project_dir = Path(__file__).parents[3].resolve()  # 项目根目录
    session_dir = project_dir / "data" / "output" / f"session_{thread_id}"
    session_dir.mkdir(parents=True, exist_ok=True)  # 确保完整输出目录存在
    session_dir_str = str(session_dir).replace("\\", "/")  # 生成完整路径字符串

    # 保存session_str到上下文
    session_token = set_session_context(session_dir_str)
    # 告诉前端，当前会话的输出目录，浏览器才能再右侧显示会话文件列表
    monitor.report_session_dir(session_dir_str)

    # 将upload目录下拷贝session下
    upload_dir = project_dir / "data" / "upload" / f"session_{thread_id}"
    uploaded_info = ""  # 关于要优先读上传的文件的提示词

    if upload_dir.exists():
        # 得到所有文件的列表
        file_names = [item.name for item in upload_dir.iterdir() if item.is_file()]
        for name in file_names:
            shutil.copy2(upload_dir / name, session_dir / name)
        uploaded_info = (
            (
                "\n    [已上传文件] 已加载到工作目录:\n"
                + "\n".join([f"    - {f}" for f in file_names])
                + "\n    请优先使用工具读取并参考这些文件。"
            )
            if file_names
            else ""
        )

    # 得到工作区目录的相对路径
    relative_session_dir_str = str(session_dir.relative_to(project_dir)).replace(
        "\\", "/"
    )
    path_instruction = f"""
            【工作环境指令】
            工作目录: {relative_session_dir_str}
           
            {uploaded_info}

            规则：
            1. 新生成文件必须保存到工作目录：'{relative_session_dir_str}'
            2. 读取已上传的文件时，请直接将文件名（例如：'开篇.txt'）作为 filename 参数传入（read_file_content）读取工具，不要带上任何目录前缀。
            3. 使用相对路径，禁止使用绝对路径
            4. 若存在上传文件，请先分析内容
            """
    try:
        # 执行agent,遍历过程数据，并特定数据信息发送给前端
        result = main_agent.astream(
            {
                "messages": [
                    HumanMessage(content=f"问题：{query}，补充描述：{path_instruction}")
                ]
            }
        )

        async for chunk in result:
            # 遍历每个chunk，向前端发送当前状态及数据
            _report_agent_process(chunk)

    except Exception as e:
        logger.error(f"智能体执行最终失败：{e}")
        monitor._emit("error", "智能体执行最终失败了")
        raise
    finally:
        # 最终都要重置保存的thread_id和session_id
        reset_session_context(session_token, thread_token)
