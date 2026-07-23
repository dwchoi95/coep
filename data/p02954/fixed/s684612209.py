import sys

sys.setrecursionlimit(10 ** 7)

S = list(input())

is_hole = [None for _ in S]
is_s = [None for _ in S]

s_1 = None
for i, s in enumerate(S):
    if s_1 == 'R' and s == 'L':
        is_hole[i - 1] = 'R'
        is_hole[i] = 'L'
    if s_1 == 'L' and s == 'R':
        is_s[i] = 'S'  
    s_1 = s

result = [0 for _ in S]
mem_R = 0  
mem_Rx = 0  
mem_L = 0

def find_next_mem_R(i):
    while i < len(S):
        if is_hole[i] == 'R':
            return i
        i += 1

mem_Rx = find_next_mem_R(0)

for i, s in enumerate(S):
    if is_s[i] == 'S':
        result[mem_Rx] = mem_R
        result[mem_Rx + 1] = mem_L
        mem_R = 0
        mem_L = 0
        mem_Rx = find_next_mem_R(i)

    if s == 'R':
        x_diff_for_R = mem_Rx - i
        if x_diff_for_R % 2 == 0:
            mem_R += 1
        else:
            mem_L += 1
    else:
        x_diff_for_R = i - mem_Rx
        if x_diff_for_R % 2 == 0:
            mem_R += 1
        else:
            mem_L += 1

result[mem_Rx] = mem_R
result[mem_Rx + 1] = mem_L

result_str = [str(i) for i in result]
print(' '.join(result_str))
