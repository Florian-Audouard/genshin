# 810538
# 14668 no reaction, no bonus from teammates

def calc_res(res):
    if res < 0:
        return 1 - (res / 2)
    elif res < 0.75:
        return 1 - res
    else:
        return 1 / (4 * res + 1)



# Maviuka stats
level = 90
base_attack = 359 + 510 # Maviuka base attack + weapon attack
elemental_mastery = 352
crit_rate = 0.54 + 0.4 # Base crit rate + crit rate from artifacts
crit_damage = 2.306
elemental_damage = 0.466 # global elemental damage bonus
bonus_damage = 0.15 + 0.4 + (0.08*5) # artifact bonus + passive bonus (200 fp) + weapon passive bonus
attack_percentage = 0.087 + 0.25  # artifact attack % + pyro resonance bonus 
attack_flat = 18 + 311 # artifact


# try modif

# enemy stats
enemy_level = 103
enemy_resistance = 0.1


# team buffs

# natlan's buffs
attack_percentage += 0.3 # natlan's passive

# Bennett's buffs
attack_flat += 1.01 * 799  * 1.2 # Bennett's ATK buff and C1
attack_percentage += 0.2 # Noble Obligation artifact set bonus

# iansan's buffs
# attack_flat += 690

# xilonen's buffs
enemy_resistance -= 0.36
elemental_damage += 0.35

# citlali's buffs
elemental_damage += 0.4 # scrolls artifact set bonus
attack_percentage += 0.48 # ttds weapon passive
enemy_resistance -= 0.2 # citlali's debuff

# cleanup stats
crit_rate = max(min(crit_rate,1.0), 0)

crit = True
# Skill multipliers
skill_multiplier = 8.006 + (0.029*200) # Base skill multiplier + bonus from 200 fp


final_attack = (base_attack) * (1 + attack_percentage) + attack_flat


base_damage = final_attack * skill_multiplier
melt = True
dammage_multiplier = 1.0 + (elemental_damage + bonus_damage)
avg_crit_multiplier = 1 + (crit_rate * crit_damage)
true_crit_multiplier = 1 + (crit_damage * int(crit))

enemy_def_mult = (level + 100) / ((level + 100) + (enemy_level + 100) * (1 - 0.0)) * (1 - 0) # no def reduc, no def ignore
base_resistance = enemy_resistance - 0.0 # no resistance shred
res_mult = calc_res(base_resistance)

amplification_reaction = 2 * (1 + 0 + (2.78* elemental_mastery) / (elemental_mastery + 1400)) # no reaction bonus
if not melt:
    amplification_reaction = 1

total_damage_avg = base_damage * avg_crit_multiplier * enemy_def_mult * res_mult * dammage_multiplier * amplification_reaction
total_damage = base_damage * true_crit_multiplier * enemy_def_mult * res_mult * dammage_multiplier * amplification_reaction
print("Total Damage:", total_damage)
print("inspect formula")
print("Base Damage:", base_damage)
print("Crit Multiplier:", true_crit_multiplier)
print("Enemy Def Multiplier:", enemy_def_mult)
print("Resistance Multiplier:", res_mult)
print("Damage Multiplier:", dammage_multiplier)
print("Amplification Reaction:", amplification_reaction)
