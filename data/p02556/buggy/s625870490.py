n = int(input())
xy_array = [list(map(int, input().split())) for _ in range(n)]

th = pow(10, 9)
right_up_max = 0
left_down_min = th
left_up_max = 0
right_down_min = th

for x, y in xy_array:
    right_up_max = max(x + y, right_up_max)
    left_down_min = min(x + y, left_down_min)
    left_up_max = max(th - x + y, left_up_max)
    right_down_min = min(th - x + y, right_down_min)

ans = max(right_up_max - left_down_min, left_up_max - right_down_min)
print(ans)