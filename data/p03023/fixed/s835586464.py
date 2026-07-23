


from collections import defaultdict
import sys
import math
from datetime import datetime

def sol(n):
    
    
    
    
    

    return int((180 - (360 / n)) * n)


do_submit = True


def input_parse(input_str):
    lines = [x.strip() for x in input_str.split("\n") if x.strip()]
    parsed_lines = [list(map(str, line.split())) for line in lines]
    print(parsed_lines)
    n = int(parsed_lines[0][0])
    
    
    
    return n


if not do_submit:
    n = input_parse()
    print(sol(n))

    n = input_parse()
    print(sol(n))

else:
    
    
    
    n = int(input().strip())
    
    print(sol(n))

