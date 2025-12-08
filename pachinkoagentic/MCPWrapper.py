# -*- coding: utf-8 -*-
"""
@author: Dr. William N. Roney

Execution wrappers used by the Library to make the MCP calls based upon the generated agentic workflow.
"""

from .Logging import get_async_logger
logger = get_async_logger(__name__, 'INFO')   

import asyncio
import types
import functools
import inspect
import importlib
import sys
from fastmcp import Client
from .WorkflowEvent import WorkflowEventStream, WorkflowEventType, WorkflowEvent
from .AIWrapper import AIWrapper
from .Capabilities import Capability

class MCPFunctionWrapper:
    def __init__(self, mcp_server:Client, funcdef: Capability, sse: WorkflowEventStream):
        self.mcp_server = mcp_server
        self.funcdef = funcdef
        self.sse = sse
        
class MCPServerWrapper:
    def __init__(self, name:str, sse: WorkflowEventStream, mcp_server:Client):
        self.name = name
        self.sse = sse
        self.mcp_server = mcp_server
        self.funcWrappers = {}
        pass
    def add_tool(self, cap: Capability):
        def create_foo(cap: Capability):
            async def function_stub(*args, **kwargs):
                method_name = inspect.currentframe().f_code.co_name
                server_name = self.__class__.__name__
                await logger.error(f'Calling {server_name}.{method_name}({kwargs})')
                return
            function_stub_copy = types.FunctionType(function_stub.__code__.replace(co_name=cap.name), function_stub.__globals__, cap.name,
                                        function_stub.__defaults__, function_stub.__closure__)
            function_stub_copy.__dict__.update(function_stub.__dict__)
            return function_stub_copy
        
        if isinstance(cap, Capability):
            setattr(self.__class__, cap.name, types.MethodType(create_foo(cap), self.__class__))
            self.funcWrappers[cap.name] = MCPFunctionWrapper(self.mcp_server, cap, self.sse)
        else:
            raise ValueError(f'Invalid Capability Type: {type(cap)}')
        return 
    async def DEMO(self):
        await logger.error(f'Inspect=>{inspect.currentframe().f_code.co_name} function from {self.__class__.__name__}')
    
class MCPWrapper:
    def __init__(self, llm: AIWrapper, workflow_id: str):
        self.event_stream = WorkflowEventStream()
        self.llm = llm
        self.funcname=None
        self.workflow_id = workflow_id
        return
    async def Output(self, output_string: str) -> None:
        asyncio.gather(logger.debug(f'OUTPUT CALLED ({output_string})'))
        lineno = inspect.stack()[1].lineno
        await self.send_update(lineno, 'Beginning Output')
        await self.send_answer(lineno, output_string)
        await self.send_update(lineno, 'Returned from Output')
        return
    async def Sample(self, llm_question: str) -> str:
        fname = inspect.stack()[1].function
        lineno = inspect.stack()[1].lineno
        await self.send_update(lineno, 'Beginning LLM Sample')
        asyncio.gather(logger.debug(f'[{fname}:{lineno}] SAMPLE CALLED ({llm_question})'))
        response = await self.llm.get_response(system_prompt='''Respond to this question in HTML format.  Wrap the HTML in tags so that the final response looks like this:
        [STARTANSWER]
        <HTML formatted answer to the question goes here>
        [ENDANSWER]

        The HTML provided between the STARTANSWER and ENDANSWER tags will be inserted into an existing <DIV> block.
        ''',
                                                question=llm_question,
                                                include_thinking=True)
        try:
            answer = response.answer.split('[STARTANSWER]')[1].lstrip().split('[ENDANSWER]')[0]
        except Exception as e:
            await logger.error(response.answer)
            answer = f'LLM was unable to provide an answer to the question [{response.answer}].'
        finally:
            await self.send_update(lineno, 'Received LLM Sample')
            return answer
    async def send_start(self):
        await self.event_stream.put(WorkflowEvent(event_type=WorkflowEventType.WORKFLOW_START, workflow_id=self.workflow_id, extra_data=None))
        return
    async def send_end(self):
        await self.event_stream.put(WorkflowEvent(event_type=WorkflowEventType.WORKFLOW_END, workflow_id=self.workflow_id, extra_data=None))
        return
    async def send_update(self, line: int, update: str):
        await self.event_stream.put(WorkflowEvent(event_type=WorkflowEventType.WORKFLOW_UPDATE, workflow_id=self.workflow_id, extra_data={'line': line, 'update': update}))
        return
    async def send_answer(self, line: int, update: str):
        await self.event_stream.put(WorkflowEvent(event_type=WorkflowEventType.ANSWER_UPDATE, workflow_id=self.workflow_id, extra_data={'line': line, 'update': update}))
        return
    def add_server_functions(self, servername: str, mcp_server: Client, capabilities: list) -> None:
        svr_class = type(servername, (MCPServerWrapper,), {})
        svr_obj = svr_class(servername, self.event_stream, mcp_server)
        setattr(self, servername, svr_obj)
        for cap in capabilities:
            getattr(self, servername).add_tool(cap)
        return
    async def exec_agentic_function(self, funcname: str, code: str):
        await self.send_start()
        self.funcname = funcname
        async def load_as_module(modulename: str, modulecode:str) -> None:
            try:
                await logger.debug(f'Loading Module: {modulename}')
                spec = importlib.util.spec_from_loader(modulename, loader=None)
                module = importlib.util.module_from_spec(spec)
                exec(modulecode, module.__dict__)
                sys.modules[spec.name] = module
            except Exception as e:
                await logger.error(f'{modulename} Loader Exception: {e}')
        async def purge_module(modulename:str) -> None:
            if modulename in sys.modules:
                await logger.debug(f'Purging Module: {modulename}')
                module = sys.modules[modulename]
                del sys.modules[modulename]
                refcount = sys.getrefcount(module)
                del module
                if refcount > 2:
                    await logger.warning(f'{modulename} LIKELY NOT PURGED')
            return

        try:
            if code is not None:
                await load_as_module(funcname, code)
                if funcname in sys.modules:
                    await logger.debug(f'Found module {funcname}')
                    foo = getattr(sys.modules[funcname], funcname)
                    await logger.debug(f'Foo is {foo}')
                    await foo(MCP=self)
                await logger.debug('Done')
        except Exception as e:
            await logger.error(f'Agentic code failed => {type(e)}:{e}')
        finally:
            await purge_module(funcname)
            await self.send_end()
            