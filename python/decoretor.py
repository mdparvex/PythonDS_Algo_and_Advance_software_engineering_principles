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

#test()
#applying multiple decoretor

def bold_decoretor(func):
    def wrapper(*args, **kwargs):
        print('inside first decoretor')
        return "<b>" + func(*args, **kwargs) + "</b>"
    return wrapper
def italic_decorator(func):
    def wrapper(*args, **kwargs):
        print('inside second decoretor')
        return "<i>" + func(*args, **kwargs) + "</i>"
    return wrapper

@italic_decorator
@bold_decoretor
def get_text(text):
    return text

print(get_text('hello world'))