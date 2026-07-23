
strings=[input() for string in range(2)]
string=strings[0]
num=int(strings[1])
i=0
check=True

while check:
    s=string[i:i+num]
    if len(s)<num:
        check=False
    print(s)
    i=i+num