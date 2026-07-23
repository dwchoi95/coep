N, K = map(int, input().split())

X = list(map(int, input().split()))


def calc_time(X):
    x_max = X[-1]
    x_min = X[0]

    if x_max * x_min >= 0:
        if abs(x_max) > abs(x_min):
            return x_max
        else:
            return abs(x_min)
    else:
        return x_max - x_min + min(abs(x_max), abs(x_min))

def calc_start_and_goal_position(index):
    if index - K >= 0:
        start_index = index - K
    else:
        start_index = 0
    
    if N > index + K:
        goal_index = index
    else:
        goal_index = N - K + 1
    
    return start_index, goal_index

if __name__ == "__main__":
    index = -1
    for i, x in enumerate(X):
        if x >= 0:
            index = i 
    if index == -1:
        index = i
    
    start_index, goal_index = calc_start_and_goal_position(index)

    time_min = float('inf')
    for i in range(start_index, goal_index):
        time = calc_time(X[i:i+K])
        if time < time_min:
            time_min = time

    print(time_min)