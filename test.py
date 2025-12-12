# --------------------- list initializations -----------------------

p_C0_pity_list = []
p_C0_list = []
p_w_pity_list = []
p_w_list = []

# --------------------- construct drop chance lists ------------------------



def calc_chance_char(a):
    if a>90:
        return 0
    if a>73:
        return (a-73)*0.06+0.006
    if a==90:
        return 1
    return 0.006

def p_char(a, pity=0):
    if a+pity>90:
        return 0
    prod = 1
    for x in range(pity, a+pity):
        prod = prod*(1-calc_chance_char(x))
    return calc_chance_char(a + pity)*prod


def calc_chance_weap(a):
    if a>77:
        return 0
    if a>62:
        return (a-62)*0.07+0.007
    if a==77:
        return 1
    return 0.007


def p_weap(a, pity=0):
    if a+pity>77:
        return 0
    prod = 1
    for x in range(pity, a+pity):
        prod = prod*(1-calc_chance_weap(x))
    return calc_chance_weap(a + pity)*prod

def p_combine(f_list, g_list, a):
    values = []
    for x in range(a+1):
        chance = 0
        for b in range(x):
            chance+=f_list[b]*g_list[x-b]
        values.append(chance)
    return values


def p_C0(a, pity=0):
    """Probability of getting a featured 5★ (C0) exactly on pull 'a'."""
    chance = p_char(a, pity) / 2  # 50% chance it's featured
    for b in range(a):
        chance += p_char(b, pity) * p_char(a - b) / 2
    return chance


def p_R1(a, pity=0):
    """Probability of getting a featured 5★ weapon (R1) exactly on pull 'a'."""
    # Using the ratios from test2.py
    value = p_weap(a, pity) * 3/8  # 3/8 chance for featured weapon
    for b in range(a):
        # 17/64 ratio for getting featured after one non-featured
        value += p_weap(b, pity) * p_weap(a-b) * 17/64
        for c in range(b):
            # 23/64 ratio for getting featured after two non-featured
            value += p_weap(c, pity) * p_weap(b-c) * p_weap(a-b) * 23/64
    return value


def cumulative_prob(f_list, wishes):
    """Cumulative probability up to 'wishes' pulls."""
    return sum(f_list[:wishes + 1])


def get_proba(number_of_wishes, number_of_5_stars_char=0, initial_pity_char=0, guarantee_char=False, number_of_5_stars_weapon=0, initial_pity_weapon=0, guarantee_weapon=False):
    """
    Calculate the probability of obtaining a certain number of featured 5★ characters and/or weapons
    within a given number of wishes, starting from some pity and optionally with a guarantee.

    Parameters
    ----------
    number_of_wishes : int
        Total number of wishes you want to simulate.
    number_of_5_stars_char : int
        Number of featured 5★ characters you want (C0=1, C1=2, etc.).
    initial_pity_char : int, optional
        Pity count on the character banner at the start. Default = 0.
    guarantee_char : bool, optional
        Whether your next 5★ character is guaranteed featured. Default = False.
    number_of_5_stars_weapon : int
        Number of featured 5★ weapons you want (R1=1, R2=2, etc.).
    initial_pity_weapon : int, optional
        Pity count on the weapon banner at the start. Default = 0.
    guarantee_weapon : bool, optional
        Whether your next 5★ weapon is guaranteed featured. Default = False.

    Returns
    -------
    float
        Probability (0-1) of achieving the goal.
    """
    # ------------------- helper functions -------------------




 
    # ------------------- setup -------------------

    max_wishes = number_of_wishes
    char_fct_lists = []
    weapon_fct_lists = []
    
    # Character calculations
    if number_of_5_stars_char > 0:
        
        # choose starting distribution depending on guarantee
        if guarantee_char:
            p_pity_list = [p_char(i, initial_pity_char) for i in range(max_wishes + 1)]
            char_fct_lists = [p_pity_list]
        else:
            p_C0_pity_list = [p_C0(i, initial_pity_char) for i in range(max_wishes + 1)]
            char_fct_lists = [p_C0_pity_list]

        # Setup p_C0_list for subsequent calculations
        if initial_pity_char == 0:
            p_C0_list = char_fct_lists[0] if not guarantee_char else [p_C0(i) for i in range(max_wishes + 1)]
        else:
            p_C0_list = [p_C0(i) for i in range(max_wishes + 1)]

        # combine distributions to reach desired constellation
        for _ in range(number_of_5_stars_char - 1):
            char_fct_lists.append(p_combine(p_C0_list, char_fct_lists[-1], max_wishes))

    # Weapon calculations
    if number_of_5_stars_weapon > 0:
        # choose starting distribution depending on guarantee
        if guarantee_weapon:
            p_weapon_pity_list = [p_weap(i, initial_pity_weapon) for i in range(max_wishes + 1)]
            weapon_fct_lists = [p_weapon_pity_list]
        else:
            p_R1_pity_list = [p_R1(i, initial_pity_weapon) for i in range(max_wishes + 1)]
            weapon_fct_lists = [p_R1_pity_list]

        # Setup p_R1_list for subsequent calculations
        if initial_pity_weapon == 0:
            p_R1_list = weapon_fct_lists[0] if not guarantee_weapon else [p_R1(i) for i in range(max_wishes + 1)]
        else:
            p_R1_list = [p_R1(i) for i in range(max_wishes + 1)]

        # combine distributions to reach desired refinement
        for _ in range(number_of_5_stars_weapon - 1):
            weapon_fct_lists.append(p_combine(p_R1_list, weapon_fct_lists[-1], max_wishes))

    # Return appropriate probability
    if number_of_5_stars_char > 0 and number_of_5_stars_weapon > 0:
        # Both character and weapon - return combined probability
        combined_list = p_combine(char_fct_lists[-1], weapon_fct_lists[-1], max_wishes)
        return cumulative_prob(combined_list, number_of_wishes)
    elif number_of_5_stars_char > 0:
        return cumulative_prob(char_fct_lists[-1], number_of_wishes)
    elif number_of_5_stars_weapon > 0:
        return cumulative_prob(weapon_fct_lists[-1], number_of_wishes)
    else:
        return 1.0  # No requirements means 100% success





if __name__ == "__main__":
    # Example usage
    NUMBER_OF_WISHES = 150
    NUMBER_OF_5_STARS_CHAR = 1
    INITIAL_PITY_CHAR = 0
    GUARANTEE_CHARACTER = False
    NUMBER_OF_5_STARS_WEAPON = 1  # Not used in this function
    INITIAL_PITY_WEAPON = 0
    GUARANTEE_WEAPON = False  # Not used in this function

    probability = get_proba(
        number_of_wishes=NUMBER_OF_WISHES,
        number_of_5_stars_char=NUMBER_OF_5_STARS_CHAR,
        initial_pity_char=INITIAL_PITY_CHAR,
        guarantee_char=GUARANTEE_CHARACTER,
        number_of_5_stars_weapon=NUMBER_OF_5_STARS_WEAPON,
        initial_pity_weapon=INITIAL_PITY_WEAPON,
        guarantee_weapon=GUARANTEE_WEAPON
    )

    print(f"Probability of getting at least {NUMBER_OF_5_STARS_CHAR} featured 5★ characters in {NUMBER_OF_WISHES} wishes: {probability:.2%}")