s = input()
n = len(s)
rl = 0
lr = 0
count = [0, 0]
ans = [0] * n
prev = s[0]
for i in range(n):
    if s[i] != prev:
        if s[i] == 'L':
            rl = i
            ans[rl - 1] += count[0]
            ans[rl] += count[1]
            count = [0, 0]
            
        if s[i] == 'R':
            lr = i
            ans[rl] += count[0]
            ans[rl - 1] += count[1]
            count = [0, 0]
            
    if s[i] == 'L':
        count[(i - rl) % 2] += 1
    if s[i] == 'R':
        count[(i - lr) % 2] += 1
    prev = s[i]
    
ans[rl] += count[0]
ans[rl - 1] += count[1]

print(' '.join(map(lambda x: str(x), ans)))






