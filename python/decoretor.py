#python decorator
import time

def time_func(func):
    def wrapper():
        print("befor calling actual function")
        start_time = time.time()
        func()
        print("after calling actual function")
        end_time = time.time()
        print(f'calling time{start_time-end_time}')
    return wrapper

@time_func
def test():
    print('hello')

test()