def character(n,k,s):
    res = s[:k-1] + s[k-1].lower() + s[k:]
    return res
n,k = map(int, input().split())
s = input()
print(character(n,k,s))