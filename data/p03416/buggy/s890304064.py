A,B = map(int,input().split())

cnt = 0

for i in range(A,B+1):
    
    Str = str(i)
    
    if Str[:2] == Str[3:]:
        cnt += 1
        
print(cnt)