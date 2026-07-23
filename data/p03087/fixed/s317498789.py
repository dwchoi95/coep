import sys
input = sys.stdin.readline

def main():
    N, Q = map(int, input().split())
    S = input().rstrip()

    cnt_ac = 0
    arr_ac = [0] * (N)
    for x in range(0, N-1):
        if S[x:x+2] == 'AC':
            cnt_ac += 1
        arr_ac[x+1] = cnt_ac

    for i in range(Q):
        L, R = map(int, input().split())
        print(arr_ac[R-1] - arr_ac[L-1])


main()