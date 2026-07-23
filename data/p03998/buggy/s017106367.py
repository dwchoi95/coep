
import sys, math, fractions, itertools


def solve(S_A: str, S_B: str, S_C: str):
    t = 'a'
    A = list(S_A)
    B = list(S_B)
    C = list(S_C)
    while(True):
        if t == 'a':
            if len(A) == 0:
                w = 'A'
                break
            t = A.pop()
        elif t == 'b':
            if len(B) == 0:
                w = 'B'
                break
            t = B.pop()
        else:
            if len(C) == 0:
                w = 'C'
                break
            t = C.pop()
    print(w)
    return



def main():
    def iterate_tokens():
        for line in sys.stdin:
            for word in line.split():
                yield word
    tokens = iterate_tokens()
    S_A = next(tokens)  
    S_B = next(tokens)  
    S_C = next(tokens)  
    solve(S_A, S_B, S_C)

if __name__ == '__main__':
    main()
