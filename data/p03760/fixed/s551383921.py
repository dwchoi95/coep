
o = list(input())
e = list(input())

len_o = len(o)
len_e = len(e)

if len_o == len_e:
    for i in range(len_o - 1):
        print(o[i], end = '')
        print(e[i], end = '')
    print(o[len_o - 1], end = '')
    print(e[len_e - 1])

else:
    for i in range(min(len_o, len_e)):
        print(o[i], end = '')
        print(e[i], end = '')
    if len_e > len_o:
        print(e[len(e) - 1])
    if len_o > len_e:
        print(o[len(o) - 1])
