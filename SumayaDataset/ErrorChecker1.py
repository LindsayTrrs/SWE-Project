number = int(input("Enter a number: "))

try:
    print(1 / number)
except ZeroDivisionError:
    print("Can't divide by zero")
