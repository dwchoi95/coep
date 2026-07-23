s = str(input())
n = len(s)
count = 0
max_W = 0

for i in range(n):
    if s[i] == 'W':
        count += i
        max_W = i

if max_W == s.count('W') - 1 or s.count('W') == 0 or s.count('W') == n:
    print(0)
    exit()

print(count)