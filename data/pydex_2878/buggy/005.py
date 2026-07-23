# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
num = int(input())
stuData = []
sample = {'rn':000, 'code':'val', 'marks':00}

if num <= 0:
    print('Wrong Input!')
    quit()
    
for i in range(0,num) :
    stuData.append(sample.copy())
    raw = input()
    rawList = raw.split(',')
    stuData[i]['rn'] = int(rawList[0].strip())
    stuData[i]['code'] = rawList[1].strip()
    stuData[i]['marks'] = int(rawList[2].strip())

tMarks = {}
for i in range(0,num):
    tMarks[stuData[i]['rn']] = 0
    #if (i+1) <= num :
        for j in range(i+1, num):
            print('njkdsgg');
            if stuData[i]['rn'] == stuData[j]['rn'] :
                tMarks[stuData[i]['rn']] = stuData[j]['marks']+stuData[i]['marks']

print(tMarks)