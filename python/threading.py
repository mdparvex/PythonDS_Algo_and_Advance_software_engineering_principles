# In threading: the OS switches between threads. It works for blocking scenario

# In asyncio: the Python event loop switches between tasks when they await.

import threading, time

def task(name):
    print(f"{name} started")
    time.sleep(2)
    print(f"{name} ended")

# Start both tasks
threading.Thread(target=task, args=("A",)).start()
threading.Thread(target=task, args=("B",)).start()

#time.sleep() blocks a thread, but other threads continue running.
#OS schedules each thread independently.

import asyncio

async def task(name):
    print(f"{name} started")
    await asyncio.sleep(2) #if i use time.sleep(2) it will block for seconds, will not work concurrently
    print(f"{name} ended")

async def main():
    await asyncio.gather(task("A"), task("B"))

asyncio.run(main())

#await asyncio.sleep() pauses the current task
#While waiting, the event loop switches to other tasks
#Requires non-blocking code (e.g., no time.sleep())

#more examples

import threading
import time

def task(name):
    for i in range(3):
        print(f"{name} is running...")
        time.sleep(1)

# Create threads
t1 = threading.Thread(target=task, args=("Thread-1",))
t2 = threading.Thread(target=task, args=("Thread-2",))

# Start threads
t1.start()
t2.start()

# Wait for completion
t1.join()
t2.join()

print("Both threads finished.")

#Thread Class and Custom Thread Subclassing
class MyThread(threading.Thread):
    def run(self):
        for _ in range(3):
            print(f"{self.name} is working")
            time.sleep(1)

t = MyThread()
t.start()
t.join()

#Daemon threads run in the background and automatically exit when the main thread exits.
def background_task():
    while True:
        print("Running background task...")
        time.sleep(2)

t = threading.Thread(target=background_task, daemon=True)
t.start()

time.sleep(5)
print("Main program done.")

#Event is used to notify one or more threads about something.
event = threading.Event()

def waiter():
    print("Waiting for signal...")
    event.wait()
    print("Signal received!")

def sender():
    time.sleep(2)
    event.set()

threading.Thread(target=waiter).start()
threading.Thread(target=sender).start()

