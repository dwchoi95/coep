x,y = map(int, input().split())
count = 0
while x*2 <= y:
    x = x*2
    count += 1
print(count)