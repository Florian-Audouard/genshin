// Final verification of the fixed pack.ts behavior.
// We reproduce Banner/CharBanner/WeaponBanner/CombinedBanner here because
// pack.ts is tied to the Coda SDK and doesn't export the classes.
// The logic below is a faithful mirror of the fixed pack.ts classes.

abstract class Banner {
  protected rate_5_star: number;
  protected rate_4_star: number;
  protected hard_pity: number;
  protected current_pull_5_star: number;
  protected current_pull_4_star: number;
  public total_pull = 0;
  public paid_pull = 0;
  protected soft_pity_start: number;
  public starglitter: number;
  protected initial_starglitter: number;
  protected guarantee_5_star = false;
  protected guarantee_4_star = false;
  protected current_wanted_5_star = 0;

  constructor(r5: number, hp: number, sps: number, r4: number, isg = 0) {
    this.rate_5_star = r5 / 100;
    this.rate_4_star = r4 / 100;
    this.hard_pity = hp;
    this.current_pull_5_star = 0;
    this.current_pull_4_star = 0;
    this.soft_pity_start = sps;
    this.starglitter = isg;
    this.initial_starglitter = isg;
  }

  protected add_starglitter(star: number): void {
    if (star === 3) return;
    if (star === 4) this.starglitter += 2;
    if (star === 5) this.starglitter += 10;
  }

  protected calc_rate_5_star() {
    if (this.current_pull_5_star < this.soft_pity_start) return this.rate_5_star;
    const sp = this.current_pull_5_star - this.soft_pity_start + 1;
    const r = Math.ceil(100 / (this.hard_pity - this.soft_pity_start + 1)) / 100;
    return this.rate_5_star + r * sp;
  }
  protected calc_proba_5_star() { this.current_pull_5_star += 1; return Math.random() <= this.calc_rate_5_star(); }
  protected calc_proba_4_star() { this.current_pull_4_star += 1; if (this.current_pull_4_star >= 10) return true; return Math.random() <= this.rate_4_star; }
  abstract calc_proba_when_5_star(): boolean;
  protected count_pull(us: boolean) { this.total_pull += 1; if (!us) { this.paid_pull += 1; return; } if (this.starglitter >= 5) { this.starglitter -= 5; return; } this.paid_pull += 1; }

  pull(us: boolean): number {
    this.count_pull(us);
    if (this.calc_proba_5_star()) {
      this.current_pull_5_star = 0;
      const r = this.calc_proba_when_5_star();
      this.guarantee_5_star = !r;
      if (r) return 5.5;
      return 5;
    }
    if (this.calc_proba_4_star()) {
      this.current_pull_4_star = 0;
      const r = Math.random() <= 0.5 || this.guarantee_4_star;
      this.guarantee_4_star = !r;
      if (r) return 4.5;
      return 4;
    }
    return 3;
  }

  // Fixed: does NOT reset starglitter
  init() {
    this.current_pull_5_star = 0; this.current_pull_4_star = 0;
    this.total_pull = 0; this.paid_pull = 0;
    this.guarantee_5_star = false; this.guarantee_4_star = false;
    this.current_wanted_5_star = 0;
  }

  // Fixed: while loop on paid_pull, returns remaining paid
  try_pull(n: number, k: number, us = false): [boolean, number] {
    this.init();
    while (this.paid_pull < n) {
      if (this.pull(us) === 5.5) {
        k--;
        if (k === 0) return [true, n - this.paid_pull];
      }
    }
    return [false, 0];
  }
}

class W extends Banner {
  constructor() { super(0.7, 77, 63, 6.0, 0); }
  calc_proba_when_5_star() { if (this.guarantee_5_star) return true; return Math.random() <= 0.75 && Math.random() <= 0.5; }
  protected override add_starglitter(star: number): void {
    super.add_starglitter(star);
    if (star === 5.5) this.starglitter += 10;
    if (star === 4.5) this.starglitter += 2;
  }
}

class C extends Banner {
  constructor() { super(0.6, 90, 74, 5.1, 0); }
  calc_proba_when_5_star() { if (this.guarantee_5_star) return true; return Math.random() <= 0.5; }
}

