def main():
    import sys
    sys.setrecursionlimit(10**9)
    input = sys.stdin.readline
    from collections import Counter

    N = int(input())
    A = list(map(int, input().split()))
    counter_A = Counter(A)
    flag = [True] * 1000001

    count = 0
    for i in sorted(counter_A.keys()):
        if counter_A[i] == 1 and flag[i]:
            count += 1
        multiple = i
        while multiple < 1000001:
            flag[multiple] = False
            multiple += i

    print(count)


main()