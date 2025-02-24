import asyncio
import time

import aiohttp


async def main():
    sites = ["https://www.jython.org", "https://olympus.realpython.org/dice"] * 80

    start_time = time.perf_counter()
    await download_all_sites(sites)
    duration = time.perf_counter() - start_time
    print(f"Download {len(sites)} sites in {duration} seconds")


async def download_all_sites(sites):
    async with aiohttp.ClientSession() as session:
        tasks = [download_site(url, session) for url in sites]
        await asyncio.gather(*tasks, return_exceptions=True)


async def download_site(url, session):
    async with session.get(url) as response:
        print(f"Read {len(response.content)} bytes from {url}")


# def get_session_for_thread():
#     if not hasattr(thread_local, "session"):
#         thread_local.session = requests.Session()
#     return thread_local.session


if __name__ == "__main__":
    asyncio.run(main())
