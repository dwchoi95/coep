s = list(input())

count = 0
white = 0
for i in range(len(s)):
    if s[i] == 'W':
        count += i - white
        white += 1

print(count)
