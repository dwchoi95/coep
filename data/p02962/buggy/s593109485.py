import sys,queue,math,copy,itertools,bisect,collections,heapq

def main():
    MOD = 2**61-1
    SI = lambda : sys.stdin.readline().rstrip()

    s = SI()
    t = SI()
    s = s * 3
    lens = len(s)
    lent = len(t)

    def cx(x):
        return ord(x) - ord('a') + 1

    hash = 0
    for x in t:
        hash = (hash * 26 + cx(x)) % MOD

    cnt = 0
    f = False
    h = 0
    last_i = 0
    ans = 0
    for i in range(lens):
        if i >= lent:
            h -= cx(s[i-lent]) * pow(26,lent-1,MOD)
        h = (h * 26 + cx(s[i])) % MOD
        if h == hash:
            cnt += 1
            ans = max(ans,cnt)
            last_i = i
        else:
            if i - last_i >= lent and last_i > 0:
                cnt = 0
                f = True
    if f:
        print(ans)
    else:
        print(-1)

if __name__ == '__main__':
    main()