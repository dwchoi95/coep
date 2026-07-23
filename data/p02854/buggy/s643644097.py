
import math
N = int(input())
A = list(map(int, input().split()))

sum = 0
for i in range(len(A)):
    sum += A[i]

check_sum = 0
for i in range(len(A)):
    check_sum += A[i]
    if check_sum == sum/2:
        print(0)
        exit()
    if check_sum > sum / 2:
        if i+ 1 == len(A):
            print(A[i] - (check_sum - A[i]))
            exit()
        else:
            print(abs(2* check_sum - sum))
            exit()
