def main():
    import sys
    import math
    input = sys.stdin.buffer.readline
    n = int(input())
    A = list(map(int, input().split()))
    ans = 0
    node = 1
    max_node = sum(A)
    for i in range(n+1):
        ans += node
        max_node -= A[i]
        node = min(max_node,(node-A[i])*2)
        if node < 0:
            print(-1)
            exit(0)
    print(ans)


if __name__ == '__main__':
    main()