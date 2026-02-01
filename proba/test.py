import random

def wish_roll(counter5, counter4):
    _rate5 = 0.006   # 0.6%
    _rate4 = 0.051   # 5.1%

    _pity5 = 73      # 5★ pity starts after 73 attempts
    _pity4 = 8       # 4★ pity starts after 8 attempts

    x = random.random()  # between 0.0 and 1.0

    prob5 = _rate5 + max(0, (counter5 - _pity5) * 10 * _rate5)
    prob4 = _rate4 + max(0, (counter4 - _pity4) * 10 * _rate4)

    if x < prob5:
        result = "5star"
        counter5 = 1
        counter4 += 1

    elif x < prob5 + prob4:
        result = "4star"
        counter5 += 1
        counter4 = 1

    else:
        result = "3star"
        counter5 += 1
        counter4 += 1

    return result, counter5, counter4



if __name__ == "__main__":
    print("Starting test of wish_roll function...")
    counter5 = 0
    counter4 = 0
    results = {"5star": 0, "4star": 0, "3star": 0}