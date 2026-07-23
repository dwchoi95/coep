x, y = map(int, input().split())
 
num = 0
while x <= y:
    num += 1
    x *= 2
    
print(num)