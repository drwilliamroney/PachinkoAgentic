# -*- coding: utf-8 -*-
"""
@author: Dr. William N. Roney

Objects encapsulate/parse the schemas sent by MCP
"""

from abc import abstractclassmethod

from pickle import NONE
import re, mcp
from fastmcp import Client
from dataclasses import dataclass, make_dataclass, asdict, is_dataclass, field

@dataclass
class Parameter:
    name: str
    datatype: str
    required: bool

@dataclass
class CapBaseStub:
    placeholder: bool = True

class Capability:
    def __init__(self, mcp_server: Client, name: str, description: str):
        self.mcp_server = mcp_server
        self.name = name.strip()
        self.description = description.strip()
        self.set_arguments([])
        self.set_responses([])
        self.output_results = None
    def __str__(self) -> str:
        arguments = asdict(self.arguments) if self.arguments is not None else None
        del arguments['placeholder']
        if arguments == {}:
            arguments = None
        responses = asdict(self.responses) if self.responses is not None else None
        del responses['placeholder']
        if responses == {}:
            responses = None
        return f'Function: {self.name}\n\tDescription: {self.description}\n\tParameters: {arguments}\n\tReturns: {responses}\n'
    @abstractclassmethod
    async def call(cls, **kwargs) -> object:
        ...
    def set_arguments(self, arglist: list) -> None:
        if len(arglist) > 0:
            self.arguments = make_dataclass(f'Inputs', arglist, bases=(CapBaseStub), namespace=f'{self.mcp_server.name}_{self.name}')
        else:
            self.arguments = CapBaseStub()
        return
    def set_responses(self, arglist: list) -> None:
        if len(arglist) > 0:
            self.responses = make_dataclass(f'Outputs', arglist, bases=(CapBaseStub), namespace=f'{self.mcp_server.name}_{self.name}')
        else:
            self.responses = CapBaseStub()
        return

class Tool(Capability):
    def __init__(self, mcp_server: Client, schema: mcp.types.Tool):
        super().__init__(mcp_server, schema.name, schema.description)
        print(f'TOOL: {schema}')
        self.inputs = None
        self.input_schema = None
        self.output_schema = None
        if schema.inputSchema is not None:
            self.input_schema = self._parse_schema(schema.inputSchema)
        self.outputs = None
        if schema.outputSchema is not None:
            self.output_schema = self._parse_schema(schema.outputSchema)
        return
    async def call(self, **kwargs) -> object:
        async with self.mcp_server:
            pass
#            self.mcp_server.call_tool(self.name, **kwargs)
        return
    def _parse_schema(self, schema: dict) -> dict:
        defs = self._defs_from_schema(schema)
        return self._parameters_from_schema(schema, defs)
    def _parameters_from_schema(self, schema: dict, defs: dict|None) -> dict | None:
        parms = None
        if schema.get('properties') is not None:
            parms = {}
            for prop in schema['properties']:
                if schema["properties"][prop].get("type") is not None:
                    parms[prop] = schema["properties"][prop]["type"]
                elif schema["properties"][prop].get("anyOf") is not None:
                    parms[prop] = ' | '.join([t['type'] for t in schema["properties"][prop]["anyOf"]])
                elif schema["properties"][prop].get("$ref") is not None:
                    parms[prop] = defs.get(schema["properties"][prop]["$ref"].split("/")[-1]) if defs is not None else None
                else:
                    raise ValueError(f'Unknown Schema Property: {prop}: {schema["properties"][prop]}')
        return parms
    def _defs_from_schema(self, schema: dict) -> dict | None:
        self.schema_defs = None
        if schema.get('$defs') is not None:
            self.schema_defs = {}
            for dtype in schema['$defs']:
                if schema['$defs'][dtype].get('properties') is not None:
                    self.schema_defs[dtype] = {}
                    for prop in schema['$defs'][dtype]['properties']:
                        if schema['$defs'][dtype]['properties'][prop].get("type") is not None:
                            self.schema_defs[dtype][prop] = schema['$defs'][dtype]['properties'][prop]["type"]
                        elif schema['$defs'][dtype]['properties'][prop].get("anyOf") is not None:
                            self.schema_defs[dtype][prop] = ' | '.join([t['type'] for t in schema['$defs'][dtype]['properties'][prop]["anyOf"]])
                        elif schema['$defs'][dtype]['properties'][prop].get("$ref") is not None:
                            self.schema_defs[dtype][prop] = schema['$defs'][dtype]['properties'][prop]["$ref"]
                        else:
                            raise ValueError(f'Unknown Datatype Definition: {dtype}: {schema["$defs"][dtype]["properties"]}')
                else:
                    raise ValueError('Sub definitions are not supported at this time.')
        return self.schema_defs    
class Resource(Capability):
    def __init__(self, mcp_server: Client, schema: mcp.types.Resource | mcp.types.ResourceTemplate):
        super().__init__(mcp_server, schema.name, schema.description)
        print(f'RESOURCE: {schema}')
        self.parms = None
        self.uriTemplate = getattr(schema, 'uri', None)
        if self.uriTemplate is None:
            self.uriTemplate = getattr(schema, 'uriTemplate')
        print(self.uriTemplate)
        if isinstance(schema, mcp.types.ResourceTemplate):
            for p in re.finditer(r'{([^/^}]*)}', self.uriTemplate):
                if self.parms is None:
                    self.parms = {}
                self.parms[p.group(0)[1:-1]] = 'any'
        return
    async def call(self, **kwargs) -> object:
        async with self.mcp_server:
            pass
#        if self.parms is None:
#            self.mcp_server.read_resource(self.uriTemplate)
        return

class Prompt(Capability):
    def __init__(self, mcp_server: Client, schema: mcp.types.Prompt):
        super().__init__(mcp_server, schema.name, schema.description)
        print(f'PROMPT: {schema}')
        return
    async def call(self, **kwargs) -> object:
        async with self.mcp_server:
#            return self.mcp_server.get_prompt()
            return 'Not implemented.'
    
