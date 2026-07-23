n = int(input())
s1 = input()
s2 = input()
cnt = 1
i = 0
while i <= n-1:
    if i == 0:
        if s1[i] == s2[i]:
            cnt *= 3
            s = 0
        else:
            cnt *= 6
            i += 1
            s = 1
    elif s1[i] == s2[i]:
        if s == 0:
            cnt *= 2
        else:
            cnt *= 1
        s = 0
    else:
        if s == 0:
            cnt *= 2
        else:
            cnt *= 3
        s = 1
        i += 1
    i += 1
print(cnt)