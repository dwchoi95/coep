
S = input()

ans = 0
state = 0
for i, Si in enumerate(S):
    
    if state < 1 and Si == 'B':
        state += 1
        marker = i
    elif state > 0 and Si == 'W':
        ans += i - marker
        marker += 1

print(ans)