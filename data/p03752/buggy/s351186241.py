from itertools import combinations
INF = int(1e18)
def main():
    n, k = map(int, input().split())
    a = [int(i) for i in input().split()]
    p = [i for i in range(1,n)]
    
    
    ans = INF
    for i in combinations(p, k-1):
        s = set(i)
        cost = 0
        mx = a[0]
        for j in range(1, n):
            if j in s:
                if a[j] > mx:
                    continue
                mx += 1
                cost += mx-a[j]
            mx = max(mx, a[j])
        ans = min(cost, ans)                
    print(ans)
main()