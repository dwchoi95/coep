
strings=[input() for string in range(2)]
string=strings[0]
num=int(strings[1])
result=""
for i in range(len(string)):
    if i% num==0:
        result=result+string[i]
    i=i+1
print(result)