def print_something(mac=None):
    print("MAC Address is:", mac
          if mac else "MAC Address not provided")
    
print_something("00:1A:2B:3C:4D:5E")
print_something()
