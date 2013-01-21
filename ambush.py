import sys
import math
import random
import itertools
from visibility import Wave

from api import Commander, commands, gameinfo
from api.vector2 import Vector2


from PySide import QtGui, QtCore
import networkx as nx

from visualizer import VisualizerApplication

SCALE = 10

def square(x): return x*x


class AmbushCommander(Commander):
    """
        Display current state and predictions on the screen in a PyQT application.
    """
    MODE_VISIBILITY = 0
    MODE_TRAVELLING = 1
    MAP_WIDTH = 88
    MAP_HEIGHT = 50

    def drawPreWorld(self, visualizer):
       furthest = max([self.distances[n] for n in itertools.chain(*self.terrain) if n])
       brightest = max([self.visibilities.pixel(i,j) for i, j in itertools.product(range(88), range(50))])

        # visible = QtGui.QImage(88, 50, QtGui.QImage.Format_ARGB32)
        # visible.fill(0)

       for i, j in itertools.product(range(88), range(50)):
            n = self.terrain[j][i]
            if n:
                if self.mode == self.MODE_TRAVELLING:
                    d = self.distances[n] * 255.0 / furthest
                if self.mode == self.MODE_VISIBILITY:
                    d = self.visibilities.pixel(i,j) * 255 / brightest
            else:
                d = 32
            visualizer.drawPixel((i, j), QtGui.qRgb(d,d,d))

    def drawPreBots(self, visualizer):
        best = max(self.scores.values())

        for p, o in self.ambushes:
            score = self.scores[(p,o)]
            g = int(score * 255.0 / best)
            visualizer.drawCircle(p, QtGui.qRgb(g,g,0), 0.5)
            visualizer.drawRay(p, o, QtGui.qRgb(g,g,0))

    def keyPressed(self, e):
        if e.key() == QtCore.Qt.Key_Space:
            self.mode = 1 - self.mode

    def initialize(self):
        self.assault = False
        self.attacker = None

        self.mode = self.MODE_VISIBILITY
        self.visualizer = VisualizerApplication(self)

        self.visualizer.setDrawHookPreWorld(self.drawPreWorld)
        self.visualizer.setDrawHookPreBots(self.drawPreBots)
        self.visualizer.setKeyboardHook(self.keyPressed)

        self.makeGraph()

        self.graph.add_node("enemy_base")
        start, finish = self.level.botSpawnAreas[self.game.enemyTeam.name]
        for i, j in itertools.product(range(int(start.x), int(finish.x)), range(int(start.y), int(finish.y))):
            self.graph.add_edge("enemy_base", self.terrain[j][i], weight = 1.0)


        self.graph.add_node("base")
        start, finish = self.level.botSpawnAreas[self.game.team.name]
        for i, j in itertools.product(range(int(start.x), int(finish.x)), range(int(start.y), int(finish.y))):
            self.graph.add_edge("base", self.terrain[j][i],weight = 1.0)


        self.node_EnemyFlagIndex = self.getNodeIndex(self.game.team.flag.position)
        self.node_EnemyScoreIndex = self.getNodeIndex(self.game.enemyTeam.flagScoreLocation)

        # self.node_Bases = self.graph.add_vertex()
        # e = self.graph.add_edge(self.node_Bases, self.node_MyBase)
        # e = self.graph.add_edge(self.node_Bases, self.node_EnemyBase)

        vb2f = nx.shortest_path(self.graph, source="enemy_base", target=self.node_EnemyFlagIndex)
        vf2s = nx.shortest_path(self.graph, source=self.node_EnemyFlagIndex, target=self.node_EnemyScoreIndex, weight = "length")
        vb2s = nx.shortest_path(self.graph, source="enemy_base", target=self.node_EnemyScoreIndex, weight = "length")

        self.visibilities = QtGui.QImage(88, 50, QtGui.QImage.Format_ARGB32)
        self.visibilities.fill(0)
        path = vb2f+vf2s[:-8] # Trim last 8m off the path to the flag, too late by then.
        for vf, vt in zip(path[0:], path[1:]) + zip(vb2s[0:], vb2s[1:]):
            if "position" not in self.graph.node[vf]:
                continue
            position = Vector2(*self.graph.node[vf]["position"])
            if "position" not in self.graph.node[vt]:
                continue
            next_position = Vector2(*self.graph.node[vt]["position"])
            if position == next_position:
                continue
            orientation = (next_position - position).normalized()

            def visible(p):
                delta = (p-position)
                l = delta.length()
                if l > 15.0:
                    return False
                if l <= 0.0:
                    return True
                delta /= l
                return orientation.dotProduct(delta) >= 0.5

            cells = []
            w = Wave((88, 50), lambda x, y: self.level.blockHeights[x][y] > 1, lambda x, y: cells.append((x,y)))
            w.compute(position)

            for x, y in [c for c in cells if visible(Vector2(c[0]+0.5, c[1]+0.5))]:
                self.visibilities.setPixel(x, y, self.visibilities.pixel(x, y)+1)

        starte, finishe = self.level.botSpawnAreas[self.game.enemyTeam.name]
        startf, finishf = self.level.botSpawnAreas[self.game.team.name]
        points = [self.game.team.flag.position, self.game.enemyTeam.flag.position,
                  self.game.team.flagScoreLocation, self.game.enemyTeam.flagScoreLocation] * 4
        for i, j in list(itertools.product(range(int(starte.x), int(finishe.x)), range(int(starte.y), int(finishe.y)))) \
                    + list(itertools.product(range(int(startf.x), int(finishf.x)), range(int(startf.y), int(finishf.y)))) \
                    + [(int(p.x), int(p.y)) for p in points]:
            n = self.terrain[j][i]
            if not n: continue

            position = Vector2(*self.graph.node[n]["position"])
            def visible(p):
                delta = (p-position)
                l = delta.length()
                return l <= 15.0

            cells = []
            w = Wave((88, 50), lambda x, y: self.level.blockHeights[x][y] > 1, lambda x, y: cells.append((x,y)))
            w.compute(position)

            for x, y in [c for c in cells if visible(Vector2(c[0]+0.5, c[1]+0.5))]:
                self.visibilities.setPixel(x, y, self.visibilities.pixel(x, y)+1)


        self.node_EnemyPath = "enemy_path"
        self.graph.add_node(self.node_EnemyPath)
        for vertex in vb2f+vf2s[:-8]: # Trim path by 8m also.
            self.graph.add_edge(self.node_EnemyPath, vertex, weight = 0.0)

        self.distances = nx.single_source_shortest_path_length(self.graph, self.node_EnemyPath)
        self.queue = {}
        self.index = 0
        self.calculateAmbushes()

    def findBestOrientation(self, position, callback):
        cells = []
        w = Wave((88, 50), lambda x, y: self.level.blockHeights[x][y] > 1, lambda x, y: cells.append((x,y)))
        w.compute(position)

        def visible(p, o):
            delta = (p-position)
            l = delta.length()
            if l > 15.0:
                return False
            if l <= 0.0:
                return True
            delta /= l
            return o.dotProduct(delta) > 0.9659

        orientation = None
        best = 0.0, 0

        for i in range(32):
            angle = math.pi * float(i) / 16.0
            o = Vector2(math.cos(angle), math.sin(angle))

            total = [0.0, 0]
            for x, y in [c for c in cells if visible(Vector2(c[0]+0.5, c[1]+0.5), o)]:
                total[0] += callback(x,y)
                total[1] += 1

            if orientation is None or total[0] > best[0]:
                best = tuple(total)
                orientation = o

        return orientation, best

    def calculateAmbushes(self):
        blocks = self.level.blockHeights
        def blocked(x, y): return blocks[x][y] > 1

        print "Finding hiding locations..."
        hiding = []
        for i, j in itertools.product(range(1, self.MAP_WIDTH-1), range(1, self.MAP_HEIGHT-1)):
            if blocked(i, j): continue
            if not blocked(i-1, j) and not blocked(i+1, j) and not blocked(i, j-1) and not blocked(i, j+1):
                continue

            if self.visibilities.pixel(i, j) < 5 and \
               self.getDistance(i, j) < 15.0 and self.getDistance(i, j) >= 2.0:
                hiding.append(Vector2(float(i)+0.5, float(j)+0.5))

        print "Filtering as ambush points..."
        results = []
        for p in hiding:
            p = random.choice(hiding)
            o, s = self.findBestOrientation(p, lambda x, y: 25.0-square(self.getDistance(x, y)))
            if s[1] > 4:
                results.append((s, (p,o)))
        results.sort(key=lambda r: -r[0][0])

        self.ambushes = [r for _, r in results]
        self.scores = {r: s[1] for s, r in results}

    def getDistance(self, x, y):
        n = self.terrain[y][x]
        if n:
            return self.distances[n]
        else:
            return 0.0

    def tick(self):
        if self.game.enemyTeam.flag.carrier != self.attacker:
            self.attacker = self.game.enemyTeam.flag.carrier
            if self.attacker:
                self.issue(commands.Charge, self.attacker, self.game.team.flagScoreLocation)

        dead = 0
        for e in self.game.enemyTeam.members:
            dead += int(e.health == 0 and e.position is not None)

        # If everyone is dead and we haven't captured the flag yet, assault!
        if dead == len(self.game.enemyTeam.members):
            if not self.assault and self.attacker is None:
                # TODO: Find nearest bot only... rest move forward.
                for bot in self.game.bots_alive:
                    self.issue(commands.Charge, bot, self.game.enemyTeam.flag.position)

            self.assault = True
        else:
            self.assault = False

        for e in self.game.match.combatEvents[self.index:]:
            if e.type != gameinfo.MatchCombatEvent.TYPE_RESPAWN:
                continue
            if e.subject in self.queue:
                del self.queue[e.subject] 
        self.index = len(self.game.match.combatEvents)

        for bot in self.game.bots_available:
            if bot == self.attacker:
                continue

            if self.game.team.members.index(bot) == 0:
               self.issue(commands.Attack, bot, self.game.enemyTeam.flag.position)
               continue

            if bot in self.queue:
                p, o = self.queue[bot]
                if (bot.position-p).length() < 1.0:
                    self.issue(commands.Defend, bot, o)
                    continue
            else:
                p, o = random.choice(self.ambushes)
                self.queue[bot] = (p, o)

            self.issue(commands.Charge, bot, p)

        self.visualizer.tick()

    def shutdown(self):
        self.visualizer.quit()
        del self.visualizer

    def makeGraph(self):
        blocks = self.level.blockHeights
        width, height = len(blocks), len(blocks[0])

        g = nx.Graph(directed=False, map_height = height, map_width = width)

        self.terrain = []
        for j in range(0, height):
            row = []
            for i in range(0,width):
                if blocks[i][j] == 0:
                    g.add_node(i+j*width, position = (float(i)+0.5, float(j)+0.5))
                    row.append(i+j*width)
                else:
                    row.append(None)
            self.terrain.append(row)

        for i, j in itertools.product(range(0, width), range(0, height)):
            p = self.terrain[j][i]
            if not p:
                continue

            q, r, s = None, None, None
            if i < width-1:
                q = self.terrain[j][i+1]
                if q:
                    e = g.add_edge(p, q, length = 1.0)

            if j < height-1:
                r = self.terrain[j+1][i]
                if r:
                    e = g.add_edge(p, r, length = 1.0)

            if i < width-1 and j < height-1:
                s = self.terrain[j+1][i+1]
                if s:
                    e = g.add_edge(p, s, length = 1.41)

            if q and r:
                e = g.add_edge(q, r, length = 1.41)


        self.graph = g

    def getNodeIndex(self, position):
        i = int(position.x)
        j = int(position.y)
        width = self.graph.graph["map_width"]
        return i+j*width

