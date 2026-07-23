import functools

import os

INF = float('inf')


def inp():
    return int(input())


def inpf():
    return float(input())


def inps():
    return input()


def inl():
    return list(map(int, input().split()))


def inlf():
    return list(map(float, input().split()))


def inls():
    return input().split()


def inpm(line):
    return [inp() for _ in range(line)]


def inpfm(line):
    return [inpf() for _ in range(line)]


def inpsm(line):
    return [inps() for _ in range(line)]


def inlm(line):
    return [inl() for _ in range(line)]


def inlfm(line):
    return [inlf() for _ in range(line)]


def inlsm(line):
    return [inls() for _ in range(line)]


def debug(fn):
    if not os.getenv('LOCAL'):
        return fn

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        print('DEBUG: {}({}) -> '.format(
            fn.__name__,
            ', '.join(
                list(map(str, args)) +
                ['{}={}'.format(k, str(v)) for k, v in kwargs.items()]
            )
        ), end='')
        ret = fn(*args, **kwargs)
        print(ret)
        return ret

    return wrapper

a, b, c = inl()
if a == b:
    print(c)
elif a ==c:
    print(b)
else:print(a)
