if __name__ == "__main__":
    a, b, c, d = map(int, input().split())
    x_list = [a, b]
    y_list = [c, d]
    ans = 0

    if x_list[0] <= 0 and x_list[1] <= 0 and y_list[0] >= 0 and y_list[1] >= 0:
        ans = max(x_list) * min(y_list)
    elif x_list[0] >= 0 and x_list[1] >= 0 and y_list[0] <= 0 and y_list[1] <= 0:
        ans = max(y_list) * min(x_list)
    elif (x_list[0] <= 0 or x_list[1] <= 0) and (y_list[0] <= 0 or y_list[1] <= 0):
        ans = max(min(x_list) * min(y_list), max(x_list) * max(y_list))
    else:
        ans = max(x_list) * max(y_list)

    print(ans)