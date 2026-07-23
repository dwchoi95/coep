from sys import stdin
from bisect import insort


def main():
    N, M = [int(x) for x in stdin.readline().rstrip().split()]
    As = [int(x) for x in stdin.readline().rstrip().split()]
    As.sort()
    for _ in range(M):
        x = As[-1] / 2
        insort(As, x)
        del As[-1]
    sum_ = 0
    for x in As:
        sum_ += x
    print(sum_)


if __name__ == "__main__":
    main()
