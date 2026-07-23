

def decode_heap(target_list):
    for i, key in enumerate(target_list):
        node_index = i + 1
        parent_index = int(node_index / 2) - 1
        parent = ""
        if not parent_index < 0:
            parent = " parent key = " + str(target_list[parent_index]) + ","
            
        left_index = node_index * 2 - 1
        left = ""
        if left_index < len(target_list):
            left = " left key = {},".format(target_list[left_index])
            
        right_index = node_index * 2
        right = ""
        if right_index <  len(target_list):
            right = " right key = {},".format(target_list[right_index])

        print("node {}: key = {},{}{}{} ".format(node_index, key, parent, left, right))

        
def main():
    n_nodes = int(input())
    target_list = [int(a) for a in input().split()]
    decode_heap(target_list)
    
if __name__ == "__main__":
    main()