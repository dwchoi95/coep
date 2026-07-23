def solve():
    N = int(input())
    A = list(map(int,input().split()))

    sm = sum(A)
    agg = 0
    idx = 0
    mid = sm / 2
    shrink_cnt = sm - N
    while agg < mid and idx < N-1:
        
        agg += A[idx]
        idx += 1
    
    oneleft = agg
    oneright = sm - oneleft 
    twoleft = agg-A[idx-1]
    tworight = sm - twoleft
    ans = min(abs(oneleft-oneright), abs(twoleft-tworight))

    print(int(ans))

if __name__ == '__main__':
    solve()