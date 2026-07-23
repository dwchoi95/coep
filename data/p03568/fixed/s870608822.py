




from functools import reduce
from itertools import repeat


def multipler(x, y):
    return x*y

def hundred_or_one(l: list):
    return [True if x == 100 else False for x in l]
    

def check_odds(l :list):
    return [True if x % 2 == 0 else False for x in l]

def check_hun(l: list):
    return [True if x == 100 else False for x in l]

def main(num, data:list):
    
    hun_one = hundred_or_one(data)
    odds = check_odds(data)  
    huns = check_hun(data)

    basis = [3 for t in hun_one]

    
    remover = [2 if o else 1 for o in odds]

    remover_num = int(reduce(multipler, remover))
    
    

    basic_answer = reduce(multipler, basis)
    
    
    return basic_answer - remover_num

if __name__ == '__main__':
    
    
    num = int(input())
    data = input().split(" ")
    data = [int(i) for i in data]

    print(main(num, data))
