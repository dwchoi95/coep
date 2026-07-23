def animal(x,y):
    if x*4 >= y:
        return "Yes"
    return "No"

if __name__ == "__main__":
    x,y = map(int,input().split())
    print(animal(x,y))