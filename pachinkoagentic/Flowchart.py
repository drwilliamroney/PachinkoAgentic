# -*- coding: utf-8 -*-
"""
@author: Dr. William N. Roney

This file the flowchart SVG code
"""

from abc import abstractclassmethod
from .Logging import get_async_logger
logger = get_async_logger(__name__, 'INFO')   


from typing import Self, List

class Symbol():
    def __init__(self, lineno: int):
        self.lineno = lineno
        self.connection_point_lower = (None,None)
        self.connection_point_upper = (None,None)
    def set_connection_points(self, center_x, center_y, radius):
        self.connection_point_upper = (center_x, center_y-radius)
        self.connection_point_lower = (center_x, center_y+radius)
        return
    @abstractclassmethod
    def svg(self, center_x: int, center_y:int , radius: int) -> str:
        ...

class Start(Symbol):
    def __init__(self):
        super().__init__(lineno = None)
    def svg(self, center_x: int, center_y:int , radius: int) -> str:
        self.set_connection_points(center_x, center_y, radius)
        return f'<circle cx="{center_x}" cy="{center_y}" r="{radius}" fill="black" />'

class End(Symbol):
    def __init__(self):
        super().__init__(lineno = 1)
    def svg(self, center_x: int, center_y:int , radius: int) -> str:
        self.set_connection_points(center_x, center_y, radius)
        return f'<circle cx="{center_x}" cy="{center_y}" r="{radius}" fill="lightgray" id="line{self.lineno}" stroke="black" stroke-width="2"/><circle cx="{center_x}" cy="{center_y}" r="{radius/2}" fill="black"/>'

class Call(Symbol):
    def __init__(self, lineno):
        super().__init__(lineno)
    def svg(self, center_x: int, center_y:int , radius: int) -> str:
        self.set_connection_points(center_x, center_y, radius)
        return f'<rect x="{center_x-radius}" y="{center_y-radius}" width="{2*radius}" height="{2*radius}" fill="lightgray" id="line{self.lineno}" stroke="black" stroke-width="2"/><text x="{center_x}" y="{center_y}" dominant-baseline="middle" text-anchor="middle">{self.lineno}</text>'

class Junction(Symbol):
    def __init__(self, lineno):
        super().__init__(lineno)
    def svg(self, center_x: int, center_y:int , radius: int) -> str:
        self.set_connection_points(center_x, center_y, radius)
        return f'<polygon points="{center_x},{center_y-radius} {center_x+radius},{center_y} {center_x},{center_y+radius} {center_x-radius},{center_y}" fill="lightgray" id="line{self.lineno}" stroke="black" stroke-width="2"/><text x="{center_x}" y="{center_y}" dominant-baseline="middle" text-anchor="middle">{self.lineno}</text>'

class Flowchart():
    min_width = 100
    min_height = 100
    symbol_radius = 15
    padding = 10
    def __init__(self):
        self.rows = [[Start()],[]]
    def add_row(self) -> None:
        self.rows.append([])
        return 
    def add_to_current_row(self, symbol: Symbol) -> None:
        self.rows[-1].append(symbol)
        return
    async def from_code(self, code: str) -> Self:
        lines = code.split('\n')
        await logger.debug(code)
        await logger.debug(f'Building image from {len(lines)} lines of code')
        currentline = 1 # skipping first line which is function declaration
        while currentline < len(lines):
            line = lines[currentline].strip()
            currentline += 1 # for direct printing, inc here
            if len(line) > 0: #ignore blank lines, it also lstripped indention
                if 'MCP.' in line: #we have something
                    if 'await' in line: # square
                        self.add_to_current_row(Call(currentline))
                        self.add_row()
                        await logger.debug(f'Line{currentline} by itself on a row.')
                    elif line.startswith ('async gather'): #diamond
                        self.add_row()
                        self.add_to_current_row(Junction(currentline))
                        self.add_row()
                        await logger.debug(f'Line{currentline} is a diamond.')
                    else: 
                        self.add_to_current_row(Call(currentline))
                        await logger.debug(f'Line{currentline} shares a row.')
        self.add_to_current_row(End())
        return self

    async def svg(self) -> str:
        async def connect_rows(rows: List[List[Symbol]]) -> str:
            connectors = ''
            current_row = 1
            while current_row < len(rows):
                for upper_symbol in rows[current_row - 1]:
                    for lower_symbol in rows[current_row]:
                        await logger.debug(f'Connecting {upper_symbol} to {lower_symbol}')
                        connectors += f'<line x1="{upper_symbol.connection_point_lower[0]}" y1="{upper_symbol.connection_point_lower[1]}" x2="{lower_symbol.connection_point_upper[0]}" y2="{lower_symbol.connection_point_upper[1]}" stroke-width="1" stroke="blue" />'
                current_row += 1
            return connectors
        height = max(Flowchart.min_height, len(self.rows) * (2*Flowchart.symbol_radius + Flowchart.padding)+2*Flowchart.padding)
        width = max(Flowchart.min_width, max(len(row) for row in self.rows) * (2*Flowchart.symbol_radius + Flowchart.padding))
        svg  = f'<svg version="1.1" width="{width}" height="{height}" xmlns="http://www.w3.org/20000/svg">'
        await logger.debug(f'Flowchart has {len(self.rows)} rows')
        row_center = 0
        for row in self.rows:
            row_center += (2*Flowchart.symbol_radius)
            row_symbols = len(row)
            column_center = Flowchart.padding + int(row_symbols/2)*(2*Flowchart.symbol_radius)
            await logger.debug(f'{row}')
            for symbol in row:
                column_center += (2*Flowchart.symbol_radius)
                if row_symbols %2 == 1:
                    column_center += Flowchart.symbol_radius
                svg += symbol.svg(column_center, row_center, Flowchart.symbol_radius)
                column_center += Flowchart.padding
            row_center += Flowchart.padding
        svg += await connect_rows(self.rows)
        svg += '</svg>'
        return svg
