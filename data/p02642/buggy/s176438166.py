
def main():
    import sys
    imput = sys.stdin.readline
    
    
    
    N = int(input())
    A = list(map(int, input().split()))

    
    from collections import Counter
    M = max(A) + 1
    B = [True] * (M)
    A = sorted(A)
    C = Counter(A)

    answer = 0
    for a in A:
        if C[a] > 1:
            continue
        elif B[a]:
            answer += 1
            for j in range(a, M, a):
                B[j] = False

    print(answer)

    
if __name__ == "__main__":
    main()
