def f():
    s = int(input())
    y = s
    x = 10**9 - s%(10**9)

    ans = [0, 0, 10**9, 1, x, y]
    
    print(*ans)

if __name__ == '__main__':
    f()
