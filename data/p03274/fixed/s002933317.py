a,b = list(map(int, input().split()))
n = list(map(int, input().split()))

ans = []
for i, name in enumerate(n):
    if b+i >a:
        break
    ans.append(min( (abs(n[i]) + abs(n[i +b-1] - n[i]),  abs(n[i+b-1]) + abs(n[i +b-1] - n[i]) )) )

print(min(ans))