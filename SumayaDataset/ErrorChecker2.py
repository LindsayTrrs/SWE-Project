try:
    number = int(input("Enter a number: "))
    print(1 / number)
except ZeroDivisionError:
    print("Can't divide by zero")
