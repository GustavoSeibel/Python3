income = float(input("Enter the annual income: "))

tax = 0.0

if income <= 85528:
    tax = income * 0.18 - 556.2
    if tax<0: tax=0
else:
    tax = (income - 85528)*.32 + 14839.02
tax = round(tax, 0)
print("The tax is:", tax, "thalers")