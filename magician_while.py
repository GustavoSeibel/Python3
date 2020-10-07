secret_number = 777

print(
"""
+================================+
| Welcome to my game, muggle!    |
| Enter an integer number        |
| and guess what number I've     |
| picked for you.                |
| So, what is the secret number? |
+================================+
""")

player_number = int(input("Insert a number:"))

while player_number != secret_number:
    print ("Ha ha! You're stuck in my loop!")
    player_number = int(input("Insert a number:"))
if player_number == secret_number:
    print("Well done, muggle! You are free now.")
        