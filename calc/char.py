class Character:
    STAT_KEYS = [
        "base_pv",
        "base_def",
        "base_atk",
        "pv_percentage",
        "def_percentage",
        "atk_percentage",
        "elemental_mastery",
        "crit_rate",
        "crit_damage",
        "pyro_damage",
        "cryo_damage",
        "hydro_damage",
        "electro_damage",
        "anemo_damage",
        "geo_damage",
        "dendro_damage",
        "physical_damage",
        "healing_bonus",
        "healing_bonus_recieved",
        "damage_bonus",
    ]

    def __init__(
        self,
        name,
        level=90,
        base_stats={},
        artifacts=[],
        weapon=None,
        passive_bonuses=[],
        elemental_type=None,
        stats_scalling=None,
        passive_effects=[],
        elemental_skill=None,
        burst=None,
        normal_attack=None,
        charged_attack=None,
    ):
        for key in base_stats:
            if key not in self.STAT_KEYS:
                raise ValueError(f"Invalid stat key: {key}")
        self.name = name
        self.level = level
        self.weapon = weapon
        self.artifacts = artifacts
        self.passive_bonuses = passive_bonuses
        self.elemental_type = elemental_type
        self.stats_scalling = stats_scalling
        self.passive_effects = passive_effects
        self.elemental_skill = elemental_skill
        self.burst = burst
        self.normal_attack = normal_attack
        self.charged_attack = charged_attack
        self.tmp_stats = {}
        for key in self.STAT_KEYS:
            setattr(self, key, base_stats.get(key, 0))
            getter = self._make_getter(key)
            setattr(self.__class__, key, property(getter))

    def _make_getter(self, key):
        def getter():
            return getattr(self, key) + self.tmp_stats.get(key, 0)
        return getter
