// pack.ts
import * as coda from "@codahq/packs-sdk";
export const pack = coda.newPack();

// ---------- Internal Classes (not exported) ----------

abstract class Banner {
  protected rate_5_star: number;
  protected rate_4_star: number;
  protected hard_pity: number;
  protected current_pull_5_star: number;
  protected current_pull_4_star: number;
  public total_pull: number;
  protected paid_pull: number;
  protected soft_pity_start: number;
  protected starglitter: number;
  protected initial_starglitter: number;
  protected guarantee_5_star: boolean;
  protected guarantee_4_star: boolean;
  protected current_wanted_5_star: number;

  constructor(
    rate_5_star: number,
    hard_pity: number,
    soft_pity_start: number,
    rate_4_star: number,
    initial_starglitter = 0
  ) {
    this.rate_5_star = rate_5_star / 100;
    this.rate_4_star = rate_4_star / 100;
    this.hard_pity = hard_pity;
    this.current_pull_5_star = 0;
    this.current_pull_4_star = 0;
    this.total_pull = 0;
    this.paid_pull = 0;
    this.soft_pity_start = soft_pity_start;
    this.starglitter = initial_starglitter;
    this.initial_starglitter = initial_starglitter;
    this.guarantee_5_star = false;
    this.guarantee_4_star = false;
    this.current_wanted_5_star = 0;
  }

  protected add_starglitter(star: number): void {
    if (star === 3) return;
    if (star === 4) {
      this.starglitter += 2;
    }
    if (star === 5) {
      this.starglitter += 10;
    }
  }

  protected calc_rate_5_star(): number {
    if (this.current_pull_5_star < this.soft_pity_start) {
      return this.rate_5_star;
    }
    const soft_pity_pull = this.current_pull_5_star - this.soft_pity_start + 1;
    const ratio = Math.ceil(100 / (this.hard_pity - this.soft_pity_start + 1)) / 100;
    return this.rate_5_star + ratio * soft_pity_pull;
  }

  protected calc_proba_5_star(): boolean {
    this.current_pull_5_star += 1;
    return Math.random() <= this.calc_rate_5_star();
  }

  protected calc_proba_4_star(): boolean {
    this.current_pull_4_star += 1;
    if (this.current_pull_4_star >= 10) {
      return true;
    }
    return Math.random() <= this.rate_4_star;
  }

  abstract calc_proba_when_5_star(): boolean;

  protected count_pull(use_starglitter: boolean): void {
    this.total_pull += 1;
    if (!use_starglitter) {
      this.paid_pull += 1;
      return;
    }
    if (this.starglitter >= 5) {
      this.starglitter -= 5;
      return;
    }
    this.paid_pull += 1;
  }

  pull(use_starglitter: boolean): number {
    this.count_pull(use_starglitter);
    
    if (this.calc_proba_5_star()) {
      this.current_pull_5_star = 0;
      // calc_proba_when_5_star already handles guarantee_5_star internally.
      const result = this.calc_proba_when_5_star();
      this.guarantee_5_star = !result;
      if (result) {
        return 5.5;
      }
      return 5;
    }
    
    if (this.calc_proba_4_star()) {
      this.current_pull_4_star = 0;
      const result = Math.random() <= 0.5 || this.guarantee_4_star;
      this.guarantee_4_star = !result;
      if (result) {
        return 4.5;
      }
      return 4;
    }
    
    return 3;
  }

  // NOTE: init() intentionally does NOT reset `starglitter`.
  // Starglitter lifecycle is owned by the caller (e.g. CombinedBanner).
  // Callers MUST invoke set_starglitter(...) before each try_pull(...) run.
  init(): void {
    this.current_pull_5_star = 0;
    this.current_pull_4_star = 0;
    this.total_pull = 0;   // total pulls performed (paid + starglitter-funded)
    this.paid_pull = 0;    // pulls paid from the wish budget (NOT funded by starglitter)
    this.guarantee_5_star = false;
    this.guarantee_4_star = false;
    this.current_wanted_5_star = 0;
  }

  pull_until_wanted_5_star(number_of_wanted_5_stars: number, use_starglitter: boolean): number {
    this.init();
    while (this.current_wanted_5_star < number_of_wanted_5_stars) {
      const star = this.pull(use_starglitter);
      this.add_starglitter(star);
      if (star === 5.5) {
        this.current_wanted_5_star += 1;
      }
    }
    return this.paid_pull;
  }

