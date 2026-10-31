from dataclasses import dataclass
from pathlib import Path

from omegaconf import OmegaConf


@dataclass
class MainAgent:
    system_prompt: str

@dataclass
class Tavily:
    name: str
    description: str
    system_prompt: str

@dataclass
class DB:
    name: str
    description: str
    system_prompt: str

@dataclass
class RagFlow:
    name: str
    description: str
    system_prompt: str

@dataclass
class SubAgent:
    tavily: Tavily
    db: DB
    ragflow: RagFlow

@dataclass
class PromptConfig:
    main_agent: MainAgent
    sub_agents: SubAgent


# 将prompts.yaml配置数据加载成Prompt_config对象

# 加载prompts.yaml文件
_prompt_yaml_path = Path(__file__).parents[3] / "configs" / "prompts.yaml"

# 加载成对象
prompt_config: PromptConfig = OmegaConf.to_object(
    OmegaConf.merge(PromptConfig, OmegaConf.load(_prompt_yaml_path))
)
