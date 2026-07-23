s = str(input())
n = len(s)
distance = 0
count = 0
max_W = 0

for i in range(n):
    if s[i] == 'W':
        distance += (i - count)
        count += 1
        max_W = i

if s.count('W') == 0 or s.count('W') == n:
    print(0)
    exit()

print(distance)