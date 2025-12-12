abstract class Banner {
  protected rate_5_star: number;
  protected hard_pity: number;
  protected initial_pity: number;
  protected current_pull: number;
  protected total_pull: number;
  protected soft_pity_start: number;
  protected garentee: boolean;

  constructor(rate_5_star: number, hard_pity: number, soft_pity_start: number, initial_pity = 0) {
    this.rate_5_star = rate_5_star / 100;
    this.hard_pity = hard_pity;
    this.initial_pity = initial_pity;
    this.current_pull = initial_pity;
    this.total_pull = 0;
    this.soft_pity_start = soft_pity_start;
    this.garentee = false;
  }

  protected calc_rate(): number {
    if (this.current_pull < this.soft_pity_start) {
      return this.rate_5_star;
    }
    const soft_pity_pull = this.current_pull - this.soft_pity_start + 1;
    const ratio = Math.ceil(100 / (this.hard_pity - this.soft_pity_start + 1)) / 100;
    return this.rate_5_star + ratio * soft_pity_pull;
  }

  protected calc_proba(): boolean {
    this.current_pull += 1;
    this.total_pull += 1;
    return Math.random() <= this.calc_rate();
  }

  abstract calc_proba_when_5_star(): boolean;

  pull(): boolean {
    let result = false;
    if (this.calc_proba()) {
      this.current_pull = 0;
      result = this.calc_proba_when_5_star();
      this.garentee = !result;
    }
    return result;
  }

  init(): void {
    this.current_pull = this.initial_pity;
    this.total_pull = 0;
    this.garentee = false;
  }

  pull_until_wanted_5_star(number_of_wanted_5_stars = 1): number {
    this.init();
    let current_pull = 0;
    while (current_pull < number_of_wanted_5_stars) {
      if (this.pull()) {
        current_pull += 1;
      }
    }
    return this.total_pull;
  }

  try_pull(number_of_pulls: number, number_of_wanted_5_stars = 1): [boolean, number] {
    this.init();
    let current_pull = 0;
    for (let current_wishes_spend = 0; current_wishes_spend < number_of_pulls; current_wishes_spend++) {
      if (this.pull()) {
        current_pull += 1;
      }
      if (current_pull >= number_of_wanted_5_stars) {
        return [true, number_of_pulls - current_wishes_spend + 1];
      }
    }
    return [false, 0];
  }

  get_hard_pity(): number{
    return this.hard_pity
  }
}

class CharBanner extends Banner {
  private radiance: number;
  private initial_radiance: number;
  private global_radiance: number;

  constructor(initial_pity = 0, lose_streak = 0,rate_5_star = 0.6, hard_pity = 90, soft_pity_start = 74) {
    super(rate_5_star, hard_pity, soft_pity_start, initial_pity);
    this.radiance = Math.min(Math.max(lose_streak, 0), 4);
    this.initial_radiance = this.radiance;
    this.global_radiance = 0;
  }

  calc_proba_when_5_star(): boolean {
    if (this.garentee){
      return true;
    }
    let res = Math.random() <= 0.5;
    if (res) {
      this.radiance = 0;
      return res;
    }
    if (this.radiance === 2) {
      res = Math.random() <= 0.5;
    }
    if (this.radiance === 3) {
      res = true;
    }
    if (!res) {
      this.radiance += 1;
    }
    if (res) {
      this.global_radiance += 1;
      this.radiance = 0;
    }
    return res;
  }

  override init(): void {
    super.init();
    this.radiance = this.initial_radiance;
  }
}

class WeaponBanner extends Banner {
  constructor(initial_pity = 0, rate_5_star = 0.7, hard_pity = 77, soft_pity_start = 63) {
    super(rate_5_star, hard_pity, soft_pity_start, initial_pity);
  }

  calc_proba_when_5_star(): boolean {
    if (this.garentee){
      return true;
    }
    return Math.random() <= 0.75 && Math.random() <= 0.5;
  }
}

class CombinedBanner {
  private char_banner: CharBanner;
  private weapon_banner: WeaponBanner;

  constructor(current_lose_streak_char = 0,initial_pity_char = 0, initial_pity_weapon = 0) {
    this.char_banner = new CharBanner(initial_pity_char, current_lose_streak_char);
    this.weapon_banner = new WeaponBanner(initial_pity_weapon);
  }

  private test_number_of_pulls(
    number_of_wishes: number,
    number_of_wanted_5_stars_chars = 1,
    number_of_wanted_5_stars_weapon = 1,
    number_of_pulls = 100000
  ): boolean[] {
    const res: boolean[] = [];
    for (let i = 0; i < number_of_pulls; i++) {
      const [char_success, char_remaining] = this.char_banner.try_pull(number_of_wishes, number_of_wanted_5_stars_chars);
      if (!char_success) {
        res.push(false);
        continue;
      }
      const [weapon_success , weapon_remaining] = this.weapon_banner.try_pull(char_remaining,number_of_wanted_5_stars_weapon);
      res.push(weapon_success);
    }
    return res;
  }

  get_proba(
    number_of_wishes: number,
    number_of_wanted_5_stars_chars = 1,
    number_of_wanted_5_stars_weapon = 1,
    number_of_pulls = 100000
  ): number {
    const total_hard_pity = (this.char_banner.get_hard_pity()*2) * number_of_wanted_5_stars_chars + (this.weapon_banner.get_hard_pity()*2) * number_of_wanted_5_stars_weapon
    if (total_hard_pity < number_of_wishes){
      return 1;
    }
    const res = this.test_number_of_pulls(number_of_wishes, number_of_wanted_5_stars_chars, number_of_wanted_5_stars_weapon, number_of_pulls);
    return (res.filter(Boolean).length / res.length);
  }
}

const loose_streak_char_5_stars = 2;
const initial_pity_char = 0;
const initial_pity_weapon = 0;

const number_of_wishes = 240;
const number_of_5_stars_char = 2;
const number_of_5_stars_weapon = 0;
const number_of_pulls = 100000;
// const number_of_pulls = 1;

const combined_banner = new CombinedBanner(loose_streak_char_5_stars, initial_pity_char, initial_pity_weapon);

const res = combined_banner.get_proba(
      number_of_wishes,
      number_of_5_stars_char,
      number_of_5_stars_weapon,
      number_of_pulls
    )

console.log(`Probability of getting at least ${number_of_5_stars_char} character 5★ and ${number_of_5_stars_weapon} weapon 5★ in ${number_of_wishes} wishes: ${(res * 100).toFixed(2)}%`);