from util import distanceBetween
from api import Vector2

def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    reverse = dict((value, key) for key, value in enums.iteritems())
    enums['reverse_mapping'] = reverse
    return type('Enum', (), enums)

class Bot():
    states = enum('DEFENDING_HORIZONTAL', 'DEFENDING_VERTICAL', 'ATTACKING')
    
    def __init__(self, bot_info, enemy_targeting = None, role = None, attacking_partner = None, how_much_danger = 0, defending_direction = Vector2(1, 0)):
        self.bot_info = bot_info
        self.enemy_targeting = enemy_targeting
        self.role = role
        self.attacking_partner = attacking_partner
        self.how_much_danger = 0
        self.defending_direction = defending_direction
        
    def getClosestEnemy(self):
        return min(self.bot_info.visibleEnemies, key=lambda enemy: distanceBetween(enemy.position, self.bot_info.position))
        
    def __getattr__(self, attr):
        # see if this object has attr
        # NOTE do not use hasattr, it goes into
        # infinite recurrsion
        if attr in self.__dict__:
            # this object has it
            return getattr(self, attr)
        # proxy to the wrapped object
        return getattr(self.bot_info, attr)
