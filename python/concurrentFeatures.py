import concurrent.futures
import time

def task(name):
    print(f"Starting task {name}")
    time.sleep(1) # Simulate I/O operation
    print(f"Finished task {name}")
    return f"Result from {name}"

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    # Submit tasks
    future1 = executor.submit(task, "A")
    future2 = executor.submit(task, "B")
    future3 = executor.submit(task, "C")

    # Retrieve results
    print(future1.result())
    print(future2.result())
    print(future3.result())

import concurrent.futures
import time
import requests

# Function to download a webpage
def download_page(url):
    response = requests.get(url)
    return f"{url} - {len(response.content)} bytes"

# List of URLs to download
urls = [
    "https://www.example.com",
    "https://www.python.org",
    "https://www.github.com",
]

# Using ThreadPoolExecutor to download pages concurrently
start_time = time.time()

with concurrent.futures.ThreadPoolExecutor() as executor:
    futures = [executor.submit(download_page, url) for url in urls]
    for future in concurrent.futures.as_completed(futures):
        print(future.result())

end_time = time.time()
print(f"Downloaded all pages in {end_time - start_time:.2f} seconds")