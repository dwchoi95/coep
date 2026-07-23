import sys

def main():
    input = sys.stdin.readline
    N = int(input())
    MOD = 10**9 + 7

    ans = 1
    for i in range(N):
        ans *= i
        ans = ans % MOD

    return ans


if __name__ == '__main__':
    print(main())
