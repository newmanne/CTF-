import sys
sys.path.append('.')

from api import Vector2

import random
import itertools

from PySide import QtGui, QtCore
from visibility import Wave


class Level(object):

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.blocks = QtGui.QImage('assets/map30.png')
        # self.blocks = QtGui.QImage(width, height, QtGui.QImage.Format_ARGB32)

    def randcoords(self, border = 0, snap = 1):
        return tuple(random.randrange(border/snap, (i-border)/snap) * snap for i in [self.width, self.height])

    def mirror(self, (x, y), size = 1):
        # return (self.width-x-1, self.height-y-1)
        return (self.width-x-size, y)
        
    def putBox(self, coords, size):
        for i, j in itertools.product(range(coords[0], coords[0]+size), range(coords[1], coords[1]+size)):
            self.blocks.setPixel(i, j, QtGui.qRgb(0,0,0))

    def generate(self):
        while True:
            self.base = self.randcoords(2)
            self.flag = self.randcoords(16)
            self.goal = self.randcoords(16)
            break

            self.blocks.fill(QtGui.QColor(255,255,255))
            for i in range(random.randrange(25, 100)):
                s = random.choice([2, 4])
                c = self.randcoords(snap = s)
                self.putBox(c, s)
                self.putBox(self.mirror(c, s), s)

            # Bases (5) are 32 travel units away from each other.
            # Bases (5) can't see each other at all.
            # Flag and goal separated by 32 travel units.
            # Base, flag and goal are separated by 64 travel units.
            # Flag boxes (2) don't overlap at all.
            # Goal boxes (3) are either identical or don't overlap.
            break

    @property
    def bases(self):
        return [self.base, self.mirror(self.base)]

    @property
    def goals(self):
        return [self.goal, self.mirror(self.goal)]

    @property
    def flags(self):
        return [self.flag, self.mirror(self.flag)]


class LevelGenerator(QtGui.QWidget):
    
    def __init__(self):
        super(LevelGenerator, self).__init__()
        
        self.resize(880, 500)
        self.center()
        self.setWindowTitle('Capture The Flag')
        self.show()

        self.level = Level(88, 50)
        self.level.generate()
        self.mouse = None

    def center(self):
        qr = self.frameGeometry()
        cp = QtGui.QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def keyPressEvent(self, e):
        if e.key() == QtCore.Qt.Key_Space:
            self.level.generate()
            self.update()

    def mouseMoveEvent(self, e):
        self.mouse = e.pos()
        self.update()

    def paintEvent(self, e):
        self.paint = QtGui.QPainter()
        self.paint.begin(self)
        self.drawLevel()
        self.paint.end()
        self.paint = None
        
    def drawLevel(self):
        visible = QtGui.QImage(88, 50, QtGui.QImage.Format_Mono)
        visible.fill(0)
        if self.mouse:
            w = Wave((88, 50), lambda x, y: self.level.blocks.pixel(x, y) != 4294967295, lambda x, y: visible.setPixel(x, y, 1))
            w.compute(Vector2(float(self.mouse.x())/10.0, float(self.mouse.y())/10.0))

        for i, j in itertools.product(range(88), range(50)):
            color = self.level.blocks.pixel(i, j)
            if visible.pixel(i, j) != 4278190080:
                self.drawPixel((i, j), QtGui.qRgb(192, 0, 192))
            else:
                self.drawPixel((i, j), color)

        colors = [QtGui.QColor(255,0,0), QtGui.QColor(32,32,255)]
        for i, (x, y) in enumerate(self.level.bases):
            self.drawBox((x-2, y-2), colors[i], 5, 'B')
            
        for i, (x, y) in enumerate(self.level.goals):
            self.drawBox((x-1, y-1), colors[i].darker(125), 3, 'G')

        for i, (x, y) in enumerate(self.level.flags):
            self.drawBox((x-1, y-1), colors[i].lighter(125), 3, 'F')

    def drawBox(self, (x,y), color, size, label = None):
        self.paint.setBrush(QtGui.QColor(color))
        self.paint.drawRect(x*10, y*10, 10*size, 10*size)
        
        if label is not None:
            self.paint.setPen(QtGui.QColor(0, 0, 0))
            font = QtGui.QFont('Ubuntu Mono', 16)
            font.setBold(True)
            self.setFont(font)
            self.paint.drawText(QtCore.QRect(x*10,y*10,size*10,size*10), QtCore.Qt.AlignCenter, label)

    def drawPixel(self, (x, y), color): 
        self.paint.setBrush(QtGui.QColor(color))
        self.paint.drawRect(x*10, y*10, 10, 10)
        

def main(args):
    app = QtGui.QApplication(args)
    ex = LevelGenerator()
    return app.exec_()


if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))

