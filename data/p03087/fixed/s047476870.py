N, Q = map(int, input().split())
S = input()
S_list = list(S)
count_list = [0]*N

for i in range(1, N):
    count_list[i] += count_list[i-1] 
    if S_list[i-1] == "A" and S_list[i] == "C":
        count_list[i] += 1

for i in range(Q):
    start, end = map(int, input().split())
    count = count_list[end-1] - count_list[start-1]
    print(count)