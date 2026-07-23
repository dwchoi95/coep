
import sys
INF = float("inf")


def solve(S: str):

    N = len(S)
    ts = N
    for i in range(1, N):
        if S[i] != S[i-1]:
            ts = min(ts, max(i, N-i))
    print(ts)
    return


def main():

    def iterate_tokens():
        for line in sys.stdin:
            for word in line.split():
                yield word
    tokens = iterate_tokens()
    S = str(next(tokens))  
    solve(S)


if __name__ == '__main__':
    main()
