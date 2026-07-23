def main():
    n = int(input())
    array = list(map(int, input().split()))
    sum_value = array[-1]
    for i in reversed(range(n-1)):
        if array[i - 1] <= array[i]:
            sum_value += array[i - 1]
        else:
            array[i - 1] = array[i]
            sum_value += array[i - 1]
    print(sum_value)

if __name__ == "__main__":
    main()
