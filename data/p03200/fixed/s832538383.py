
import sys, math, fractions, itertools, collections, copy, heapq


def solve(S: str):
    counter = 0
    c = 0
    for i, s in enumerate(S):
        if s == 'W':
            counter += i - c
            c += 1
    print(counter)
    return



def main():
    def iterate_tokens():
        for line in sys.stdin:
            for word in line.split():
                yield word
    tokens = iterate_tokens()
    S = next(tokens)  
    solve(S)

if __name__ == '__main__':
    main()
