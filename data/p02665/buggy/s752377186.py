def main():
    import sys
    import math
    input = sys.stdin.buffer.readline
    n = int(input())
    A = list(map(int, input().split()))
    ans = 0
    nodes = 0
    for i in range(n,-1,-1):
        if i == 0:
            ans +=1 
            break
        if math.ceil(nodes/2) + A[i] > 2**i:
           
            print(-1)
            exit(0)
        nodes += A[i]
        nodes = min(2**i,nodes)
        ans += nodes
    print(ans)

if __name__ == '__main__':
    main()