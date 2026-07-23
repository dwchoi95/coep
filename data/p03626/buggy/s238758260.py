n = int(input())

s1 = input()
s2 = input()

INF = 1000000009

left = None
index = 0
cnt = 0
while index < n:
    
    if s1[index] == s2[index]:
        index += 1
        if left is None:
            left = 1
            cnt = 3
        
        elif left == 1:
            cnt *= 2
        
        else:
            cnt *= 1
        left = 1

    
    else:
        index += 2
        if left is None:
            left = 2
            cnt = 6
        
        elif left == 1:
            cnt *= 2
        
        else:
            cnt *= 3
        left = 2
    cnt = cnt % INF
print(cnt)