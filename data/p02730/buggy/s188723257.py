if __name__ == '__main__':
    a = input()
    a_len = len(a)
    
    top_s = a[:int((a_len-1)/2)]
    tail_s = a[int((a_len+3)/2)-1:]
    if top_s == ''.join(list(reversed(top_s))) and tail_s == ''.join(list(reversed(tail_s))):
        print('Yes')
    else:
        print('No')