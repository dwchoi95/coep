n = int(input())
a_tmp = input().split()
a = []
ans = 0
for _ in a_tmp:
    a.append(int(_))
i = 0
same = 1
while i < n-1:
    tmp = a[i]
    i += 1
    if a[i] == tmp:
        same += 1
        if same == 3:
            ans += 1
            same = 1
    else:
        if same >= 2:
            ans += 1
            same = 1
if same >= 2:
    ans += 1

print(ans)
