from contextlib import contextmanager
from functools import wraps

@contextmanager
def timing(name):
    """decorator used to timing"""
    start = time.time()
    yield
    finish = time.time()
    print(f'{name} took {finish - start:.4f} sec')

def timer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        with timing(func.__name__):
            return func(*args, **kwargs)
    return wrapper
