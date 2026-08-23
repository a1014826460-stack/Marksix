(function (window) {
  "use strict";

  function keyOf(draw) {
    return String(draw && (draw.current_issue || draw.issue) || "").trim();
  }

  function merge(previous, incoming) {
    if (!incoming) return previous || null;
    var nextIssue = keyOf(incoming);
    var previousIssue = keyOf(previous);
    if (!nextIssue) return previous || incoming;
    if (previousIssue && previousIssue !== nextIssue) {
      return Object.assign({}, incoming, { balls: (incoming.balls || []).slice() });
    }
    var oldBalls = previous && Array.isArray(previous.balls) ? previous.balls : [];
    var newBalls = Array.isArray(incoming.balls) ? incoming.balls : [];
    var balls = oldBalls.slice();
    newBalls.forEach(function (ball, index) {
      if (ball && ball.value != null && String(ball.value).trim() !== "") balls[index] = ball;
    });
    return Object.assign({}, previous || {}, incoming, { current_issue: nextIssue, balls: balls });
  }

  window.LotterySiteDrawState = { merge: merge };
})(window);
