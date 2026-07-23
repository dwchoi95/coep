n=int(input())
a={}
temp=n
for i in range(2,int(n**0.5)+1):
    if temp % i ==0:
        count=0
        while temp % (i**(count+1)) ==0:
            count+=1
        temp= temp/(i**count)
        a[i]=count

sum=0
for i in a:
    jisu= a[i]
    temp= int((2*jisu)**0.5)-1
    if temp*(temp+1) > 2*jisu:
        sum+= temp-1
    elif (temp+1)*(temp+2) > 2*jisu:
        sum+= temp
    elif (temp+2)*(temp+3)> 2*jisu:
        sum+= temp+1
print(sum)   
        