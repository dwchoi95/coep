import sys

def main():
    input = sys.stdin.readline
    N = int(input())
    A = [list(map(str, input().strip())) for _ in range(2)]
    MOD = 10**9 + 7

    D = []
    flag = False
    for i in range(N):
        if A[0][i] != A[1][i] and flag:
            D.append('h')
            flag = False
        elif A[0][i] != A[1][i]:
            flag = True
        else:
            D.append('v')

    if D[0] == 'h':
        ans = 6
    else:
        ans = 3

    for i in range(1, len(D)):
        if D[i-1] == 'v' and D[i] == 'h':
            ans *= 2
        elif D[i-1] == 'v' and D[i] == 'v':
            ans *= 2
        elif D[i-1] == 'h' and D[i] == 'h':
            ans *= 3
        else:
            ans *= 1

    return ans % MOD


if __name__ == '__main__':
    print(main())