class Comb {
  cb: C; wb: W; isg: number;
  constructor(isg = 0) { this.cb = new C(); this.wb = new W(); this.isg = isg; }
  get_proba(nw: number, cN: number, wN: number, sims = 100000, us = false) {
    if (cN * 180 + wN * 154 < nw) return 2;
    let s = 0;
    for (let i = 0; i < sims; i++) {
      let carry = this.isg; let budget = nw;
      if (wN > 0) {
        this.wb.starglitter = this.isg;
        const [ok, rem] = this.wb.try_pull(nw, wN, us);
        if (!ok) continue;
        carry = this.wb.starglitter;
        budget = rem;
      }
      if (cN > 0) {
        this.cb.starglitter = carry;
        const [ok] = this.cb.try_pull(budget, cN, us);
        if (ok) s++;
      } else s++;
    }
    return s / sims;
  }
}

function T(label: string, v: number, check?: (v: number) => string | null) {
  const status = check ? (check(v) ?? "PASS") : "OK";
  console.log(`  ${label} = ${typeof v === "number" ? v.toFixed(4) : v}  [${status}]`);
  return v;
}

const SIMS = 100_000;

console.log("=== Primary equivalence (A vs B) in single-banner regime (no sentinel) ===");
// Use 150 wishes so sentinel doesn't fire (150 < 334).
// Test: does 150 wish + 0sg use=true behave similarly to
// 150 - N wishes + 5*N sg (where 5*N starglitter converts to N wishes)?
// Use smaller budgets where we get a real probability.

console.log("\n=== Starglitter conversion test (char only, 1 C0) ===");
// Char only: 90w vs 70w + 100sg (100sg = 20 wishes -> 90 effective)
const A1 = T("A1: 90w, 0sg, use=true ", new Comb(0).get_proba(90, 1, 0, SIMS, true));
const B1 = T("B1: 70w, 100sg, use=true", new Comb(100).get_proba(70, 1, 0, SIMS, true));
const d1 = Math.abs(A1 - B1);
console.log(`  |A1 - B1| = ${d1.toFixed(4)}  ${d1 < 0.02 ? "PASS" : "FAIL"}`);

console.log("\n=== Starglitter conversion test (char only, larger) ===");
const A2 = T("A2: 120w, 0sg, use=true ", new Comb(0).get_proba(120, 1, 0, SIMS, true));
const B2 = T("B2: 100w, 100sg, use=true", new Comb(100).get_proba(100, 1, 0, SIMS, true));
const d2 = Math.abs(A2 - B2);
console.log(`  |A2 - B2| = ${d2.toFixed(4)}  ${d2 < 0.02 ? "PASS" : "FAIL"}`);

console.log("\n=== Combined banner: 150w C1W1 vs 100w + 250sg ===");
const A3 = T("A3: 150w, 0sg, use=true  ", new Comb(0).get_proba(150, 1, 1, SIMS, true));
const B3 = T("B3: 100w, 250sg, use=true", new Comb(250).get_proba(100, 1, 1, SIMS, true));
const d3 = Math.abs(A3 - B3);
console.log(`  |A3 - B3| = ${d3.toFixed(4)}  ${d3 < 0.02 ? "PASS" : "FAIL"}`);

console.log("\n=== Regression: 80 wishes char-only should be ~50% ===");
T("80w C1W0 use=false", new Comb(0).get_proba(80, 1, 0, SIMS, false),
  v => (v > 0.45 && v < 0.55) ? null : `OUT OF ~50% RANGE`);

console.log("\n=== Starglitter does NOT affect result when use=false ===");
const X1 = T("120w C1W0 0sg   use=false", new Comb(0).get_proba(120, 1, 0, SIMS, false));
const X2 = T("120w C1W0 999sg use=false", new Comb(999).get_proba(120, 1, 0, SIMS, false));
const dx = Math.abs(X1 - X2);
console.log(`  |X1 - X2| = ${dx.toFixed(4)}  ${dx < 0.01 ? "PASS" : "FAIL"}`);

console.log("\n=== Sentinel ===");
T("335w C1W1 => 2", new Comb(0).get_proba(335, 1, 1, 1000, false),
  v => v === 2 ? null : "EXPECTED 2");
T("334w C1W1 => not 2", new Comb(0).get_proba(334, 1, 1, SIMS, false),
  v => v !== 2 ? null : "UNEXPECTED SENTINEL");

console.log("\nDone.");
