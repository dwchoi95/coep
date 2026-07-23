
import sys


def main(argv=sys.argv):
  a, b, c, d = map(int, input().split(' '))
  
  if a + b > c + d:
    print('Left')
  elif a + b < c + d:
    print('Right')
  else:
    print('Balanced')
    
    
  return 0


if __name__ == '__main__':
  sys.exit(main())