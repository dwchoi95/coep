import itertools
import copy

def main():
    N,K = map(int, input().split())
    a_list = [int(e) for e in input().split()]

    
    
    
    

    ans = 10**100

    l = [i for i in range(0,N)]

    for v in itertools.combinations(l,K): 
        copied_a_list = copy.copy(a_list)
        
        v = set(v)
        left_max = copied_a_list[0]-1
        temp_ans = 0
        
        for i in range(N): 
            if i in v:
                temp_ans += max(0,left_max+1 - copied_a_list[i])
                copied_a_list[i] = left_max+1
            
            if copied_a_list[i] > left_max:
                left_max = copied_a_list[i]
        
        print(v,copied_a_list,temp_ans)
        
        if temp_ans < ans:
            ans = temp_ans
            
    print(ans)

main()