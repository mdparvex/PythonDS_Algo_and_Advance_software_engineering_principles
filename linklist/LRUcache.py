from collections import OrderedDict
class LRUcache:
    def __init__(self, capacity):
        self.capacity = capacity
        self.cache = OrderedDict()

    def get(self, key):
        if key not in self.cache:
            return -1
        self.cache.move_to_end(key)
        return self.cache.get(key)
    
    def put(self, key, val):
        if key in self.cache:
            self.cache[key] = val
            self.cache.move_to_end(key)
        else:
            if len(self.cache)>=self.capacity:
                self.cache.popitem(last=False)
            self.cache[key] = val

cache = LRUcache(5)
cache.put(1,1)
print(cache.get(1))
cache.put(2,2)
cache.put(3,3)
cache.put(4,4)
print(cache.get(2))
cache.put(5,5)
cache.put(6,6)
print(cache.get(6))

