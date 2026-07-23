def solve():
    N = int(input())
    A = list(map(int,input().split()))

    sm = sum(A)
    agg = 0
    idx = 0
    mid = sm / 2
    shrink_cnt = 0
    while agg < mid and idx < N-1:
        shrink_cnt += A[idx] - 1
        
        agg += A[idx]
        idx += 1
    
    shrink = (agg-mid) / 0.5
    expand = (mid - (agg-A[idx]))/0.5

    if shrink <= shrink_cnt:
        ans = min(shrink, expand)
    else:
        ans = expand
    
    print(int(ans))

if __name__ == '__main__':
    solve()