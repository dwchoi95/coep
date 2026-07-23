
def main():
    import sys
    imput = sys.stdin.readline
    
    
    
    N = int(input())
    A = list(map(int, input().split()))

    
    from collections import Counter
    M = max(A) + 1
    B = [True] * (M+1)
    A = sorted(A)
    C = Counter(A)

    answer = 0
    for a in A:
        if B[a]:
            for j in range(a, M, a):
                B[j] = False
            if C[a] > 1:
                continue
            else:
                answer += 1

    print(answer)

    
if __name__ == "__main__":
    main()
