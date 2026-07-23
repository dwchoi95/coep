[N,M]=list(map(int,input().split()
              )
          )
XYZ=[[int(i) for i in input().split()] for i in range(N)] 
maxabs=0

for i in range(8):
  pm=list(map(int,format(i, 'b')))
  pm=[0,]*(3-len(pm))+pm
  pm=[(-1)**item for item in pm]
  
  newXYZ=sorted([[item[0]*pm[0],item[1]*pm[1],item[2]*pm[2]] for item in XYZ],
                key=lambda x:sum(x),
                reverse=True)
  
  maxabs=max(sum([abs(sum([newXYZ[m][j] for m in range(M)]
                             )
                         ) for j in range(3)
                 ]
                ),
             maxabs
            )


print(maxabs)
