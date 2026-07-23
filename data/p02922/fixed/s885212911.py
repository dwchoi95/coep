def resolve():
    a, b = map(int, input().split())
    ret = 0
    if b > 1:
        from math import ceil
        ret = ceil((b - 1) / (a - 1))
    print(ret)


if __name__ == '__main__':
    resolve()