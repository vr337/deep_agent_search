from deep_agent_search.tools.ragflow_tools import create_ask_delete, get_assistant_list

if __name__ == "__main__":
    print(get_assistant_list.invoke({}))
    # print(
    #     create_ask_delete.invoke(
    #         {"chat_name": "空调安装助手", "question": "空调的绝热工作怎么做？"}
    #     )
    # )
