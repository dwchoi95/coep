N = int(input())
s = input()
cnt = 0
for a in s:
    if a == 'R':
        cnt += 1
if N - cnt < cnt:
    print('Yes')
else:
    print('No')