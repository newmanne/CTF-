import math

def distance(vector1, vector2):
    return (vector1-vector2).length();

def distanceBetween(bot1, bot2):
    return distance(bot1.position, bot2.position)

def inVOF( bot, enemy, FOVangle):
        facing = bot.facingDirection
        neededDir = enemy.position - bot.position
        cosTheta = (facing.x*neededDir.x + facing.y*neededDir.y)/(facing.length()*neededDir.length())
        if cosTheta >1:      
            cosTheta = 1
        if math.acos(cosTheta) <= FOVangle/2:
            return True
        return False
    
def inArea(position, target):
    if distance(position, target) < 2:
        return True
    return False

def inAreaParameter(position, target, vicinity):
    if distance(position, target) < vicinity:
        return True
    return False

def chunks(seq, size):
    """ Yield successive n-sized chunks from l.
    """
    newseq = []
    splitsize = 1.0/size*len(seq)
    for i in range(size):
            newseq.append(seq[int(round(i*splitsize)):int(round((i+1)*splitsize))])
    return newseq