NM = list(map(int, input().split()))
A = list(map(int, input().split()))

count = 0
sumA = sum(A)
board = sumA / (4*NM[1])





for i in range(len(A)):
    if float(A[i]) >= board:
        count += 1
    else:
        continue


if count >= NM[1]:
    print("Yes")
else:
    print("No")
