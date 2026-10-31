from deepagents import SubAgent

from deep_agent_search.agents.llm import get_llm_client
from deep_agent_search.core.prompt_loader import prompt_config
from deep_agent_search.tools.ragflow_tools import create_ask_delete, get_assistant_list

rag_config = prompt_config.sub_agents.ragflow
rag_sub_agent = SubAgent(
    model=get_llm_client(),
    name=rag_config.name,
    description=rag_config.description,
    system_prompt=rag_config.system_prompt,
    tools=[get_assistant_list, create_ask_delete],
)
