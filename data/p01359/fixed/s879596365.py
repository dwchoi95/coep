inputnum,outputnum = (int(n) for n in input().split(' '))
while True:
    data = {}
    for i in range(inputnum):
        temp = input().split(' ')
        data[temp[0]] = [int(temp[2]) - int(temp[1]) + 1,int(temp[2])]
    for o in range(outputnum):
        targ = int(input())
        for k,v in data.items():
            if v[0] <= targ  <= v[1]:
                print(k + ' ' + str(targ-v[0] + 1))
                break
        else:
            print("Unknown")
    inputnum,outputnum = (int(n) for n in input().split(' '))
    if inputnum == outputnum == 0:
        break