  // `number_of_pulls` is the budget of PAID wishes (from the wallet).
  // Starglitter-funded pulls do NOT consume this budget.
  // Returns [success, remaining_paid_wishes].
  try_pull(number_of_pulls: number, number_of_5_stars: number, use_starglitter = false): [boolean, number] {
    this.init();
    while (this.paid_pull < number_of_pulls) {
      if (this.pull(use_starglitter) === 5.5) {
        number_of_5_stars--;
        if (number_of_5_stars === 0) {
          return [true, number_of_pulls - this.paid_pull];
        }
      }
    }
    return [false, 0];
  }

  get_hard_pity(): number {
    return this.hard_pity;
  }

  get_starglitter(): number {
    return this.starglitter;
  }

  set_starglitter(amount: number): void {
    this.starglitter = amount;
  }
}

class CharBanner extends Banner {
  private radiance: number;
  private initial_radiance: number;
  private initial_pity_5_star: number;
  private global_radiance: number;
  private count_4_star: number[];
  private last_4_star: number;
  private number_of_C0: number;

  constructor(
    rate_5_star = 0.6,
    hard_pity = 90,
    soft_pity_start = 74,
    number_of_C0 = 1,
    rate_4_star = 5.1,
    initial_radiance = 0,
    initial_starglitter = 0,
    initial_pity = 0
  ) {
    super(rate_5_star, hard_pity, soft_pity_start, rate_4_star, initial_starglitter);
    this.radiance = initial_radiance;
    this.initial_radiance = initial_radiance;
    this.initial_pity_5_star = initial_pity;
    this.current_pull_5_star = initial_pity;
    this.global_radiance = 0;
    this.count_4_star = [0, 0, 0];
    this.last_4_star = -1;
    this.number_of_C0 = number_of_C0;
  }

  protected override add_starglitter(star: number): void {
    super.add_starglitter(star);
    if (star === 5.5 && this.current_wanted_5_star > this.number_of_C0) {
      this.starglitter += 10;
    }
    if (star === 4.5) {
      const current_count = this.count_4_star[this.last_4_star];
      if (current_count > 7) {
        this.starglitter += 5;
      } else if (current_count > 1) {
        this.starglitter += 2;
      }
    }
  }

  override pull(use_starglitter: boolean): number {
    const star = super.pull(use_starglitter);
    if (star === 5.5 && this.current_wanted_5_star + 1 < this.number_of_C0) {
      this.count_4_star = [0, 0, 0];
      this.last_4_star = -1;
    }
    if (star === 4.5) {
      this.last_4_star = Math.floor(Math.random() * 3);
      this.count_4_star[this.last_4_star] += 1;
    }
    return star;
  }

  calc_proba_when_5_star(): boolean {
    if (this.guarantee_5_star) {
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
    this.current_pull_5_star = this.initial_pity_5_star;
    this.count_4_star = [0, 0, 0];
  }
}

class WeaponBanner extends Banner {
  private initial_pity_5_star: number;

  constructor(
    rate_5_star = 0.7,
    hard_pity = 77,
    soft_pity_start = 63,
    rate_4_star = 6.0,
    initial_starglitter = 0,
    initial_pity = 0
  ) {
    super(rate_5_star, hard_pity, soft_pity_start, rate_4_star, initial_starglitter);
    this.initial_pity_5_star = initial_pity;
    this.current_pull_5_star = initial_pity;
  }

  calc_proba_when_5_star(): boolean {
    if (this.guarantee_5_star) {
      return true;
    }
    return Math.random() <= 0.75 && Math.random() <= 0.5;
  }

  protected override add_starglitter(star: number): void {
    super.add_starglitter(star);
    if (star === 5.5) {
      this.starglitter += 10;
    }
    if (star === 4.5) {
      this.starglitter += 2;
    }
  }

  override init(): void {
    super.init();
    this.current_pull_5_star = this.initial_pity_5_star;
  }
}

class CombinedBanner {
  private char_banner: CharBanner;
  private weapon_banner: WeaponBanner;
  private initial_starglitter: number;
  private current_simulation: {
    total_pull: number[];
    paid_pull: number[];
  };

