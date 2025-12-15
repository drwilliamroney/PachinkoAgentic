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
import time
from fastmcp import Client
from .WorkflowEvent import WorkflowEventStream, WorkflowEventType, WorkflowEvent
from .AIWrapper import AIWrapper
from .Capabilities import Capability

from random import randint

class MCPFunctionWrapper:
    def __init__(self, mcp_server:Client, funcdef: Capability, sse: WorkflowEventStream):
        self.mcp_server = mcp_server
        self.funcdef = funcdef
        self.sse = sse
    async def execute(self, lineno, **kwargs):
        start = time.time()
        await self.sse.send_update(f'Beginning {self.mcp_server.name}.{self.funcdef.name}()', lineno=lineno, hover=self.funcdef.description)
        async with self.mcp_server:
            await logger.info(f'Calling {self.mcp_server.initialize_result.serverInfo.name}.{self.funcdef.name}({kwargs})')
        await asyncio.sleep(randint(1,10))
        await self.sse.send_update(f'Returned from {self.mcp_server.name}.{self.funcdef.name}()', hover=f'(func specific, TBD)\nTime: {time.time()-start:.2f} seconds.', lineno=lineno)
        return
        
class MCPServerWrapper:
    def __init__(self, name:str, sse: WorkflowEventStream, mcp_server:Client):
        self.name = name
        self.sse = sse
        self.mcp_server = mcp_server
        self.funcWrappers = {}
        pass
    def add_tool(self, cap: Capability):
        def create_foo(cap: Capability):
            def function_stub(*args, **kwargs):
                async def foo(*args, **kwargs):
                    retval = None
                    server_name = self.__class__.__name__
                    t = asyncio.current_task()
                    if t is not None:
                        tn = t.get_name()
                        if tn.startswith('Agentic'):
                            methodline = tn.split('-')[1].split(':')
                            method_name = methodline[0]
                            lineno = int(methodline[1])
                            await logger.debug(f'Calling {server_name}.{method_name}({kwargs}): {self.funcWrappers[method_name]}')
                            retval = await self.funcWrappers[method_name].execute(lineno, **kwargs)
                    return retval
                return asyncio.create_task(foo(*args, **kwargs), name=f'Agentic-{inspect.stack()[0].function}:{inspect.stack()[1].lineno}')
            function_stub_copy = types.FunctionType(function_stub.__code__.replace(co_name=cap.name), function_stub.__globals__, cap.name, function_stub.__defaults__, function_stub.__closure__)
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
    builtin_function_names = ['Output', 'Sample', 'Wait']
    def __init__(self, llm: AIWrapper, workflow_id: str):
        self.event_stream = WorkflowEventStream()
        self.llm = llm
        self.funcname=None
        self.workflow_id = workflow_id
        return
    @staticmethod
    def builtins(prefix: str) -> str:
        swagger = "Built in functions:\n"
        for foo in MCPWrapper.builtin_function_names:
            swagger += f'Function: {prefix}.{getattr(MCPWrapper, foo).__name__}\n{getattr(MCPWrapper, foo).__doc__}'
        return swagger
    def add_server_functions(self, servername: str, mcp_server: Client, capabilities: list) -> None:
        svr_class = type(servername, (MCPServerWrapper,), {})
        svr_obj = svr_class(servername, self, mcp_server)
        setattr(self, servername, svr_obj)
        for cap in capabilities:
            getattr(self, servername).add_tool(cap)
        return
    async def is_harmless(self, code:str)->bool:
        is_harmless = True
        # Check for imports
        # check for exec
        return is_harmless
    async def exec_agentic_function(self, funcname: str, code: str):
        await logger.debug(funcname)
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
    async def send_start(self):
        await logger.debug('Sending Start Event')
        await self.event_stream.put(WorkflowEvent(event_type=WorkflowEventType.WORKFLOW_START, workflow_id=self.workflow_id, extra_data=None))
        await logger.debug('Back')
        return
    async def send_end(self):
        await logger.debug('Sending End Event')
        await self.event_stream.put(WorkflowEvent(event_type=WorkflowEventType.WORKFLOW_END, workflow_id=self.workflow_id, extra_data=None))
        await logger.debug('Back')
        return
    async def send_update(self, update: str, hover: str = '', lineno: int = None):
        await logger.debug('Sending Update Event')
        if lineno is None:
            line = inspect.stack()[2].lineno
        else:
            line = lineno
        await logger.debug(f'Lineno: [{line}]')
        await self.event_stream.put(WorkflowEvent(event_type=WorkflowEventType.WORKFLOW_UPDATE, workflow_id=self.workflow_id, extra_data={'line': line, 'update': update, 'hover':hover}))
        await logger.debug('Back')
        return
    async def send_answer(self, update: str, lineno: int = None):
        await logger.debug('Sending Answer Event')
        if lineno is None:
            line = inspect.stack()[2].lineno
        else:
            line = lineno
        await logger.debug(f'Lineno: [{line}]')
        await self.event_stream.put(WorkflowEvent(event_type=WorkflowEventType.ANSWER_UPDATE, workflow_id=self.workflow_id, extra_data={'line': line, 'update': update}))
        await logger.debug('Back')
        return
    async def Wait(self, *args):
        '''Description: This function mimics asyncio.gather.  You should NOT use asyncio.gather, but instead use this function.  When using this function, explicitly assign the coroutines the variables prior to the call and pass variables as parameters.
        Parameters: <coroutines as *args>
        Returns: array of results from the coroutine parameters
        '''
        start = time.time()
        await self.send_update('Beginning Gather', hover="Waiting for this group of requests to return.")
        results = await asyncio.gather(*args)
        await self.send_update('Returned from Gather', hover=f"Time: {time.time()-start:.2f} seconds.")
        return results
    async def Output(self, output_string: str) -> None:
        '''Description: This function sends a result to the user.  It should be used instead of print().
        Parameters: <output_string: str>
        Returns: None
        '''
        await logger.debug(f'Self is {type(self)}')
        await logger.debug(f'OUTPUT CALLED ({output_string})')
        lineno = inspect.stack()[1].lineno
        await self.send_update('Beginning Output', lineno=lineno, hover='This function prints part of the final answer.')
        await self.send_answer(output_string)
        await self.send_update('Returned from Output', lineno=lineno)
        return
    async def Sample(self, llm_question: str) -> str:
        '''Description: This function should be used if you cannot figure out a method of answering the user's question using the available library of functions.
        Parameters: <llm_question: str>
        Returns: str
        '''
        start = time.time()
        await logger.debug(f'Self is {type(self)}')
        lineno = inspect.stack()[1].lineno
        fname = inspect.stack()[1].function
        await self.send_update('Beginning LLM Sample', lineno=lineno, hover='Making a call to the LLM.')
        await logger.debug(f'[{fname}:{lineno}] SAMPLE CALLED ({llm_question})')
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
            await logger.debug(response.answer)
            answer = f'LLM was unable to provide an answer to the question [{response.answer}].'
        finally:
            await self.send_update('Received LLM Sample', lineno=lineno, hover=f'Prompt Tokens:{response.prompt_token_use}\nCompletionTokens:{response.completion_token_use}\nTime: {time.time()-start:.2f} seconds.')
            return answer

            