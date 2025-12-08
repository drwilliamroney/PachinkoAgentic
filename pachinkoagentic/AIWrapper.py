# -*- coding: utf-8 -*-
"""
@author: Dr. William N. Roney

Because of the various LM protocols, this is a simple wrapped interface.  
This allows functional consistency whether you are going to Ollama, VLLM, or any of the commercial LLMs.
"""

from abc import ABC, abstractclassmethod
from dataclasses import dataclass
from typing import Generator

@dataclass
class AIResponse:
    answer: str
    thought: str
    prompt_token_use: int
    completion_token_use: int
    duration: float
    
class AIWrapper(ABC):
    @abstractclassmethod
    async def get_response(self, system_prompt: str, question:str, include_thinking: bool=False) -> AIResponse:
        ...
    @abstractclassmethod
    async def get_streaming_response(self, system_prompt: str, question:str, include_thinking: bool=False) -> Generator[str, None, None]:
        ...
        