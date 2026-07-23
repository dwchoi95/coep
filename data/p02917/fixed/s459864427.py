def main():
    n = int(input())
    array = list(map(int, input().split()))
    sum_value = array[-1] + array[0]
    for i in range(n-2):
        sum_value += min(array[i], array[i+1])
        
    print(sum_value)

if __name__ == "__main__":
    main()
