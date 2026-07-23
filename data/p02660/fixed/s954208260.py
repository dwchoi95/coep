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
if temp !=1:
    a[temp]=1

sum=0
for i in a:
  jisu= a[i]
  temp=1
  while temp*(temp+1)/2<= jisu:
          temp+=1
  sum+= temp-1
print(sum)