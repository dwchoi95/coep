import sys
import collections
import bisect


def main():
    n = int(input())
    AList = list(map(int, input().split()))
    ASum = sum(AList)
    c = 0
    for i in range(n):
        c += AList[i]
        if c >= ASum / 2:
            k = i
            break
    ans = min(2 * c - ASum, ASum - 2 * c + 2 * AList[k])
    print(ans)


if __name__ == '__main__':
    main()
