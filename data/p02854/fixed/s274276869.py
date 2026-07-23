
import sys
sys.setrecursionlimit(10000000)
INF = 1<<32


def solve(N: int, A: "List[int]"):
    r = [0] * (N+1)
    rr = [0] * (N+1)

    for i in range(1,N+1):
        r[i] = r[i-1] + A[i-1]
    
    for i in range(N-1, -1, -1):
        rr[i] = rr[i+1] + A[i]

    ans = INF
    for i in range(1,N):
        ans = min(ans, abs(r[i]-rr[i]))

    print(ans)

    
    return



def main():
    def iterate_tokens():
        for line in sys.stdin:
            for word in line.split():
                yield word
    tokens = iterate_tokens()
    N = int(next(tokens))  
    A = [int(next(tokens)) for _ in range(N)]  
    solve(N, A)

if __name__ == '__main__':
    main()
