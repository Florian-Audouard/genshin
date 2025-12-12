from abc import ABC, abstractmethod
import random
from tqdm import tqdm
import math
import statistics


class Banner(ABC):
    def __init__(self, rate_5_star, hard_pity, soft_pity_start):
        self.rate_5_star = rate_5_star / 100
        self.hard_pity = hard_pity
        self.current_pull = 0
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

    def print_proba(self):
        self.current_pull = 0
        for i in range(1, self.hard_pity + 1):
            self.current_pull = i
            print(f"Pull {i}: {self.calc_rate() * 100:.2f}% chance for 5-star item.")
        self.current_pull = 0

    @abstractmethod
    def pull(self):
        pass

    def init(self):
        self.current_pull = 0
        self.total_pull = 0
        self.garentee = False

    def pull_until_wanted_5_star(self):
        self.init()
        while not self.pull():
            pass
        return self.total_pull

    def test_banner(self, number_of_pulls=10000):
        res = []
        for _ in tqdm(range(number_of_pulls), desc="Pulling for 5-star item"):
            res.append(self.pull_until_wanted_5_star())
        avg = statistics.mean(res)
        median = statistics.median(res)
        max_pulls = max(res)
        min_pulls = min(res)
        print(
            f"average number of pulls to get a 5-star: {avg} , max: {max_pulls}, min: {min_pulls}, median: {median}"
        )
        return avg, median, max_pulls


class CharBanner(Banner):
    def __init__(self, rate_5_star=0.6, hard_pity=90, soft_pity_start=74):
        super().__init__(rate_5_star, hard_pity, soft_pity_start)
        self.garentee = False

    def pull(self):
        result = False
        if self.calc_proba():
            self.current_pull = 0
            result = self.garentee or random.random() <= 0.5
            self.garentee = not result
            self.current_pull = 0
        return result


class WeaponBanner(Banner):
    def __init__(self, rate_5_star=0.7, hard_pity=77, soft_pity_start=63):
        super().__init__(rate_5_star, hard_pity, soft_pity_start)
        self.fate_points = 0

    def pull(self):
        if self.calc_proba():
            self.current_pull = 0
            banner_weapon = self.garentee or random.random() <= 0.75
            self.garentee = not banner_weapon
            if not banner_weapon:
                self.current_pull = 0
                return False
            good_weapon = random.random() <= 0.5
            if good_weapon or self.fate_points >= 2:
                self.fate_points = 0
                return True
            self.fate_points += 1
            return False
        return False

    def init(self):
        super().init()
        self.fate_points = 0

    def pull_until_wanted_5_star(self):
        self.init()
        while not self.pull():
            pass
        return self.total_pull


def main():
    char_banner = CharBanner()
    number_of_pulls = 100000
    char_banner.test_banner(number_of_pulls)

    weapon_banner = WeaponBanner()
    weapon_banner.test_banner(number_of_pulls)


def main2():
    char_banner = CharBanner()
    char_banner.print_proba()

    weapon_banner = WeaponBanner()
    weapon_banner.print_proba()


def main3():
    weapon_banner = WeaponBanner()
    print(weapon_banner.pull_until_wanted_5_star())


if __name__ == "__main__":
    main2()
