# -*- coding: utf-8 -*-
import time
from contextlib import contextmanager


@contextmanager
def timer(name):
    """decorator used to timing"""
    start = time.time()
    yield
    finish = time.time()
    print(f'{name} took {finish - start:.4f} sec')
