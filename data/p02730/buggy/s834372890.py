
def isReverse(s):
    p1 = 0
    p2 = len(s) - 1
    flag = True
    while p1 <= p2:
        if s[p1] != s[p2]:
            flag = False
        p1 += 1
        p2 += -1
    return flag
if __name__ == "__main__":
    s = input()
    s1 = s[:int((len(s) - 1) / 2)]
    s2 = s[int((len(s) + 1) / 2):]
    print(s, s1, s2)
    print(isReverse(s), isReverse(s1), isReverse(s2))
    if isReverse(s) and isReverse(s1) and isReverse(s2):
        print("Yes")
    else:
        print("No")