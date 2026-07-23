N = int(input())
s = list(input().split())
cnt = 0
for a in s:
    if s == 'R':
        cnt += 1
if N - cnt < cnt:
    print('Yes')
else:
    print('No')