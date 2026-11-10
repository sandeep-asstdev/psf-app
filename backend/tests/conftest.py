import pytest
import pytest_asyncio
from scripts.purge_test_data import purge
from app.core.database import engine

@pytest_asyncio.fixture(scope="session", autouse=True)
async def cleanup_after_test_suite():
    yield
    try:
        await purge()
        await engine.dispose()
    except Exception as e:
        print(f"Cleanup warning: {e}")
