import sys
import collections
import bisect


def main():
    n = int(input())
    AList = list(map(int, input().split()))
    sumAList = AList
    sumA = sum(AList)
    for i in range(n):
        if i != 0:
            AList[i] = AList[i] + AList[i - 1]
        if sumA - AList[i] <= AList[i]:
            print(abs(sumA - 2 * AList[i]))
            return

    print(sumAList)


if __name__ == '__main__':
    main()
