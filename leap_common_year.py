year = int(input("Enter a year: "))

if year <1582:
    print("Not within the Gregorian calendar period")
elif year % 4 != 0:
    print("common year")
elif year % 100 != 0:
    print("leap year")
elif year % 400 !=0:
    print("common year")
else:
    print("leap year")
