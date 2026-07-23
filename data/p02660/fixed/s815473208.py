
import math
N = int(input())
Nsyo = N
count = 0
div = 2
divcount = 0
divlist = []
while N > 1 and div <= math.sqrt(Nsyo)+1:
    if N%div == 0:
        while N%div == 0:
            N = N/div
            divcount = divcount+1
        divlist.append(divcount)
        divcount = 0
    else:
        pass
    div = div + 1
div = 1
divcount = 0
for i in divlist:
    while i >= div:
        i = i-div
        divcount = divcount + 1
        div = div + 1
        
    count = count +divcount
    divcount = 0
    div = 1
if N > math.sqrt(Nsyo):
    count = count + 1
print(count)