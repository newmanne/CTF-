import util

def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    reverse = dict((value, key) for key, value in enums.iteritems())
    enums['reverse_mapping'] = reverse
    return type('Enum', (), enums)

class Bot():
    states = enum('DEFENDING_HORIZONTAL', 'DEFENDING_VERTICAL', 'ATTACKING')
    
    def __init__(self, bot):
        self.bot = bot
        self.enemy_targeting = None
        self.state = None
        self.attacking_partner = None
        self.how_much_danger = 0
        
    def getClosestEnemy(self):
        return reduce(lambda x,y: x if util.distanceBetween(x, self.bot.position) <= util.distanceBetween(y, self.bot.position) else y, self.bot.visibleEnemies)