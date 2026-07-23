a, b, k = map(int, input().split())
 
num = min(a, b)
answer = []
for i in range(1, num+1):
    if (a % i == 0 and b % i == 0):
        answer.append(i)
        
print(answer[-k])