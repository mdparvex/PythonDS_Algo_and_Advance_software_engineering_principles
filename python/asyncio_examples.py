#Python has limitation t run parallal code execution (multiprocessing, concurrency) in single CPU. asyncio solved this issue by executing concurrent function when waition
# to execute current task. let see some examples
import asyncio

async def say_hello():
    await asyncio.sleep(2)
    print('hello world')

asyncio.run(say_hello())

async def do_something_else():
    print('start execution another task')
    await asyncio.sleep(1)
    print('finished another task')
async def main():
    await asyncio.gather(
        say_hello(),
        do_something_else()
    )
asyncio.run(main())

import requests
import time
import aiohttp
import aiofiles
# lets see the time differences between sync and async
start_time = time.time()

def fetch(url):
    return requests.get(url).text

page1 = fetch('http://example.com')
page2 = fetch('http://example.org')

print(f"Done in {time.time() - start_time} seconds")

#async function
async def fetch_async(url, session):
    async with session.get(url) as response:
        return await response.text()

async def main():
    async with aiohttp.ClientSession() as session:
        page1 = asyncio.create_task(fetch_async('http://example.com', session))
        page2 = asyncio.create_task(fetch_async('http://example.org', session))
        await asyncio.gather(page1, page2)

start_time = time.time()
asyncio.run(main())
print(f"Done in {time.time() - start_time} seconds")

# Asynchronously reading a single file
async def read_file_async(filepath):
    async with aiofiles.open(filepath, 'r') as file:
        return await file.read()

async def read_all_async(filepaths):
    tasks = [read_file_async(filepath) for filepath in filepaths]
    return await asyncio.gather(*tasks)

# Running the async function
async def main():
    filepaths = ['file1.txt', 'file2.txt']
    data = await read_all_async(filepaths)
    print(data)

asyncio.run(main())
#Sometimes, you can’t escape synchronous functions but still want to enjoy the async ride. Here’s how you can mix them:
import asyncio
import time

def sync_task():
    print("Starting a slow sync task...")
    time.sleep(5)  # Simulating a long task
    print("Finished the slow task.")

async def async_wrapper():
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, sync_task)

async def main():
    await asyncio.gather(
        async_wrapper(),
        # Imagine other async tasks here
    )

asyncio.run(main())
