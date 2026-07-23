import sys

readline = sys.stdin.readline
MOD = 10 ** 9 + 7
INF = float('INF')
sys.setrecursionlimit(10 ** 5)


def main():
    n, x = map(int, readline().split())
    ans = [0] * (2 * n - 1)

    if x == 1 or x == (2 * n - 1):
        print("No")
        return

    for i in range(1, n + 1):
        if i % 2 == 1:
            ans[i - 1] = (x - 1 + abs(n - i)) % (2 * n - 1) + 1
        else:
            ans[i - 1] = (x - 1 - abs(n - i)) % (2 * n - 1) + 1
    ans[n] = x

    for i in range(n + 1, 2 * n):
        if i % 2 == 0:
            ans[i - 1] = (x - 1 + abs(n - i)) % (2 * n - 1) + 1
        else:
            ans[i - 1] = (x - 1 - abs(n - i)) % (2 * n - 1) + 1
    
    print("Yes")
    print(*ans, sep="\n")


if __name__ == '__main__':
    main()
