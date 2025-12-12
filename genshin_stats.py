from abc import ABC, abstractmethod
import random
from tqdm import tqdm
import math

class Banner(ABC):
    def __init__(self, rate_5_star, hard_pity, soft_pity_start, initial_pity=0):
        self.rate_5_star = rate_5_star / 100
        self.hard_pity = hard_pity
        self.initial_pity = initial_pity
        self.current_pull = initial_pity
        self.total_pull = 0
        self.soft_pity_start = soft_pity_start
        self.garentee = False

    def calc_rate(self):

        if self.current_pull < self.soft_pity_start:
            return self.rate_5_star
        soft_pity_pull = self.current_pull - self.soft_pity_start + 1
        ratio = math.ceil(100 / (self.hard_pity - self.soft_pity_start + 1)) / 100
        return self.rate_5_star + ratio * soft_pity_pull

    def calc_proba(self):
        self.current_pull += 1
        self.total_pull += 1
        res = random.random() <= self.calc_rate()
        return res

    def get_proba(self):
        self.current_pull = 0
        res = []
        for i in range(1, self.hard_pity + 1):
            self.current_pull = i
            res.append(self.calc_rate() * 100)
        self.current_pull = 0
        return res

    @abstractmethod
    def calc_proba_when_5_star(self):
        pass

    def pull(self):
        result = False
        if self.calc_proba():
            self.current_pull = 0
            result = self.calc_proba_when_5_star() or self.garentee
            self.garentee = not result
        return result

    def init(self):
        self.current_pull = self.initial_pity
        self.total_pull = 0
        self.garentee = False

    def pull_until_wanted_5_star(self, number_of_wanted_5_stars=1):
        self.init()
        current_pull = 0
        while current_pull < number_of_wanted_5_stars:
            if self.pull():
                current_pull += 1
        return self.total_pull

    def try_pull(self, number_of_pulls, number_of_wanted_5_stars=1):
        self.init()
        current_pull = 0
        for current_wishes_spend in range(number_of_pulls):
            if self.pull():
                current_pull += 1
            if current_pull >= number_of_wanted_5_stars:
                return True , number_of_pulls - current_wishes_spend + 1
        return False,0

    def test_banner_garentee(self, number_of_pulls=10000, number_of_wanted_5_stars=1):
        res = []
        for _ in tqdm(range(number_of_pulls), desc="Pulling for 5-star item"):
            res.append(self.pull_until_wanted_5_star(number_of_wanted_5_stars))
        return res
    
    def test_number_of_pulls(self,number_of_wishes, number_of_wanted_5_stars=1, number_of_pulls=100_000):
        res = []
        for _ in tqdm(range(number_of_pulls), desc="Pulling for 5-star item"):
            res.append(self.try_pull(number_of_wishes, number_of_wanted_5_stars)[0])
        return res

class CharBanner(Banner):
    def __init__(self, rate_5_star=0.6, hard_pity=90, soft_pity_start=74, initial_pity=0):
        super().__init__(rate_5_star, hard_pity, soft_pity_start, initial_pity)
        self.radiance = 0
        self.global_radiance = 0

    def calc_proba_when_5_star(self):
        res = random.random() <= 0.5
        if res == True:
            self.radiance = 0
            return res
        if self.radiance == 2:
            res = random.random() <= 0.5
        if self.radiance == 3:
            res = True
        self.radiance += 1 if not res else 0
        self.global_radiance += 1 if res else 0
        return res

    def init(self):
        super().init()
        self.radiance = 0


class WeaponBanner(Banner):
    def __init__(self, rate_5_star=0.7, hard_pity=77, soft_pity_start=63,initial_pity=0):
        super().__init__(rate_5_star, hard_pity, soft_pity_start,initial_pity)

    def calc_proba_when_5_star(self):
        return random.random() <= 0.75 and random.random() <= 0.5
    



