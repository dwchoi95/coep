def animal(x,y):
    if x*4==y or x*2==y:
        return "Yes"
    for i in range(1,x+1):
        if ((x-i)*4 + i*2) == y:
            return "Yes"
    return "No"

if __name__ == "__main__":
    x,y = map(int,input().split())
    print(animal(x,y))