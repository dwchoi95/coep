if __name__ == '__main__':
  str = input()
  strList = [c for c in str]
  strList.append('e')
  strLength = len(strList)
  rLength = 0
  lLength = 0
  i = 0
  changePoint = 0

  child = [0 for i in range(strLength)]

  c = 'R'
  
  while(c != 'e'):
    c = strList[i]
    while(c == 'R'):
      i += 1
      c = strList[i]
      rLength += 1
    
    changePoint = i
    
    while(c == 'L'):
      i += 1
      c = strList[i]
      lLength += 1

    rRight = int(rLength/2)
    rLeft = rLength - rRight

    lLeft = int(lLength/2)
    lRight = lLength - lLeft

    child[changePoint-1] += rLeft + lLeft
    child[changePoint] += rRight + lRight

    rLength = 0
    lLength = 0
  
  for numOfChild in child:
    print(numOfChild, end="")
    print(' ', end="")