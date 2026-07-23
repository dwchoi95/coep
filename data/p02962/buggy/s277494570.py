import sys,queue,math,copy,itertools,bisect,collections,heapq

def main():
    MOD = 2**61-1
    SI = lambda : sys.stdin.readline().rstrip()

    s = SI()
    t = SI()
    lens = len(s)
    lent = len(t)

    def cx(x):
        return ord(x) - ord('a') + 1

    hsh = 0
    for x in t:
        hsh = (hsh * 27 + cx(x)) % MOD

    cnt = 0
    f = False
    h = 0
    last_i = 0
    ans = 0
    i = 0
    while True:
        if i >= lent:
            h -= cx(s[(i - lent)%lens]) * pow(27,lent-1,MOD)
        h = (h * 27 + cx(s[i % lens])) % MOD
        if h == hsh:
            cnt += 1
            ans = max(ans,cnt)
            last_i = i
        else:
            if i - last_i >= lent and ans > 0:
                cnt = 0
                f = True
        if i > lens*2 and i > lent:
            break
        i += 1

    if f or ans == 0:
        print(ans)
    else:
        print(-1)

if __name__ == '__main__':
    main()