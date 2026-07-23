def resolve():
    a, b = map(int, input().split())
    ret = 0
    if b > 1:
        n, m = divmod(b, a)
        ret = n + (1 if m > 0 else 0)
    print(ret)


if __name__ == '__main__':
    resolve()