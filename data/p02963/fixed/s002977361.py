def f():
    s = int(input())
    i9 = 10**9
    if s == i9 ** 2:
        print(i9, 0, 0, i9, 0, 0)
    else:
        print(i9 - (s%i9), s

if __name__ == '__main__':
    f()
