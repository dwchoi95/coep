
import sys
INF = float("inf")


def solve(S: str):

    if int(S) == 0:
        print(len(S))
        return

    N = len(S)
    ts = INF
    for i, c in enumerate(S):
        if i == 0:
            continue
        if S[i-1] != S[i]:
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
