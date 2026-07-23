h,w,n = map(int, input().split())
sr, sc = map(int, input().split())
s = input()
t = input()

left = 1
right = w
bot = 1
top = h


if s[-1] == "L":
    left += 1
elif s[-1] == "R":
    right -= 1
elif s[-1] == "U":
    top -= 1
elif s[-1] == "D":
    bot += 1

for i in range(n-2, -1, -1):
    
    
    if t[i] == "L":
        right = min(w, right+1)
    elif t[i] == "R":
        left = max(0, left-1)
    elif t[i] == "U":
        bot = max(0, bot-1)
    elif t[i] == "D":
        top = min(h, top+1)
    
    
    if s[i] == "L":
        left += 1
    elif s[i] == "R":
        right -= 1
    elif s[i] == "U":
        top -= 1
    elif s[i] == "D":
        bot += 1
    if left >= right or bot >= top:
        print("NO")
        exit()


if left <= sc <= right and bot <= sr <=top:
    print("YES")
else:
    print("NO")