import sys

def I(): return int(sys.stdin.readline().rstrip())
def LI():return list(map(int,sys.stdin.readline().rstrip().split()))
def LS():return list(sys.stdin.readline().rstrip().split())

def main():
  X,Y = LI()[:]
  

  if ((Y-2*X) % 2) == 0:
    a = (Y-2*X) / 2
    if a<=X:
      print('Yes')
      exit()
  
  print('No')

if __name__ == '__main__':
	main()
