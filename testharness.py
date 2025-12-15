# test harness
import asyncio
import pachinkoagentic
from fastmcp import Client

logger = pachinkoagentic.get_async_logger(__name__, 'DEBUG')   

async def main():
    library = pachinkoagentic.Library()\
                .add(Client('http://localhost:9001/mcp'))
    await library.reload()
    await logger.info(library.swagger_docs())
    return

if __name__ == '__main__':
    print("Hello")
    asyncio.run(main())
    print("Goodbye")
