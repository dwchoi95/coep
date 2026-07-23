n = int(input())
a = list(map(int,input().split()))

s = sum(a)

left = 0
right = 0
for i in range(n):
    left += a[i]
    if left >= s/2:
        right = s - left
        break
    
if left == s/2:
    print(0)
else:
    print(abs(left-right))