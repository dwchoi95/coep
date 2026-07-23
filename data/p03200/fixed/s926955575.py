s = input()
ans = 0
w_count = 0
for i in range(len(s)):
    if s[i] == 'W':
        ans += i - w_count
        w_count += 1
print(ans)
