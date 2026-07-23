import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")


def main():
    N = int(input())
    A = list(map(int, input().split()))
    B = list(map(int, input().split()))
    logging.info(A)
    logging.info(B)

    counter = 0
    for i in range(N):
        if A[i] < B[i]:
            
            if (A[i] + A[i + 1]) > B[i]:
                counter += B[i]
                A[i + 1] = A[i + 1] - B[i] + A[i]
                B[i] = 0
            else:
                counter += (A[i] + A[i + 1])
                B[i] = B[i] - A[i] - A[i + 1]
                A[i + 1] = 0
                
        elif A[i] == B[i]:
            counter += A[i]
            B[i] = 0
            A[i] = 0
                
        else:
            counter += B[i]
            B[i] = 0

    if B[N - 1] > A[N]:
        counter += A[N]
    elif B[N - 1] != 0:
        counter += B[N - 1]

    print(counter)
            
    
if __name__ == "__main__":
    main()
