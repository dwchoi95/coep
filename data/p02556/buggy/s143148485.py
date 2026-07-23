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

    print(max(Z) - min(Z))


main()