import json
import os
import uuid

import requests
from dotenv import load_dotenv
from langchain_core.tools import tool
from ragflow_sdk import RAGFlow

from deep_agent_search.api.monitor import monitor
from deep_agent_search.core.logger_utils import logger

load_dotenv(override=True)
# _rag_client = RAGFlow(
#     api_key=os.getenv("RAGFLOW_API_KEY"), base_url=os.getenv("RAGFLOW_API_URL")
# )
RAGFLOW_API_URL = os.getenv("RAGFLOW_API_URL", "").rstrip("/")
RAGFLOW_API_KEY = os.getenv("RAGFLOW_API_KEY", "")
HEADERS = {
    "Authorization": f"Bearer {RAGFLOW_API_KEY}",
    "Content-Type": "application/json"
}


@tool
def get_assistant_list() -> str:
    """
    获取ragflow服务中所有的聊天助手信息! 用于后续具体提问的筛选!

    Returns:
        str:
        返回格式: 助手名称:xxx , 描述: xx , 关联的知识库: x,x,x,x \n
                助手名称:xxx , 描述: xx , 关联的知识库: x,x,x,x \n
    """
    monitor.report_tool("get_assistant_list", {})

    try:
        # 1. 直接发请求获取助手列表
        url = f"{RAGFLOW_API_URL}/api/v1/chats"
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()  # 如果状态码不是 200，抛出 HTTPError
        data = response.json()

        # 2. 提取 chats 列表
        chat_list = data.get("data", {}).get("chats", [])
        if not chat_list:
            return "未找到可用任何助手"

        final_result = ""
        # 3. 遍历并拼接所需信息
        for chat in chat_list:
            name = chat.get("name", "")
            description = chat.get("description", "")
            
            # 根据 RAGFlow 的 JSON 结构，知识库名称在 kb_names 字段里
            kb_names = chat.get("kb_names", [])
            ds_str = ",".join(kb_names) if kb_names else "无"
            
            final_result += f"助手名称:{name}，描述:{description}，关联的知识库:{ds_str}\n"
            
        return final_result
        
    except requests.exceptions.HTTPError as e:
        return f"查询助手列表失败 (HTTP {e.response.status_code}): {e.response.text}"
    except Exception as e:
        return f"查询助手列表失败：{e!s}"

    # SDK的写法由bug
    # try:
    #     # 1.查询所有的聊天助手
    #     chat_list = _rag_client.list_chats()
    #     if not chat_list:
    #         return "未找到可用任何助手"

    #     final_result = ""
    #     # 2.查询每个助手关联的知识库
    #     for chat in chat_list:
    #         # 收集所需的数据
    #         name = chat.name
    #         description = chat.description
    #         kb_names = chat.kb_names
    #         # 拼接
    #         final_result += f"助手名称:{name}，描述:{description}，关联的知识库:{','.join([kb_name for kb_name in kb_names])}\n"
    #     # 3.返回结果
    #     return final_result
    # except Exception as e:
    #     return f"查询助手列表失败：{e!s}"


@tool
def create_ask_delete(chat_name: str, question: str) -> str:
    """
    向指定的助手提问,并获取返回结果!

    Args:
        chat_name (str): 助手的名称,名称需要get_assistant_list查询和确认
        question (str): 本次提问的问题

    Returns:
        str: 提问的回答
    """
    logger.info(f"==========向ragflow提问, chat_name={chat_name}, question={question}")
    monitor.report_tool("create_ask_delete", {"chat_name": chat_name, "question":question})           
    # 使用原始的http的方式

    api_url = os.getenv("RAGFLOW_API_URL", "").rstrip("/")
    api_key = os.getenv("RAGFLOW_API_KEY", "")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        # 1. 获取助手 chat_id
        chats_res = requests.get(f"{api_url}/api/v1/chats", headers=headers)
        chats_res.raise_for_status()
        chats = chats_res.json().get("data", {}).get("chats", [])
        target_chat = next((c for c in chats if c.get("name") == chat_name), None)
        if not target_chat:
            return f"未找到名称为{chat_name}的助手"
        chat_id = target_chat["id"]

        # 2. 创建会话
        session_res = requests.post(
            f"{api_url}/api/v1/chats/{chat_id}/sessions",
            headers=headers, json={"name": uuid.uuid4().hex}
        )
        session_res.raise_for_status()
        session_id = session_res.json().get("data", {}).get("id")

        # 3. 使用新的 API 端点进行流式提问
        payload = {
            "chat_id": chat_id,
            "session_id": session_id,
            "question": question,
            "stream": True
        }
        ask_res = requests.post(
            f"{api_url}/api/v1/chat/completions", 
            headers=headers, json=payload, stream=True
        )
        ask_res.raise_for_status()

        # 4. 终极安全解析 SSE 流
        final_result = ""
        for line in ask_res.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith("data:"):
                    data_str = decoded_line[5:].strip()
                    if data_str:
                        try:
                            data_json = json.loads(data_str)
                            
                            # 关键：判断 data_json 是不是字典
                            if isinstance(data_json, dict):
                                data_content = data_json.get("data")
                                
                                # 关键：判断 data 字段是不是字典
                                if isinstance(data_content, dict):
                                    # 尝试提取 answer 或 content
                                    chunk_text = data_content.get("answer") or data_content.get("content")
                                    if chunk_text:
                                        final_result = chunk_text
                        except json.JSONDecodeError:
                            continue
                            
        return final_result if final_result else "未获取到有效回答"

    except requests.exceptions.HTTPError as e:
        return f"向{chat_name}提问失败 (HTTP {e.response.status_code}): {e.response.text}"
    except Exception as e:
        return f"向{chat_name}提问失败：{e!s}"

    # 下面因为sdk的bug，会报'NoneType' object is not subscriptable错，所以不能用
    # 使用sdk的方式
    # todo 注意：ragflow list_chats[chat对象的列表] datasets [知识库信息字典的列表]
    # 向前端发送通知
    # monitor.report_tool(
    #     tool_name="向ragflow提问的工具",
    #     args={"chat_name": chat_name, "question": question},
    # )

    # try:
    #     # 1.查询指定名称的助手
    #     chat_list = _rag_client.list_chats(name=chat_name)
    #     if not chat_list:
    #         return f"未找到名称为{chat_name}的助手"
    #     # 2.获取助手
    #     chat = chat_list[0]
    #     print(chat)
    #     # 3.创建聊天会话
    #     chat_session = chat.create_session(name=uuid.uuid4().hex)
    #     # 4.向助手提问
    #     stream_result = chat_session.ask(question=question, stream=True)

    #     # 5.获取结果
    #     final_result = ""
    #     for chunk in stream_result:
    #         # 遍历的chunk本身就是累加的，所有取最后一个就可以了
    #         final_result = chunk.content

    #     return final_result
    # except Exception as e:
    #     return f"向{chat_name}提问失败：{e!s}"
