A,B = map(int,input().split())
ans = 0
for i in range(A,B+1):
    i = str(i)
    if i[0] == i[4]:
        if i[1] == i[3]:
            ans += 1
        else:
            ans += 0
    else:
        ans += 0
print(ans)