s = list(input())
w = int(input())
ans =[]
 
for i in range(len(s)):
    if i%w == 0:
        ans.append(s[i])
        
print("".join(ans))