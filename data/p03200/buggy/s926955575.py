s = input()
w_count = s.count('W')
ans = 0
for i in range(w_count):
    if s[i] == 'B':
        ans += w_count - i + 1
print(ans)