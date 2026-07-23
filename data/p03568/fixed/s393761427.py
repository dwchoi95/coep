n = int(input())
A = list(map(int, input().split()))

ans = 1
for a in A:
    
    
    
        ans *= 3

odd = 1
for a in A:
    if a%2 == 0:
        odd *= 2

print(ans-odd)
