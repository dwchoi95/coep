
def main():
    s = input()
    if len(s) % 2  == 0:
        print("No")
        return
    N = int(len(s))
    
    s1 = s[0:int((N-1)/2)]
    s2 = s[int((N+1)/2):N]

    
    

    i = 0
    j = int((N - 1) / 2) - 1
    
    while True:
        if i > j:
            break
        if s1[i] != s1[j]:
            print("No")
            return
        i += 1
        j -= 1

    i = 0
    j = int((N - 1) / 2) - 1
    while True:
        if i > j:
            break
        if s2[i] != s2[j]:
            
            return
        i += 1
        j -= 1


    print("Yes")
    return


if __name__ == '__main__':
    main()