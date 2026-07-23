import sys
input = sys.stdin.readline

def main():
    N, Q = map(int, input().split())
    S = list(input().rstrip())

    dec_a = [0] * (N)
    for x in range(1, N):
        if S[x] == 'C' and S[x-1] == 'A':
            S[x-1] = 'a'
        dec_a[x] = S[:x+1].count('a')


    L = [0] * Q
    R = [0] * Q
    for i in range(Q):
        L[i], R[i] = map(int, input().split())

    print(dec_a)
    for j in range(Q):
        print(dec_a[R[j]-1] - dec_a[L[j]-1])

main()