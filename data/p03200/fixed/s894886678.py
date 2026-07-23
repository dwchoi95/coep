s = list(input())

cnt = 0
prev_cnt = 0
result = 0
for i in range(len(s)):
    if s[i] == "B":
        cnt += 1
    if s[i] == "W":
        cnt += prev_cnt
        result += cnt
        prev_cnt = cnt
        cnt = 0
print(result)
