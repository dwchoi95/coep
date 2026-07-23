from itertools import islice
def solve(A):
    memo = [0]*(10**6+1)

    for a in A:
        memo[a] += 1
    if memo[1] > 0:
        return 1 if memo[1] == 1 else 0

    res = 0
    for i,v in enumerate(islice(memo,2,None),start=2):
        if v > 0:
            res += 1 if v == 1 else 0
            j = i
            while j <= 10**6:
                memo[j] = 0
                j += i
    return res

if __name__ == '__main__':
    N = int(input())
    A = list(map(int,input().split()))
    print(solve(A))
