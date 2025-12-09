# -*- coding: utf-8 -*-
"""
@author: Dr. William N. Roney

Converts a set of MCP Servers into a library.
"""

from .Logging import get_async_logger
logger = get_async_logger(__name__, 'INFO')   

import asyncio
import sys
import importlib.util
from fastmcp import Client
from typing import Self
from .Capabilities import Tool, Resource, Prompt
from .MCPWrapper import MCPWrapper
from .AIWrapper import AIWrapper

class Library:
    def __init__(self, packagename: str='MCP'):
        self.mcp_servers = []
        self.capabilities = {}
        self.package = packagename
        pass
    def add(self, mcp_server: Client) -> Self:
        self.mcp_servers.append(mcp_server)
        return self
    async def reload(self) -> Self:
        #await self.purge_modules()
        self.capabilities = {}
        coroutines = []
        for mcp_server in self.mcp_servers:
            await logger.debug(f'mcp_server: {type(mcp_server)}: {mcp_server}')
            coroutines.append(asyncio.ensure_future(self.__load_capabilities(mcp_server)))
        await asyncio.gather(*coroutines)
        #await self.load_as_modules()
        return self
    async def __load_capabilities(self, mcp_server: Client):
        try:
            async with mcp_server:
                self.capabilities[mcp_server.initialize_result.serverInfo.name] = {'client': mcp_server, 'instructions': mcp_server.initialize_result.instructions.strip(), 'capabilities': []}
                tools = await mcp_server.list_tools()
                for tool in tools:
                    self.capabilities[mcp_server.initialize_result.serverInfo.name]['capabilities'].append(Tool(tool))
                resources = await mcp_server.list_resources()
                for resource in resources:
                    await logger.debug(f'Parsing: {resource}')
                    self.capabilities[mcp_server.initialize_result.serverInfo.name]['capabilities'].append(Resource(resource))
                resource_templates = await mcp_server.list_resource_templates()
                for resource in resource_templates:
                    await logger.debug(f'Parsing: {resource}')
                    self.capabilities[mcp_server.initialize_result.serverInfo.name]['capabilities'].append(Resource(resource))
                prompts = await mcp_server.list_prompts()
                for prompt in prompts:
                    await logger.debug(f'Parsing: {prompt}')
                    self.capabilities[mcp_server.initialize_result.serverInfo.name]['capabilities'].append(Prompt(prompt))
        except Exception as e:
            await logger.error(f'Error loading capabilities from MCP Server({mcp_server.transport}) => {type(e)}:{e}')
        return
    def swagger_docs(self) -> str:
        swaggerDocs = ''
        swaggerDocs += f'{MCPWrapper.builtins()}\n'
        for lib in self.capabilities:
            swaggerDocs += f'Module: {lib}\nInstructions: {self.capabilities[lib]["instructions"]}\n'
            for capability in self.capabilities[lib]['capabilities']:
                swaggerDocs += f'{capability}\n'
            swaggerDocs += '\n'
        return swaggerDocs
    
    def mcp_wrapper(self, llm: AIWrapper, workflow_id: str) -> MCPWrapper:
        mcpcode = MCPWrapper(llm, workflow_id)
        for lib in self.capabilities:
            mcpcode.add_server_functions(lib, self.capabilities[lib]['client'], self.capabilities[lib]['capabilities'])
        return mcpcode
    
