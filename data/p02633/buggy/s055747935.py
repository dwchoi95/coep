
import math
 
def Strider():
 
    NumA = int(input())
 
    count = 360/NumA
    
    NumB = 1
    
    while (count == 0):
        NumB = NumB + 1
        count = 360*NumB/NumA
    
    print(int(count))
 
if __name__ == '__main__':
    Strider()