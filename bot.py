from util import distanceBetween
from api import Vector2

def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    reverse = dict((value, key) for key, value in enums.iteritems())
    enums['reverse_mapping'] = reverse
    return type('Enum', (), enums)

class Bot():
    states = enum('DEFENDING_HORIZONTAL', 'DEFENDING_VERTICAL', 'ATTACKING')
    
    def __init__(self, bot_info, enemy_targeting = None, state = None, attacking_partner = None, how_much_danger = 0, defending_direction = Vector2(1, 0)):
        self.bot_info = bot_info
        self.enemy_targeting = enemy_targeting
        self.state = state
        self.attacking_partner = attacking_partner
        self.how_much_danger = 0
        self.defending_direction = defending_direction
        
    def getClosestEnemy(self):
        return min(self.bot_info.visibleEnemies, key=lambda enemy: distanceBetween(enemy.position, self.bot_info.position))
    