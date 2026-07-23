import itertools


def read():
    N = int(input())

    return N,


def solve(N, ):
    for i in range(9):
        a = i + 1

        b = N / a

        if b in [1,2,3,4,5,6,7,8,9]:
            continue
        if a * b == N:
            return "Yes"
        else:
            return "No"


if __name__ == '__main__':
    input = read()
    print(solve(*input))