"""Integer-pixel geometry library."""


import math


class Point(object):
  def __init__(self, x, y):
    self.x = x
    self.y = y
  
  @staticmethod
  def FromTuple(t):
    if len(t) != 2:
      raise ValueError('Cannot create Point from %d-element tuple' % len(t))
    return Point(t[0], t[1])


class Segment(object):
  def __init__(self, p1, p2):
    self.p1 = p1
    self.p2 = p2
  
  def Intersects(self, other):
    """Returns True if the two segments intersect."""
    o1 = Orientation(self.p1, self.p2, other.p1)
    o2 = Orientation(self.p1, self.p2, other.p2)
    o3 = Orientation(other.p1, other.p2, self.p1)
    o4 = Orientation(other.p1, other.p2, self.p2)
    if o1 * o2 == -1 and o3 * o4 == -1:
      return True  # Segments are noncolinear and intersecting.
    
    # Check colinearity special cases.
    if o1 == 0 and OnSegment(self.p1, other.p1, self.p2):
      return True
    if o2 == 0 and OnSegment(self.p1, other.p2, self.p2):
      return True
    if o3 == 0 and OnSegment(other.p1, self.p1, other.p2):
      return True
    if o4 == 0 and OnSegment(other.p1, self.p2, other.p2):
      return True
    
    return False

def Area2(a,b,c):
  """Returns the area of the triangle, multiplied by 2.
  
  Negative for ccw-oriented triangles, positive for cw-oriented triangles,
  and zero for collinear points.
  
  In other words, this is the vector product of b-a with c-a.
  
  a,b,c are of type Point.
  """
  return (b.x - a.x) * (c.y - a.y) - (c.x - a.x) * (b.y - a.y);


def Orientation(a,b,c):
  """The orientation of the three points.
  
  Returns:
    0 for colinear points,
    1 for clockwise orientation,
    -1 for counterclockwise orientation.
  """
  area = Area2(a,b,c)
  if area == 0:
    return 0
  elif area > 0:
    return 1
  else:
    return -1


def OnSegment(p,q,r):
  """Returns True if q is on the segment between p and r.
  
  Note that if q coincides with p or with r, we return False.
  This is done so that segments originating from the same point are not considered intersecting,
  i.e., these are "open segments".
  
  Assumes p,q,r are colinear.
  """
  return (q.x < max(p.x, r.x) and q.x > min(p.x, r.x) and
          q.y < max(p.y, r.y) and q.y > min(p.y, r.y))


def PointInTriangle(pt, triangle):
  """Returns true if pt is strictly inside triangle.
  
  Args:
    pt: Point object.
    triangle: List of three Point objects.
  """
  if len(triangle) != 3:
    raise ValueError('Received a triangle with %d vertices' % len(triangle))
  
  # Calculation based on http://stackoverflow.com/questions/2049582/how-to-determine-a-point-in-a-triangle
  area2 = Area2(triangle[0], triangle[1], triangle[2])
  if area2 == 0:
    return False  # Nothing is strictly inside a collinear triangle.
  st = (triangle[0].y*triangle[2].x - triangle[0].x*triangle[2].y +
        (triangle[2].y - triangle[0].y)*pt.x + (triangle[0].x - triangle[2].x)*pt.y)
  tt = (triangle[0].x*triangle[1].y - triangle[0].y*triangle[1].x +
        (triangle[0].y - triangle[1].y)*pt.x + (triangle[1].x - triangle[0].x)*pt.y)
  areasign = math.copysign(1, area2)
  st *= areasign
  tt *= areasign
  if st <= 0:
    return False
  if tt <= 0:
    return False
  if st + tt >= abs(area2):
    return False
  return True
