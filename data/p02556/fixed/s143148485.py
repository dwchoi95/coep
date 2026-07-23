import sys


def main():
    N = int(sys.stdin.readline().rstrip())

    X = [None] * N
    Y = [None] * N 
    Z = [None] * N

    for i in range(N):
        x, y = map(int, sys.stdin.readline().rstrip().split())
        X[i] = x
        Y[i] = y
    
    X_min = min(X)
    Y_min = min(Y)

    for i in range(N):
        X[i] = X[i] - X_min
        Y[i] = Y[i] - Y_min
        Z[i] = X[i] + Y[i]

    ans1 = max(Z) - min(Z)

    X_max = max(X)

    for i in range(N):
        X[i] = X_max - X[i]
        Y[i] = Y[i] - Y_min
        Z[i] = X[i] + Y[i]

    ans2 = max(Z) - min(Z)

    print(max(ans1, ans2))


main()