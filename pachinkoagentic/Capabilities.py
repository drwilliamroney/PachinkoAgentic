# -*- coding: utf-8 -*-
"""
@author: Dr. William N. Roney

Objects encapsulate/parse the schemas sent by MCP
"""

import re, mcp

class Capability:
    def __init__(self, name: str, description: str):
        self.name = name.strip()
        self.description = description.strip()
    def __str__(self):
        return f'Function: {self.name}\n\tDescription: {self.description}\n'

class Tool(Capability):
    def __init__(self, schema: mcp.types.Tool):
        super().__init__(schema.name, schema.description)
        self.inputs = None
        if schema.inputSchema is not None:
            self.inputs = self._parse_schema(schema.inputSchema)
        self.outputs = None
        if schema.outputSchema is not None:
            self.outputs = self._parse_schema(schema.outputSchema)
        return
    def __str__(self):
        return f'Function: {self.name}\n\tDescription: {self.description}\n\tParameters: {self.inputs}\n\tReturns: {self.outputs}\n'
    def _parse_schema(self, schema: dict) -> dict:
        defs = self._defs_from_schema(schema)
        return self._parameters_from_schema(schema, defs)
    def _parameters_from_schema(self, schema: dict, defs: dict|None) -> dict | None:
        parm_defs = None
        if schema.get('properties') is not None:
            parm_defs = {}
            for prop in schema['properties']:
                if schema["properties"][prop].get("type") is not None:
                    parm_defs[prop] = schema["properties"][prop]["type"]
                elif schema["properties"][prop].get("anyOf") is not None:
                    parm_defs[prop] = ' | '.join([t['type'] for t in schema["properties"][prop]["anyOf"]])
                elif schema["properties"][prop].get("$ref") is not None:
                    parm_defs[prop] = defs.get(schema["properties"][prop]["$ref"].split("/")[-1]) if defs is not None else None
                else:
                    raise ValueError(f'Unknown Schema Property: {prop}: {schema["properties"][prop]}')
        return parm_defs
    def _defs_from_schema(self, schema: dict) -> dict | None:
        schema_defs = None
        if schema.get('$defs') is not None:
            schema_defs = {}
            for dtype in schema['$defs']:
                if schema['$defs'][dtype].get('properties') is not None:
                    schema_defs[dtype] = {}
                    for prop in schema['$defs'][dtype]['properties']:
                        if schema['$defs'][dtype]['properties'][prop].get("type") is not None:
                            schema_defs[dtype][prop] = schema['$defs'][dtype]['properties'][prop]["type"]
                        elif schema['$defs'][dtype]['properties'][prop].get("anyOf") is not None:
                            schema_defs[dtype][prop] = ' | '.join([t['type'] for t in schema['$defs'][dtype]['properties'][prop]["anyOf"]])
                        elif schema['$defs'][dtype]['properties'][prop].get("$ref") is not None:
                            schema_defs[dtype][prop] = schema['$defs'][dtype]['properties'][prop]["$ref"]
                        else:
                            raise ValueError(f'Unknown Datatype Definition: {dtype}: {schema["$defs"][dtype]["properties"]}')
                else:
                    raise ValueError('Sub definitions are not supported at this time.')
        return schema_defs    
class Resource(Capability):
    def __init__(self, schema: mcp.types.Resource | mcp.types.ResourceTemplate):
        super().__init__(schema.name, schema.description)
        self.parms = None
        if isinstance(schema, mcp.types.ResourceTemplate):
            for p in re.finditer(r'{([^/^}]*)}', schema.uriTemplate):
                if self.parms is None:
                    self.parms = {}
                self.parms[p.group(0)[1:-1]] = 'any'
        return
    def __str__(self):
        return f'Function: {self.name}\n\tDescription: {self.description}\n\tParameters: {self.parms if self.parms is not None else ""}\n\tReturns: object\n'

class Prompt(Capability):
    def __init__(self, schema: mcp.types.Prompt):
        super().__init__(schema.name, schema.description)
        return
    
