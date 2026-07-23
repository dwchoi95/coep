s = input()
g, p = 0, 0
ans = 0
for e in s:
    if e == "g":
        if p+1 <= g:
            p += 1
            ans += 1
        else:
            g += 1
    else:
        p += 1

print(ans)
