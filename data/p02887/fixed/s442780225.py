def solve():
    N = int(input())
    S = input()

    ans = 1
    pre = S[0]
    for i in range(1,int(len(S))):
        if S[i] != pre:
            ans += 1
            pre = S[i]
    
    print(ans)

solve()