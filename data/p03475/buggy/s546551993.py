import sys
read = sys.stdin.buffer.read
readline = sys.stdin.buffer.readline
readlines = sys.stdin.buffer.readlines


n = int(readline())
csf = [tuple(map(int, readline().split())) for _ in range(n-1)]

for i in range(n):
    now = 0
    for c, s, f in csf[i::]:
        if now <= s:
            now += s - now + c
        else:
            now += (now-s) % f + c
    print(now)