  constructor(
    initial_starglitter = 0,
    initial_radiance = 0,
    number_of_C0 = 0,
    initial_pity_char = 0,
    initial_pity_weapon = 0
  ) {
    this.char_banner = new CharBanner(0.6, 90, 74, number_of_C0, 5.1, initial_radiance, 0, initial_pity_char);
    this.weapon_banner = new WeaponBanner(0.7, 77, 63, 6.0, 0, initial_pity_weapon);
    this.initial_starglitter = initial_starglitter;
    this.current_simulation = {
      total_pull: [],
      paid_pull: [],
    };
  }
  get_proba(
    number_of_wishes: number,
    number_of_5_stars_char: number,
    number_of_5_stars_weapon: number,
    number_of_simulations = 100000,
    use_starglitter = false
  ): number {
    // Deterministic upper bound sentinel:
    //   Char banner: 90 hard pity + 90 guaranteed next = 180 wishes guarantee a wanted 5-star.
    //   Weapon banner: 77 hard pity * 2 = 154 wishes effectively guarantee a wanted 5-star
    //     (under the current "effectively guaranteed after a loss" model).
    // If the requested wish budget is below the deterministic threshold, returning 2
    // signals "result is NOT from simulation but from a theoretical 100% cap".
    if (number_of_5_stars_char * 180 + number_of_5_stars_weapon * 154 < number_of_wishes) {
      return 2;
    }
    this.current_simulation = { total_pull: [], paid_pull: [] };
    let success_count = 0;

    for (let i = 0; i < number_of_simulations; i++) {
      // Weapon stage runs first so leftover starglitter (initial + drops) carries to char.
      let carry_starglitter = this.initial_starglitter;
      let char_budget = number_of_wishes;

      if (number_of_5_stars_weapon > 0) {
        // set_starglitter MUST be called BEFORE try_pull (init() no longer resets sg).
        this.weapon_banner.set_starglitter(this.initial_starglitter);
        const [weapon_success, weapon_remaining_paid] = this.weapon_banner.try_pull(
          number_of_wishes,
          number_of_5_stars_weapon,
          use_starglitter
        );
        if (!weapon_success) {
          continue;
        }
        carry_starglitter = this.weapon_banner.get_starglitter();
        char_budget = weapon_remaining_paid;
      }

      if (number_of_5_stars_char > 0) {
        this.char_banner.set_starglitter(carry_starglitter);
        const [char_success] = this.char_banner.try_pull(
          char_budget,
          number_of_5_stars_char,
          use_starglitter
        );
        if (char_success) {
          success_count++;
        }
      } else {
        success_count++;
      }
    }

    return success_count / number_of_simulations;
  }
}

// ---------- Exposed Formulas ----------

pack.addFormula({
  name: "GetProba",
  description: "Get probability (%) of obtaining desired 5-star characters and weapons within a number of wishes.",
  parameters: [
    coda.makeParameter({
      type: coda.ParameterType.Number,
      name: "number_of_wishes",
      description: "Number of wishes available",
    }),
    coda.makeParameter({
      type: coda.ParameterType.Number,
      name: "number_of_5_stars_char",
      description: "Desired 5-star characters",
    }),
    coda.makeParameter({
      type: coda.ParameterType.Number,
      name: "number_of_5_stars_weapon",
      description: "Desired 5-star weapons",
    }),
    coda.makeParameter({
      type: coda.ParameterType.Number,
      name: "initial_pity_char",
      description: "Initial pity for character banner (0-89)",
      optional: true,
    }),
    coda.makeParameter({
      type: coda.ParameterType.Number,
      name: "initial_pity_weapon",
      description: "Initial pity for weapon banner (0-76)",
      optional: true,
    }),
    coda.makeParameter({
      type: coda.ParameterType.Number,
      name: "initial_starglitter",
      description: "Starting starglitter amount",
      optional: true,
    }),
    coda.makeParameter({
      type: coda.ParameterType.Number,
      name: "initial_radiance",
      description: "Initial lose streak (0-3)",
      optional: true,
    }),
    coda.makeParameter({
      type: coda.ParameterType.Number,
      name: "number_of_C0",
      description: "Number of C0 copies needed",
      optional: true,
    }),
    coda.makeParameter({
      type: coda.ParameterType.Boolean,
      name: "use_starglitter",
      description: "Use starglitter for pulls",
      optional: true,
    }),
    coda.makeParameter({
      type: coda.ParameterType.Number,
      name: "number_of_simulations",
      description: "Number of Monte Carlo simulations",
      optional: true,
    }),
  ],
  resultType: coda.ValueType.Number,
  execute: async function ([
    number_of_wishes,
    number_of_5_stars_char,
    number_of_5_stars_weapon,
    initial_pity_char = 0,
    initial_pity_weapon = 0,
    initial_starglitter = 0,
    initial_radiance = 0,
    number_of_C0 = 0,
    use_starglitter = false,
    number_of_simulations = 100000,
  ]: [number, number, number, number?, number?, number?, number?, number?, boolean?, number?]): Promise<number> {
    const combined_banner = new CombinedBanner(
      initial_starglitter,
      initial_radiance,
      number_of_C0,
      initial_pity_char,
      initial_pity_weapon
    );
    return combined_banner.get_proba(
      number_of_wishes,
      number_of_5_stars_char,
      number_of_5_stars_weapon,
      number_of_simulations,
      use_starglitter
    );
  },
});
