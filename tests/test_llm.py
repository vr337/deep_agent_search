from deep_agent_search.agents.llm import get_llm_client

if __name__ == "__main__":
    print(get_llm_client().invoke("hello"))
