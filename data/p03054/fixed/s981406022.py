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
    bot += 1
elif s[-1] == "D":
    top -= 1

for i in range(n-2, -1, -1):
    if t[i] == "L":
        right = min(w, right+1)
    elif t[i] == "R":
        left = max(1, left-1)
    elif t[i] == "U":
        top = min(h, top+1)
    elif t[i] == "D":
        bot = max(1, bot-1)
    if s[i] == "L":
        left += 1
    elif s[i] == "R":
        right -= 1
    elif s[i] == "U":
        bot += 1
    elif s[i] == "D":
        top -= 1
    if left > right or bot > top:
        print("NO")
        exit()
if left <= sc <= right and bot <= sr <=top:
    print("YES")
else:
    print("NO")