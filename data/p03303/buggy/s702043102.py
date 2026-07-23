s = list(input())
ans =[]

for i in range(len(s)):
    if i%3 == 0:
        ans.append(s[i])
        
print("".join(ans))