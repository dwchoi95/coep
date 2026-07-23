


N = int(input())
a_list = list(map(int, input().split()))


min_cost = 10**18
left_sum = 0
right_sum = sum(a_list)


for i in range(N-1):
    left_sum += a_list[i]
    right_sum -= a_list[i]
    distance = abs(left_sum - right_sum)
    min_cost = min(min_cost, distance)


print(min_cost)
