a=input()
b=input()
c=input()
dic={'a':[_ for _ in a],'b':[_ for _ in b],'c':[_ for _ in c]}
char='a'
print(dic)
for i in range(len(a)+len(b)+len(c)):
    if len(dic[char]) == 0:
        break
    char = dic[char].pop(0)
print(char.upper())