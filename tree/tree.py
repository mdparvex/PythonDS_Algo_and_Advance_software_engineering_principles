class TreeNode():
    def __init__(self, data):
        self.data = data
        self.childern = []
        self.parant = None

    def add_child(self, child):
        self.parant=self
        self.childern.append(child)
    def print_tree(self):
        print(self.data) 
        if self.childern:
            for child in self.childern:
                child.print_tree()

def build_tree():
    root = TreeNode("Electronics")

    laptop = TreeNode("Laptop")
    laptop.add_child(TreeNode("mac"))
    laptop.add_child(TreeNode("Thikpad"))
    laptop.add_child(TreeNode("Lenovo"))
    
    
    phone = TreeNode("phone") 
    phone.add_child(TreeNode("Iphone")) 
    phone.add_child(TreeNode("samsung")) 
    phone.add_child(TreeNode("googlePixel")) 
    
    
    tv = TreeNode("TV") 
    tv.add_child(TreeNode("LG")) 
    tv.add_child(TreeNode("samsung")) 
    tv.add_child(TreeNode("sony")) 

    root.add_child(laptop)
    root.add_child(phone)
    root.add_child(tv)

    return root

if __name__== '__main__':
    root = build_tree()
    root.print_tree()
     
