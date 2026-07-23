import itertools


def read():
    N = int(input())

    return N,


def solve(N, ):
    for i in range(9):
        a = i + 1
        for j in range(9):
            b = j + 1
            if a*b==N:
                return "Yes"
            else:
                continue
    return "No"


            
            
            
            
            
            
            
            
            
            
            


if __name__ == '__main__':
    input = read()
    print(solve(*input))
