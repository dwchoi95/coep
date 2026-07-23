
def main():
    s = input()
    sr = s[::-1]

    N = int(len(s))
    s1 = s[:int((N-1)/2)]
    s1r = s1[::-1]
    s2 = s[int((N+1)/2):]
    s2r = s2[::-1]

    
    
    
    
    

    for i in range(len(s)-1):
        if s[i] != sr[i]:
            print("No")
            return

    for i in range(len(s1)-1):
        if s1[i] != s1r[i]:
            print("No")
            return

    for i in range(len(s2)-1):
        if s2[i] != s2[i]:
            print("No")
            return

    print("Yes")


if __name__ == '__main__':
    main()