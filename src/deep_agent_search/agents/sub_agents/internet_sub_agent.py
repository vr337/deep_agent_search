



from deepagents import SubAgent

from deep_agent_search.agents.llm import get_llm_client
from deep_agent_search.core.prompt_loader import prompt_config
from deep_agent_search.tools.internet_search_tool import internet_search

tavily_config=prompt_config.sub_agents.tavily
internet_sub_agent=SubAgent(
    model=get_llm_client(),
    name=tavily_config.name,
    description=tavily_config.description,
    system_prompt=tavily_config.system_prompt,
    tools=[internet_search]
)