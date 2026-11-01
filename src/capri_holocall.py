"""Procedural holocall HUD. No assets or fonts extracted from the game.

Only painters are changed: camera/avatar playback and voice states remain shared.
Scanlines use the existing avatar tick, without extra timers or image conversions.
"""
from PySide6.QtCore import QRectF, QPointF
from PySide6.QtGui import QColor, QPainterPath, QPen
from capri_theme import selected_theme, SILVERHAND_COLORS


def hud_color(value):
    return QColor(SILVERHAND_COLORS.get(value,value) if selected_theme()=='silverhand' else value)


def paint_frame(p, width, height, anger=0.0):
    path = QPainterPath()
    for i,(x,y) in enumerate(((18,1),(width-2,1),(width-2,height-20),
                             (width-20,height-2),(2,height-2),(2,18))):
        (path.moveTo if i == 0 else path.lineTo)(x,y)
    path.closeSubpath()
    p.fillPath(path,QColor(7,15,30,242) if selected_theme()=='silverhand' else QColor(5,20,23,235))
    p.setPen(QPen(hud_color('#FF404A' if anger > .25 else '#C9515D'),1.3))
    p.drawPath(path)
    for x in (7,width-7):
        p.drawLine(QPointF(x,36),QPointF(x,90))
        p.drawLine(QPointF(x,height-90),QPointF(x,height-36))
    p.fillRect(QRectF(25,height-4,64,3),hud_color('#F56B70'))
    p.fillRect(QRectF(width-89,1,64,3),QColor('#8FB4FF') if selected_theme()=='silverhand' else hud_color('#F56B70'))


def paint_signal(p, photo, phase):
    # Caller clips to the circular portrait, keeping text outside the effect.
    p.fillRect(photo,QColor(39,94,187,47) if selected_theme()=='silverhand' else QColor(4,72,57,80))
    p.setPen(QPen(QColor(3,22,22,100),1))
    for y in range(int(photo.top()),int(photo.bottom()),4):
        p.drawLine(QPointF(photo.left(),y),QPointF(photo.right(),y))
    y=photo.top()+(phase*8)%max(1,photo.height())
    p.fillRect(QRectF(photo.left(),y,photo.width(),2),QColor(122,171,255,120) if selected_theme()=='silverhand' else QColor(131,255,205,55))


def paint_brackets(p, photo):
    rect=photo.adjusted(-7,-7,7,7)
    p.setPen(QPen(hud_color('#F56B70'),2))
    for x,y,dx,dy in ((rect.left(),rect.top(),1,1),(rect.right(),rect.top(),-1,1),
                       (rect.left(),rect.bottom(),1,-1),(rect.right(),rect.bottom(),-1,-1)):
        p.drawLine(QPointF(x,y),QPointF(x+dx*27,y))
        p.drawLine(QPointF(x,y),QPointF(x,y+dy*27))
    p.setPen(QPen(QColor(113,152,248,150) if selected_theme()=='silverhand' else QColor(104,205,186,155),1))
    p.drawEllipse(photo.adjusted(-2,-2,2,2))
    for i in range(6):
        p.fillRect(QRectF(rect.right()-35+i*6,rect.bottom()+5,3,3),hud_color('#82DCD5'))
