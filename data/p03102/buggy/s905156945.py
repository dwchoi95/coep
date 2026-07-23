def main():
    N, M, C = map(int, input().split())
    
    B = list(map(int, input().split())) 
    A = [[] for i in range(N)]
    for i in range(N):
        A[i] = list(map(int, input().split()))
    print('B=',B)
    print('A=',A)
    
    num = 0
    for i in range(N):
        sum = 0
        for j in range(M):
            sum = sum + A[i][j]*B[j]
        result = sum + C
        if (result > 0 ):
            num = num + 1
    print(num)
    return num

main()
