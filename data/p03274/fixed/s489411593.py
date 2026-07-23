import sys
input = sys.stdin.readline


def main():
    N, K = map(int, input().split())
    X = [int(c) for c in input().split()]

    def fullsearch():
        for i in range(N-K+1):
            l = X[i]
            r = X[i+K-1]
            distance = abs(r - l)
            yield distance + abs(r)
            yield distance + abs(l)

    print(min(fullsearch()))

main()