class CombinedBanner:
    def __init__(self, initial_pity_char=0, initial_pity_weapon=0):
        self.char_banner = CharBanner(initial_pity=initial_pity_char)
        self.weapon_banner = WeaponBanner(initial_pity=initial_pity_weapon)

    def pull_until_wanted_5_stars(self, number_of_wanted_5_stars_chars=1, number_of_wanted_5_stars_weapons=1):
        char_pull = self.char_banner.pull_until_wanted_5_star(number_of_wanted_5_stars_chars)
        weapon_pull = self.weapon_banner.pull_until_wanted_5_star(number_of_wanted_5_stars_weapons)
        return char_pull + weapon_pull

    def test_number_of_pulls(self, number_of_wishes, number_of_wanted_5_stars=1, number_of_wanted_char_5_stars=1, number_of_pulls=100_000):
        res = []
        for _ in tqdm(range(number_of_pulls), desc="Pulling for 5-star item"):
            char_success, char_remaining = self.char_banner.try_pull(number_of_wishes, number_of_wanted_char_5_stars)
            if not char_success:
                res.append(False)
                continue
            weapon_success, _ = self.weapon_banner.try_pull(char_remaining if char_success else number_of_wishes, number_of_wanted_5_stars - number_of_wanted_char_5_stars)
            res.append(weapon_success)
        return res
    
    def get_proba(self, number_of_wishes, number_of_wanted_5_stars=1, number_of_wanted_char_5_stars=1, number_of_pulls=100_000):
        res = self.test_number_of_pulls(number_of_wishes, number_of_wanted_5_stars, number_of_wanted_char_5_stars, number_of_pulls)
        return sum(res) / len(res) * 100

def get_proba(number_of_wishes, number_of_5_stars_char, number_of_5_stars_weapon, initial_pity_char=0, initial_pity_weapon=0, number_of_pulls=100_000):
    combined_banner = CombinedBanner(initial_pity_char, initial_pity_weapon)
    return combined_banner.get_proba(number_of_wishes, number_of_5_stars_char + number_of_5_stars_weapon, number_of_5_stars_char, number_of_pulls)

import math

# per-pull probability function with soft/hard pity
def pity_prob(p0: float, tstart: int, tmax: int, pity_index: int) -> float:
    if pity_index < tstart:
        return p0
    elif pity_index >= tmax:
        return 1.0
    else:
        return p0 + (1 - p0) * ((pity_index - tstart + 1) / (tmax - tstart + 1))

# probability of at least one wanted 5★
def prob_wanted(
    C0: int, W0: int, N: int, w_c: int,
    p0_c: float, tstart_c: int, tmax_c: int, q_c: float,
    p0_w: float, tstart_w: int, tmax_w: int, q_w: float,
) -> float:
    w_w = N - w_c  # wishes spent on weapon banner

    # product for character banner
    Pno_char = 1.0
    for j in range(1, w_c + 1):
        pity_index = C0 + j
        p = pity_prob(p0_c, tstart_c, tmax_c, pity_index)
        Pno_char *= (1 - p * q_c)

    # product for weapon banner
    Pno_weap = 1.0
    for j in range(1, w_w + 1):
        pity_index = W0 + j
        p = pity_prob(p0_w, tstart_w, tmax_w, pity_index)
        Pno_weap *= (1 - p * q_w)

    return (1 - (Pno_char * Pno_weap)) * 100

# ---------------- Example usage ----------------
if __name__ == "__main__":
    # Example params (toy values, not exact Genshin)
    C0 = 60   # current pity on character banner
    W0 = 40   # current pity on weapon banner
    N = 60    # wishes available
    w_c = 40  # wishes you want to spend on character banner

    # Character banner mechanics
    p0_c, tstart_c, tmax_c = 0.006, 75, 90
    q_c = 0.5   # chance wanted if 5★ appears (e.g. 50/50 case)

    # Weapon banner mechanics
    p0_w, tstart_w, tmax_w = 0.007, 65, 80
    q_w = 0.2   # chance wanted weapon

    prob = prob_wanted(C0, W0, N, w_c,
                       p0_c, tstart_c, tmax_c, q_c,
                       p0_w, tstart_w, tmax_w, q_w)



def main_test():
    NUMBER_OF_5_STARS_CHAR = 3
    NUMBER_OF_5_STARS_WEAPON = 0
    NUMBER_OF_WISHES = 179
    INITIAL_PITY_CHAR = 1
    INITIAL_PITY_WEAPON = 0
    NUMBER_OF_PULLS = 1_000_000
    # proba = get_proba(NUMBER_OF_WISHES, NUMBER_OF_5_STARS_CHAR, NUMBER_OF_5_STARS_WEAPON, INITIAL_PITY_CHAR, INITIAL_PITY_WEAPON, NUMBER_OF_PULLS)
    proba_2 = prob_wanted(
        C0=INITIAL_PITY_CHAR,
        W0=INITIAL_PITY_WEAPON,
        N=NUMBER_OF_WISHES,
        w_c=NUMBER_OF_WISHES,
        p0_c=0.006,
        tstart_c=75,
        tmax_c=90,
        q_c=0.5,
        p0_w=0.007,
        tstart_w=65,
        tmax_w=80,
        q_w=0.35
    )
    print(f"proba {proba_2}")

if __name__ == "__main__":
    main_test()