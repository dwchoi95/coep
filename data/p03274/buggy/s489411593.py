import sys
input = sys.stdin.readline


def main():
    N, K = map(int, input().split())
    X = [int(c) for c in input().split()]

    def fullsearch():
        for i in range(N-K):
            l = X[i]
            r = X[i+K-1]
            distance = abs(r - l)
            if abs(l) > abs(r):
                distance += abs(r)
            else:
                distance += abs(l)
            yield distance

    if N == K:
        print(0)
    else:
        print(min(fullsearch()))

main()