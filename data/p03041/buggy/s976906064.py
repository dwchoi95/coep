N , K = map(int,input().split())
str_t = list(input())
ans =''
for i in range(len(str_t)):
    if i == K:
        ans += str_t[i].lower()
    else:
        ans += str_t[i].upper()
print(ans)