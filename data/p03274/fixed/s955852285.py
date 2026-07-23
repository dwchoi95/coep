

def main():
    n, k = map(int, input().split())
    x_list = list(map(int, input().split()))
    ans = float('inf')

    for i in range(n - k + 1):
        if x_list[i] >= 0 and x_list[i+k-1] >= 0:
            ans = min(ans, x_list[i+k-1])
        elif x_list[i] <= 0 and x_list[i+k-1] <= 0:
            ans = min(ans, -x_list[i])
        else:
            ans = min(ans, min(-x_list[i] * 2 + x_list[i+k-1] , -x_list[i] + x_list[i+k-1] * 2))
    print(ans)

if __name__ == '__main__':
    main()