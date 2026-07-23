def main():
    
    N = int(input())
    *A, = map(int, input().split())

    
    ans = 0
    i = 1
    while i < N:
        if A[i-1] == A[i]:
            ans += 1
            i += 2
        else:
            i += 1
    print(ans)


if __name__ == '__main__':
    main()
