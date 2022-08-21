class university:
    def __init__(self, uniname, location):
        self.uniname = uniname
        self.location = location
    def getAll(self):
        print(f'university name : {self.uniname} and location : {self.location}')
class dept(university):
    def __init__(self, uniname, location, deptname):
        self.deptname = deptname
        university.__init__(self, uniname, location)

    def getdeptname(self):
        print(f'dept. name is {self.deptname}')

class student(dept):
    def __init__(self,uniname, location,deptname, name, id):
        self.name = name
        self.id= id
        dept.__init__(self, uniname,location,deptname)
    def getstudent(self):
        print(f'name is :{self.name} and id:{self.id}')

stu = student('NSU','Dhaka', 'ECE', 'mamun', 1713062042)
stu.getstudent()
stu.getdeptname()
stu.getAll()
