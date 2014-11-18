/* Examples of objects used by these functions:
var point1 = {x:0, y:0};
var point1 = {x:10, y:10};
var segment = {p1: point1, p2: point2};
*/

areSegmentsIntersecting = function(segment1, segment2) {
  var o1 = orientation(segment1.p1, segment1.p2, segment2.p1);
  var o2 = orientation(segment1.p1, segment1.p2, segment2.p2);
  var o3 = orientation(segment2.p1, segment2.p2, segment1.p1);
  var o4 = orientation(segment2.p1, segment2.p2, segment1.p2);
  
  if (o1*o2 == -1 && o3*o4 == -1)
    return true;  // Segments are noncolinear and intersecting.
  
  // Check colinearity special cases.
  if (o1 == 0 && isPointOnSegment(segment1.p1, segment2.p1, segment1.p2))
    return true;
  if (o2 == 0 && isPointOnSegment(segment1.p1, segment2.p2, segment1.p2))
    return true;
  if (o3 == 0 && isPointOnSegment(segment2.p1, segment1.p1, segment2.p2))
    return true;
  if (o4 == 0 && isPointOnSegment(segment2.p1, segment1.p2, segment2.p2))
    return true;

  return false;
};

area2 = function(ptA, ptB, ptC) {
  return (ptB.x - ptA.x) * (ptC.y - ptA.y) - (ptC.x - ptA.x) * (ptB.y - ptA.y);
}

orientation = function(ptA, ptB, ptC) {
  var area = area2(ptA, ptB, ptC);
  if (area == 0)
    return 0
  if (area > 0)
    return 1
  return -1
}

isPointOnSegment = function(ptP, ptQ, ptR) {
  return (ptQ.x < Math.max(ptP.x, ptR.x) && ptQ.x > Math.min(ptP.x, ptR.x) &&
          ptQ.y < Math.max(ptP.y, ptR.y) && ptQ.y > Math.min(ptP.y, ptR.y));
}
