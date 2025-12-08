# -*- coding: utf-8 -*-
"""
@author: Dr. William N. Roney

Uses the LM to generate a python function using MCP server routines.  Executes by passing in the Library
  wrapped by the MCPWrappers as an object.  

Also creates an AsyncDeque that agentic steps emit (async generator) events to while acting as coroutines for
  results within the agentic workflow function.

Function is loaded as a module and unloaded on completion in order to restrain growth of the memory space.
"""

from .Logging import get_async_logger
logger = get_async_logger(__name__, 'INFO')   

import time
import asyncio
from .AIWrapper import AIWrapper
from .Library import Library
from .WorkflowEvent import WorkflowEventType, WorkflowEvent

class Workflow:
    def __init__(self, agentic_code_generator: AIWrapper, llm: AIWrapper, library: Library, workflow_id: str):
        self.agentic_code_generator = agentic_code_generator
        self.llm = llm
        self.library = library
        self.workflow_id = workflow_id
        self._funcname = f'PACHINKO_AGENTIC_WORKFLOW_{self.workflow_id}'
        self._generator_prompt = f'''First, you are to define a Python function using this template and name:  async def {self._funcname}({self.library.package})
        You shall construct this function using the available library of functions to answer the user's question.
        You may not import any packages within the function either with import or from.  
          Assume 'import asyncio' has already been done outside of the function scope.
          Assume that every module in the library is defined within the parameter object.
            For example, if the library spec includes Module: Umptyfratz, and function named foobar, then you should make function calls fully specified as {self.library.package}.Umptyfratz.foobar(...).

        All functions and methods within the {self.library.package} object are async coroutines, not generators.  When possible, you should run groups of coroutines and gather before proceeding.  Only await individual functions when there is no other option.

        If you cannot figure out a method of answering the user's question using the available library, then call: await {self.library.package}.Sample(<user's question as a quoted string>) which returns a string result.  
            
        Outputs should use await {self.library.package}.Output(<string to output>).  Do not use print().
        
        Wrap the python function in tags so that the final output looks like this:
        [PYTHON BEGINS]
        async def {self._funcname}():
            ...
        [PYTHON ENDS]
        
        Second, you are to define a flowchart of the python function that you created.  This flowchart should be in SVG format and wrapped in tags so that the final output looks like this:
        [FLOWCHART BEGINS]
        <svg>...</svg>
        [FLOWCHART ENDS]

        This flowchart should be structured vertically starting at the top.  The flowchart symbology is as follows:
          The start symbol, a solid black circle, should be in the top center.  This symbol should not have an id assigned.
          Each async function call should be a square with a black outline, and id of "line#" using the line number within the python code (function declaration is line 1), and the line number as text, centered in the middle.
          Each gather call should be a diamond with a black outline, an id of "line#" using the line number within the python code (function declaration is line 1),  and the line number displayed as text, centered in the middle.
          At the end of the flow chart should be a hollow black circle with a double outline, and an id of "line1".
          Each "row" of the flowchart should be centered.
          No shapes should overlap.
          The flowchart should have red lines connecting all shapes to indicate the process flow.  The connection points should start from the bottom center of the source shape and top center of the destination shape.

        Here is the library definition:
        '''

        return
    
    async def generate(self, question: str):
        yield WorkflowEvent(event_type=WorkflowEventType.WORKFLOW_GENERATION_START, workflow_id=self.workflow_id, extra_data=None)
        global __generator_prompt
        start = time.time()
        await self.library.reload()
        await logger.debug(self.library.swagger_docs())
        self.code = ''
        self.image = ''
        system_prompt = self._generator_prompt+self.library.swagger_docs()
        yield WorkflowEvent(event_type=WorkflowEventType.WORKFLOW_GENERATION_PROMPT, workflow_id=self.workflow_id, extra_data=system_prompt)
        llm_response = await self.agentic_code_generator.get_response(system_prompt=system_prompt,
                                                         question=question,
                                                         include_thinking=True)
        self.workplan = llm_response
        await logger.debug(self.workplan)
        try:
            code = self.workplan.answer.split('[PYTHON BEGINS]')[1]
            if code is not None:
                self.code = code.split('[PYTHON ENDS]')[0].lstrip()
            await logger.debug(self.code)
            image = self.workplan.answer.split('[FLOWCHART BEGINS]')[1]
            if image is not None:
                self.image = image.split('[FLOWCHART ENDS]')[0].lstrip()
            await logger.debug(self.code)
            yield WorkflowEvent(event_type=WorkflowEventType.WORKFLOW_CODE, workflow_id=self.workflow_id, extra_data=self.code)
            yield WorkflowEvent(event_type=WorkflowEventType.WORKFLOW_IMAGE, workflow_id=self.workflow_id, extra_data=self.image)
        except Exception as e:
            self.code = None
            await logger.error(f'Failed to create workflow: {type(e)}: {e}.  LLM returned: {llm_response}')
            yield WorkflowEvent(event_type=WorkflowEventType.WORKFLOW_GENERATION_FAILED, workflow_id=self.workflow_id, extra_data=f'Failed to create workflow: {type(e)}: {e}.  LLM returned: {llm_response}')
        finally:
            yield WorkflowEvent(event_type=WorkflowEventType.WORKFLOW_GENERATION_END, workflow_id=self.workflow_id, extra_data=None)
        
    async def process(self):
        start = time.time()
        runner = self.library.mcp_wrapper(self.llm, self.workflow_id)
        await logger.debug('Starting agentic')
        foo = asyncio.ensure_future(runner.exec_agentic_function(self._funcname, self.code))
        await logger.debug('Starting message pump')
        async for event in runner.event_stream:
            yield event
            if event.event_type == WorkflowEventType.WORKFLOW_END:
                await logger.debug('Completion Event Detected, exiting loop')
                break
        await logger.debug('Exited message pump')
        if foo is not None:
            await logger.debug('Final await on foo')
            await foo
        await logger.debug('Process complete')
