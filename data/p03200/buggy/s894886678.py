s = list(input())
b_counts = []
cnt = 0
for i in range(len(s)):
    if s[i] == "B":
        cnt += 1
    if s[i] == "W":
        cnt += sum(b_counts)
        b_counts.append(cnt)
        cnt = 0
print(sum(b_counts))
