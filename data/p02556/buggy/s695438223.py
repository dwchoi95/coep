N = int(input())

max_f_0 = 0
min_f_0 = 10**10
max_f_1 = 0
min_f_1 = 10**10

for _ in range(N):
    x, y = map(int, input().split(" "))
    f_0 = x - y
    f_1 = x + y
    
    if max_f_0 < f_0:
        max_f_0 = f_0
    if min_f_0 > f_0:
        min_f_0 = f_0
    if max_f_1 < f_1:
        max_f_1 = f_1
    if min_f_1 > f_1:
        min_f_1 = f_1
        
print(max((max_f_0-min_f_0), (max_f_1-min_f_1)))
    