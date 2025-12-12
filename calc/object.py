class Object:
    def __init__(self, name,effect_bonus={},passive_bonus={}):
        self.name = name
        self.effect_bonus = effect_bonus
        self.passive_bonus = passive_bonus
    
    def add_effect_bonus(self, character):
        for key, bonus in self.effect_bonus.items():
            if hasattr(character, key):
                setattr(character, key, getattr(character, key) + bonus)