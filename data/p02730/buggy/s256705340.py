def main():
    s = input()
    s1 = s[:int((len(s)-1)/2)]
    s2 = s[int((len(s)+3)/2-1):]
    rs1 = s1[::-1]
    rs2 = s2[::-1]

    if s1 == rs1 and s2 == rs2:
        print("Yes")
    else:
        print("No")
    
    return
    
main()
