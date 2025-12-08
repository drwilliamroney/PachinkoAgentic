# -*- coding: utf-8 -*-
"""
@author: Dr. William N. Roney

Because MCP has logging ability from server to client, this is a wrapper that links
  with Python standard logging.  An MCP server that logs will do so to their Python logging as well
  as across the MCP protocol to the client which will also log.
"""

import logging
from typing import Literal, Any
from rich.console import Console
from rich.logging import RichHandler

#FORMAT = "[<%(name)s> %(asctime)s:%(filename)s:%(lineno)s:%(levelname)s] %(message)s"
#logging.basicConfig(format=FORMAT, level=logging.INFO)

class MCPLogger():
    def __init__(self, logger):
        self.logger = logger
    def get_destination(self):
        logger_name = None
        ctx = None
        try:
            from fastmcp.server.dependencies import get_context
            ctx = get_context()
            if ctx is not None:
                mcp = ctx.fastmcp
                if mcp is not None:
                    logger_name = mcp.name
        except:
            pass
        return logger_name, ctx
        
    async def info(self, message: str) -> None:
        self.logger.info(message, stacklevel=2)
        name, ctx = self.get_destination()
        if ctx is not None:
            await ctx.info(message,name)
        return
    async def debug(self, message: str) -> None:
        self.logger.debug(message, stacklevel=2)
        name, ctx = self.get_destination()
        if ctx is not None:
            await ctx.debug(message,name)
        return
    async def error(self, message: str) -> None:
        self.logger.error(message, stacklevel=2)
        name, ctx = self.get_destination()
        if ctx is not None:
            await ctx.error(message,name)
        return
    async def warning(self, message: str) -> None:
        self.logger.warning(message, stacklevel=2)
        name, ctx = self.get_destination()
        if ctx is not None:
            await ctx.warning(message,name)
        return
    async def warn(self, message: str) -> None:
        self.logger.warning(message, stacklevel=2)
        name, ctx = self.get_destination()
        if ctx is not None:
            await ctx.warning(message,name)
        return

def get_async_logger(name: str, 
               level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] | int = "INFO") -> MCPLogger:
    logger = logging.getLogger(name)        
    configure_logging(logger=logger, level=level)
    return MCPLogger(logger)

def configure_other_logging(loggers:list,
                         level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] | int = "INFO") -> None:
    for logger in loggers:
        configure_logging(logger=logging.getLogger(logger), level=level)
    return

def quiet_spammers(spammers:list) -> None:
    for spammer in spammers:
        spamlogger = logging.getLogger(spammer)
        spamlogger.setLevel(logging.WARNING)
    return

def configure_logging(
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] | int = "INFO",
    logger: logging.Logger | None = None,
    enable_rich_tracebacks: bool = True,
    **rich_kwargs: Any,
) -> None:
    """
    Configure logging for FastMCP.

    Args:
        logger: the logger to configure
        level: the log level to use
        rich_kwargs: the parameters to use for creating RichHandler
    """

    if logger is None:
        logger = logging.getLogger("FastMCP")

    # Only configure the FastMCP logger namespace
    handler = RichHandler(
        console=Console(stderr=True),
        show_path = False,
        enable_link_path=False,
        **rich_kwargs,
    )
    formatter = logging.Formatter("%(filename)s:%(lineno)d=>%(message)s")
    handler.setFormatter(formatter)

    logger.setLevel(level)

    # Remove any existing handlers to avoid duplicates on reconfiguration
    for hdlr in logger.handlers[:]:
        logger.removeHandler(hdlr)

    logger.addHandler(handler)

    # Propagate to the root logger
    logger.propagate = True    

