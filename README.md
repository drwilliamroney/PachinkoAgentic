PachinkoAgentic is an agentic workflow package.



Usage:



1.)  Build a class derived from pachinkoagentic.AIWrapper.  This exposes get\_response and get\_streaming\_response methods and handle interactions with an SLM for generating python code.  (see https://github.com/drwilliamroney/PachinkoTestClient/blob/main/localollama.py)

2.)  Instantiate an instance of pachinkoagentic.Library and use .add(fastmcp.Client()) for each MCP server you want to include.

3.)  Create a pachinkoagent.Workflow object passing in a link to an LM for generating code, and another for LLM Samples (per MCP definition, calls from agentic workflow to an LLM for an answer).

4.)  There are 2 async generator calls:

&nbsp;    a.)  workflow.generate(question)

&nbsp;    b.)  workflow.process()



Workflow generate calls the agentic\_code\_generator asking it to construct both a Python function and a SVG flowchart which return on the generator.  See pachinkoagentic.WorkflowEventType.



Workflow process executes the returned python function wrapping any calls to the MCP services.







