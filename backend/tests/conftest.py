import pytest
import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal
from scripts.purge_test_data import purge

@pytest.fixture(scope="session", autouse=True)
def cleanup_after_test_suite():
    yield
    # Run purge after all tests complete
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(purge())
        else:
            loop.run_until_complete(purge())
    except Exception as e:
        # Fallback to new event loop
        new_loop = asyncio.new_event_loop()
        new_loop.run_until_complete(purge())
        new_loop.close()

