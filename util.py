import math
from api import Vector2

def getVonNeumannNeighborhood(cell, cells, r): # where cell is a tuple, cells is a 2D list, and r is the range
    newCells = [] # list of tuples
    for x, cx in enumerate(cells):
        for y, cy in enumerate(cx):
            if abs(x - cell[0]) + abs(y - cell[1]) <= r:
                newCells.append((x,y))
    return newCells

def numAdjCoverBlocks(cell, blockHeights):
    adjCells = getVonNeumannNeighborhood(cell, blockHeights, 1)
    numWallCells = 0
    for aCell in adjCells:
        aCellX, aCellY = aCell
        if blockHeights[aCellX][aCellY] >= 2:
            numWallCells += 1
    return numWallCells

def numAdjMapWalls(cell, mapSize):
    adjWalls = 0
    x,y = cell
    width,height = mapSize

    if x == 0 or x == width-1:
        adjWalls += 1
    if y == 0 or y == height-1:
        adjWalls += 1
    return adjWalls

# prioritize cells that have cover from their spawn
def numAdjCoverBlocksWeighted(cell, cmdr):
    adjCells = getVonNeumannNeighborhood(cell, cmdr.level.blockHeights, 1)
    # get distances of cells to their spawn
    spawnPoint = cmdr.game.enemyTeam.botSpawnArea[0]
    cellDistances = [distance(spawnPoint, Vector2(x[0] + .5, x[1] + .5)) for x in adjCells]
    cellDistData = sorted(zip(adjCells, cellDistances), key = lambda x: x[1], reverse = True)
    
    wallScore = 0
    for i, aCell in enumerate([x[0] for x in cellDistData]):
        if not aCell == cell:
            aCellX, aCellY = aCell
            if cmdr.level.blockHeights[aCellX][aCellY] >= 2:
                wallScore += i
    return wallScore

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
    
def inArea(position, target, vicinity=2):
    if distance(position, target) < vicinity:
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

def areUniqueAngles(a, b, closeness=15):
    """Given 2 vector2s, do they differ by more than closeness degrees?"""
    return False if math.degrees(math.acos(min(a.normalized().dotProduct(b.normalized()), 1))) < closeness else True