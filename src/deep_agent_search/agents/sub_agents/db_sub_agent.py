


from deepagents import SubAgent

from deep_agent_search.agents.llm import get_llm_client
from deep_agent_search.core.prompt_loader import prompt_config
from deep_agent_search.tools.mysql_tools import (
    execute_sql_query,
    get_table_data,
    list_sql_tables,
)

db_config=prompt_config.sub_agents.db
db_sub_agent=SubAgent(
    model=get_llm_client(),
    name=db_config.name,
    description=db_config.description,
    system_prompt=db_config.system_prompt,
    tools=[list_sql_tables,get_table_data,execute_sql_query]
)
