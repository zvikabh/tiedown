// Element sizes in pixels - must match values in stylesheet
CARD_WIDTH = 80;  // Width of a card.
CARD_SPACING = 10;  // Space between cards.
BOARD_SQUARE_WIDTH = 40;  // Width of a single element on the board.
BOARD_SQUARE_HEIGHT = 40;  // Height of a single element on the board.

ALLOW_INTERSECTING_LINKS = true;

// Number of positions in the board (in each direction)
var BOARD_SIZE = 15;

var PlayStage = {
  SELECT_PAWN:        {id: 0, message: 'Select a ship to move, click on a card, or click on Sail Away'},
  MOVE_PAWN:          {id: 1, message: 'Select where the ship should move'},
  WAIT_FOR_JOIN:      {id: 2, message: 'Waiting for another player to join'},
  WAIT_FOR_OTHER:     {id: 3, message: 'Waiting for other players to play'},
  SAIL_AWAY:          {id: 4, message: 'All moves completed. Click on Sail Away to confirm.'},
  APPLY_NUMERIC_CARD: {id: 5, message: 'To move anchor #curCardValue, click on a ship located on a valid anchor position. To create a link, click on a ship located on another anchor.'},
  VICTORY:            {id: 6, message: 'We have a winner!'},
}

var state = {};

var CARD_TITLES = {
  'bomb': 'Bomb',
  'joker': 'Joker Anchor',
  'switch': 'Switch Dice',
  'wind': 'Wind',
};
(function() {
  for (var i = 1; i <= 12; i++) {
    CARD_TITLES[i.toString()] = 'Anchor ' + i;
  }
}());

PLAYER_AREA_COLORS = {
  'purple': 'rgba(128,0,128,0.3)',
  'orange': 'rgba(225,125,0,0.4)',
  'cyan':   'rgba(0,255,255,0.3)',
  'yellow': 'rgba(255,255,0,0.6)',
};

var ANCHOR_LOCATIONS = [
    [0,4],
    [0,7],
    [2,5],
    [2,7],
    [2,9],
    [2,11],
    [3,3],
    [4,4],
    [4,6],
    [4,9],
    [4,11],
    [5,2],
    [6,0],
    [6,3],
    [6,5],
    [6,8],
    [6,10],
    [7,1],
    [7,7],
    [7,11],
    [7,12],
    [8,3],
    [8,5],
    [8,8],
    [9,0],
    [9,7],
    [9,10],
    [9,12],
    [9,14],
    [10,3],
    [10,9],
    [11,1],
    [11,4],
    [11,7],
    [11,12],
    [12,6],
    [12,10],
    [13,5],
    [13,8],
    [14,7],
    [14,9]];

isAnchorLoc = function(x, y) {
  for (var i = 0; i < ANCHOR_LOCATIONS.length; i++) {
    if (x == ANCHOR_LOCATIONS[i][0] && y == ANCHOR_LOCATIONS[i][1]) {
      return true;
    }
  }
  return false;
};

var curPlayStage = PlayStage[state.status];
var yourColor = state.yourColor;
var curSelectedPawn = -1;
var curSelectedPawnPos;
var curSelectedCard = -1;
var curCardValue = "";

// The user's action in this turn. Consists of a sequence of moves.
var myAction = [];

var boardElements = [];

// Get the game_id cgi param.
var game_id;
getGameId = function() {
  var argsMap = {};
  var query = window.location.search.substring(1);
  var args = query.split('&');
  for (var i = 0; i < args.length; i++) {
    var pair = args[i].split('=');
    argsMap[pair[0]] = pair[1];
  }
  return argsMap['game_id'];
};

// Retrieve the current state from the server.
loadState = function() {
  try {
    if (!game_id) {
      game_id = getGameId();
    }
    var request = new XMLHttpRequest();
    request.open('GET', '/getstate?game_id='+game_id, false);
    request.send(null);
    var json_state = request.responseText;
    updateStateTo(JSON.parse(json_state));
  }
  catch(err) {
    alert('Could not load game state - using default (for debug only)');
  }
};

updateStateTo = function(newState) {
  state = newState;
  curPlayStage = PlayStage[state.status];
  yourColor = state.yourColor;
};

var updatesChannel;
var updatesSocket;

// Set up a GAE Channel API token for getting server updates.
initUpdatesChannel = function() {
  try {
    if (!game_id) {
      game_id = getGameId();
    }
    var request = new XMLHttpRequest();
    request.open('GET', '/gettoken?game_id='+game_id, false);
    request.send(null);
    var json_token = request.responseText;
    var channelToken = JSON.parse(json_token).token;
    updatesChannel = new goog.appengine.Channel(channelToken);
    updatesSocket = updatesChannel.open();
    updatesSocket.onmessage = function(data) { updateStateTo(JSON.parse(data.data)); drawAll(); };
    updatesSocket.onclose = function() { initUpdatesChannel(); };
  }
  catch(err) {
    alert('Could not set up GAE Channel API token:\n' + err);
  }
};

createBoard = function() {
  var board = $("#board");
  for (var i = 0; i < BOARD_SIZE; i++) {
    boardElements[i] = [];
    for (var j = 0; j < BOARD_SIZE; j++) {
      var square = $("<div></div>");
      square.css("left", BOARD_SQUARE_WIDTH*i);
      square.css("top", BOARD_SQUARE_HEIGHT*j);
      square.attr("x", i).attr("y", j);
      boardElements[i][j] = square;
      board.prepend(square);
    }
  }
};

drawAll = function() {
  drawBoard();
  drawDice();
  drawYouAre();
  drawCards();
  drawMessage();
};

drawCards = function() {
  var cardsData = state.players[yourColor].cards;
  for (var i = 0; i < 6; i++) {
    var cardElem = $("#card-position-"+(i+1));
    if (i < cardsData.length) {
      cardElem.attr("class", "card card-type-"+cardsData[i]);
      cardElem.attr("title", CARD_TITLES[cardsData[i]]);
    } else {
      cardElem.attr("class", "card card-type-empty");
      cardElem.removeAttr("title");
    }
    if (i == curSelectedCard) {
      cardElem.addClass("selected");
    }
  }
};

drawDice = function() {
  var dice = [ "hdie", "vdie" ];
  for (var i = 0; i < dice.length; i++) {
    var die = $("#"+dice[i]+">img");
    die.attr("src", "images/dice-" + Math.abs(state.diceRoll[i]) + ".jpg");
    if (state.diceRoll[i] < 0) {
      die.addClass("used");
    } else {
      die.removeClass("used");
    }
  }
};

drawYouAre = function() {
  var imageSrc = "images/player-color-" + yourColor + ".png";
  var imageTitle = "Your color: " + yourColor;
  $("#player-color").html('<img src="' + imageSrc + '" title="' + imageTitle + '">');
};

drawBoard = function() {
  // Create class names from all board squares
  for (var i = 0; i < BOARD_SIZE; i++) {
    for (var j = 0; j < BOARD_SIZE; j++) {
      var boardElem = boardElements[i][j];
      boardElem.attr("class", "boardsquare");
      boardElem.contents().remove();
      if (isAnchorLoc(i,j)) {
        boardElem.addClass("anchorloc");
      }
    }
  }
  
  // Add portal positions
  for (var nPortal in state.anchors) {
    if (!state.anchors.hasOwnProperty(nPortal)) {
      continue;
    }
    var pos = state.anchors[nPortal];
    var boardSquare = boardElements[pos[0]][pos[1]];
    boardSquare.addClass("portal");
    var boardSquareSpan = $("<span></span>");
    boardSquareSpan.addClass("boardsquarespan");
    boardSquareSpan.text(nPortal);
    boardSquare.append(boardSquareSpan);
  }
  
  // Add pawn positions
  for (var playerName in state.players) {
    if (!state.players.hasOwnProperty(playerName)) {
      continue;
    }
    var pawns = state.players[playerName].pawns;
    for (var i = 0; i < pawns.length; i++) {
      var pos = pawns[i];
      var pawn = $("#" + playerName + "pawn-" + (i+1));
      var pawnLeft = BOARD_SQUARE_WIDTH*pos[0];
      var pawnTop = BOARD_SQUARE_HEIGHT*pos[1];
      if (boardElements[pos[0]][pos[1]].hasClass("portal")) {
        pawnLeft -= 5;
        pawnTop -= 8;
        pawn.css("z-index", 1);
        pawn.text(boardElements[pos[0]][pos[1]].text());
      } else {
        pawn.text("");
      }
      pawn.css({left: pawnLeft, 
                top: pawnTop});
      if (curSelectedPawn == i && state.currentPlayer == playerName) {
        pawn.addClass("selectedpawn");
      } else {
        pawn.removeClass("selectedpawn");
      }
    }
  }
  
  // Draw links
  var anchorToCoords = function(nanchor) {
    var cellCoords = state.anchors[nanchor];
    return [(cellCoords[0] + 0.5) * BOARD_SQUARE_WIDTH,
            (cellCoords[1] + 0.5) * BOARD_SQUARE_HEIGHT];
  };
  var canvas = $("#boardcanvas")[0];
  canvas.width = BOARD_SIZE * BOARD_SQUARE_WIDTH;
  canvas.height = BOARD_SIZE * BOARD_SQUARE_HEIGHT;
  var ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.lineWidth = 3;
  for (var playerName in state.players) {
    if (!state.players.hasOwnProperty(playerName)) {
      continue;
    }
    var links = state.players[playerName].links;
    if (!links) {
      continue;
    }
    ctx.beginPath();
    ctx.strokeStyle = playerName;
    for (var i = 0; i < links.length; i++) {
      var link = links[i];
      var srcCoord = anchorToCoords(link[0]);
      var dstCoord = anchorToCoords(link[1]);
      ctx.moveTo(srcCoord[0], srcCoord[1]);
      ctx.lineTo(dstCoord[0], dstCoord[1]);
      ctx.stroke();
    }
  }
  
  // Draw areas
  for (var playerName in state.players) {
    if (!state.players.hasOwnProperty(playerName)) {
      continue;
    }
    var areas = state.players[playerName].areas;
    if (!areas) {
      continue;
    }
    ctx.fillStyle = PLAYER_AREA_COLORS[playerName];
    for (var i = 0; i < areas.length; i++) {
      ctx.beginPath();
      var pos = anchorToCoords((areas[i][0]));
      ctx.moveTo(pos[0], pos[1]);
      for (var j = 1; j < areas[i].length; j++) {
        pos = anchorToCoords((areas[i][j]));
        ctx.lineTo(pos[0], pos[1]);
      }
      ctx.closePath();
      ctx.fill();
    }
  }
};

drawMessage = function() {
  var message = curPlayStage.message;
  message = message.replace("curCardValue", curCardValue);
  $("#new-text").text(message);
  
  if (curPlayStage == PlayStage.WAIT_FOR_JOIN) {
    var pathname = window.location.href;
    pathname = pathname.replace("game.html", "joingame");
    $("#msgbox-join-url").text(pathname);
    $("#msgbox-wrapper").css("display", "block");
  } else if (curPlayStage == PlayStage.VICTORY) {
    var captured = state.players[state.winner].captures
    if (state.winner == state.yourColor) {
      $("#msgbox-title").text("You win!");
      $("#msgbox-text").text("Congratulations! You won the game by capturing " + captured + " anchors.");
    } else {
      $("#msgbox-title").text("You lose!");
      $("#msgbox-text").text(state.winner + " has won the game by capturing " + captured + " anchors.");
    }
    $("#msgbox-wrapper").css("display", "block");
  } else {
    $("#msgbox-wrapper").css("display", "none");
  }
};

onSquareClick = function() {
  if (curPlayStage == PlayStage.MOVE_PAWN) {
    tryMovePawn(this);
  } else {
    // Meaningless click. Do nothing.
  }
};

onPawnClick = function() {
  var match = /.*pawn-([0-9]*)/.exec($(this).attr("id"));
  var npawn = parseInt(match[1])-1;

  if (curPlayStage == PlayStage.MOVE_PAWN) {
    // A pawn is already selected.
    if (!$(this).hasClass(state.currentPlayer + "pawn")) {
      // Clicked on another user's pawn.
      alert("There is already a ship in this position. Please try again.");
      return;
    }
    if (curSelectedPawn == npawn) {
      // Clicked on the same ship again. Cancel move.
      cancelMovePawn();
    } else {
      // Clicked on a different ship. Fall through to selecting that ship.
      selectPawn(npawn);
    }
    return;
  }
  
  if (curPlayStage == PlayStage.APPLY_NUMERIC_CARD) {
    // Apply a numeric card.
    if (!$(this).hasClass(state.currentPlayer + "pawn")) {
      alert("Wrong colored ship. You must click a " + state.currentPlayer + " ship.");
      return;
    }
    applyNumericCard(npawn);
    curSelectedCard = -1;
    curCardValue = "";
    curPlayStage = PlayStage.SELECT_PAWN;
    
    // Update display.
    drawBoard();
    drawCards();
    drawMessage();
    return;
  }
  
  if (curPlayStage != PlayStage.SELECT_PAWN) {
    return;
  }
  
  // Select a pawn to move.
  if (!$(this).hasClass(state.currentPlayer + "pawn")) {
    alert("Wrong colored ship. You must click a " + state.currentPlayer + " ship.");
    return;
  }
  selectPawn(npawn);
};

onCardClick = function() {
  var match = /card-position-([0-9]*)/.exec($(this).attr("id"));
  var ncard = parseInt(match[1])-1;
  
  if (curPlayStage == PlayStage.MOVE_PAWN) {
    // Cancel pawn move, instead select the card.
    cancelMovePawn();
    // curPlayStage is now PlayStage.SELECT_PAWN.
  }
  
  if (curPlayStage == PlayStage.APPLY_NUMERIC_CARD &&
      ncard == curSelectedCard) {
    // Cancel card selection.
    curSelectedCard = -1;
    curPlayStage = PlayStage.SELECT_PAWN;
    drawAll();
    return;
  }
  
  if (curPlayStage != PlayStage.SELECT_PAWN &&
      curPlayStage != PlayStage.APPLY_NUMERIC_CARD) {
    alert("Cannot select a card right now.");
    return;
  }
  
  var cardsData = state.players[yourColor].cards;
  if (ncard >= cardsData.length) {
    // No card to select; do nothing.
    return;
  }
  
  var selectedCard = parseInt(cardsData[ncard]);
  if (isNaN(selectedCard)) {
    alert("Special cards are not supported yet.");
    return;
  }
  
  curPlayStage = PlayStage.APPLY_NUMERIC_CARD;
  curSelectedCard = ncard;
  curCardValue = cardsData[ncard];
  drawCards();
  drawMessage();
};

cancelMovePawn = function() {
  curPlayStage = PlayStage.SELECT_PAWN;
  curSelectedPawn = -1;
  drawMessage();
  drawBoard();
};

selectPawn = function(npawn) {
  curSelectedPawn = npawn;
  curSelectedPawnPos = [state.players[state.currentPlayer].pawns[npawn][0],
                        state.players[state.currentPlayer].pawns[npawn][1]];
  curPlayStage = PlayStage.MOVE_PAWN;
  
  drawMessage();
  drawBoard();

  // Show potential move targets.
  var x = curSelectedPawnPos[0];
  var y = curSelectedPawnPos[1];
  var dx, dy, xtarget, ytarget;
  for (dx = -1; dx <= 1; dx++) {
    if (state.diceRoll[0] < 0 && dx != 0) {
      continue;
    }
    xtarget = x + dx * state.diceRoll[0];
    if (xtarget < 0 || xtarget >= BOARD_SIZE) {
      continue;
    }
    for (dy = -1; dy <= 1; dy++) {
      if (state.diceRoll[1] < 0 && dy != 0) {
        continue;
      }
      ytarget = y + dy * state.diceRoll[1];
      if (ytarget < 0 || ytarget >= BOARD_SIZE) {
        continue;
      }
      boardElements[xtarget][ytarget].addClass('possiblemovetarget');
    }
  }
};

applyNumericCard = function(npawn) {
  var proposedMove = {
    "ncard": curSelectedCard,
    "npawn": npawn,
  }
  
  var pawnpos = state.players[state.currentPlayer].pawns[npawn];
  var boardElem = boardElements[pawnpos[0]][pawnpos[1]];
  if (!boardElem.hasClass("anchorloc")) {
    alert("You cannot move an anchor to this location. Only circled locations are valid anchor positions.");
    return;
  }
  
  var nanchor = parseInt(curCardValue);
  if (boardElem.hasClass("portal")) {
    // Trying to create a link. Check if this is allowed.
    var nCurAnchor = parseInt(boardElem.text());
    var errMsg = isLinkPossible(Math.min(nanchor, nCurAnchor),
                                Math.max(nanchor, nCurAnchor));
    if (errMsg) {
      alert(errMsg);
      return;
    }
    // Link possible. Create link.
    state.players[state.currentPlayer].links.push([nanchor, nCurAnchor]);
  } else {
    // Trying to move an anchor. Check if this is allowed.
    var oldPos = state.anchors[nanchor];
    for (var playerName in state.players) {
      if (!state.players.hasOwnProperty(playerName)) {
        continue;
      }
      for (var i = 0; i < state.players[playerName].pawns.length; i++) {
        var otherPawnPos = state.players[playerName].pawns[i];
        if (otherPawnPos[0] == oldPos[0] && otherPawnPos[1] == oldPos[1]) {
          alert('Cannot move an anchor on which a ship is docked.');
          return;
        }
      }
    }
    // Move allowed. Do it.
    state.anchors[nanchor] = [pawnpos[0], pawnpos[1]];
  }

  // Remove card.
  state.players[state.currentPlayer].cards.splice(curSelectedCard, 1);
  
  // Update state.
  myAction.push(proposedMove);
};

tryMovePawn = function(target) {
  var proposedMove = {
    "npawn": curSelectedPawn,
    "target": [parseInt($(target).attr("x")), parseInt($(target).attr("y"))],
  }
  
  var srcx, srcy, dstx, dsty;
  srcx = curSelectedPawnPos[0];
  srcy = curSelectedPawnPos[1];
  dstx = proposedMove.target[0];
  dsty = proposedMove.target[1];
  dx = Math.abs(srcx - dstx);
  dy = Math.abs(srcy - dsty);
  
  if (dx == 0 && dy == 0) {
    // Move was canceled. Do nothing.
  } else if ((dx == 0 || dx == state.diceRoll[0]) &&
             (dy == 0 || dy == state.diceRoll[1])) {
    // Valid move.
    performMove(proposedMove);
    
    // Update dice roll state to show that some dice have been used.
    if (dx != 0) {
      state.diceRoll[0] *= -1;
    }
    if (dy != 0) {
      state.diceRoll[1] *= -1;
    }
  } else {
    alert("Invalid move. Please try again.");
  }
  
  if (state.diceRoll[0] < 0 && state.diceRoll[1] < 0) {
    curPlayStage = PlayStage.SAIL_AWAY;
  } else {
    curPlayStage = PlayStage.SELECT_PAWN;
  }
  curSelectedPawn = -1;
  drawAll();
}

isLinkPossible = function(nAnchor1, nAnchor2) {
  if (nAnchor1 == nAnchor2) {
    return "Cannot create a link from an anchor to itself.";
  }
  
  if (nAnchor1 > nAnchor2) {
    return "Internal error: nAnchor1 must be less than nAnchor2.";
  }
  
  var allLinks = [];
  for (var playerName in state.players) {
    if (!state.players.hasOwnProperty(playerName)) {
      continue;
    }
    for (var i = 0; i < state.players[playerName].links.length; i++) {
      var link = state.players[playerName].links[i];
      var linkFrom = Math.min(link[0], link[1]);
      var linkTo = Math.max(link[0], link[1]);
      if (nAnchor1 == link[0] && nAnchor2 == link[1]) {
        return "Link already exists.";
      }
      allLinks.push(link);
    }
  }
  
  if (!ALLOW_INTERSECTING_LINKS) {
    var anchorLocsAsPts = {};
    for (var nPortal in state.anchors) {
      if (!state.anchors.hasOwnProperty(nPortal)) {
        continue;
      }
      var pos = state.anchors[nPortal];
      anchorLocsAsPts[nPortal] = {x: pos[0], y: pos[1]};
    }
    
    var proposedSegment = {p1: anchorLocsAsPts[nAnchor1],
                           p2: anchorLocsAsPts[nAnchor2]};
    for (var i = 0; i < allLinks.length; i++) {
      var segment = {p1: anchorLocsAsPts[allLinks[i][0]],
                     p2: anchorLocsAsPts[allLinks[i][1]]};
      if (areSegmentsIntersecting(segment, proposedSegment)) {
        return "Link intersects an existing link.";
      }
    }
  }
  
  return "";  // Link possible.
};

performMove = function(proposedMove) {
  // Assumes isValidMove(proposedMove) returned true.
  var curPlayer = state.currentPlayer;
  var nPawn = proposedMove.npawn;
  state.players[curPlayer].pawns[nPawn] = proposedMove.target;
  myAction.push(proposedMove);
}

onSail = function() {
  // Send the action to the server.
  // This function returns immediately, but when the server responds, it will
  // call loadState() and drawAll().
  // We will soon call drawAll() anyway to show the user the new state even
  // before the server responds.
  sendMyActionToServer();

  curPlayStage = PlayStage.WAIT_FOR_OTHER;
  curSelectedPawn = -1;
  drawAll();
}

sendMyActionToServer = function() {
  $.post(
      '/action', 
      {
        action: JSON.stringify(myAction),
        game_id: game_id,
      }, 
      function(result) {
        if (result.status == 'ERROR') {
          alert('Move failed: ' + result.error);
          loadState();
        } else {
          updateStateTo(result);
        }
        drawAll();
      });
  myAction = [];
}

onCancel = function() {
  curSelectedPawn = -1;
  curSelectedCard = -1;
  myAction = [];
  loadState();
  drawAll();
}

$(document).ready(function() {
  createBoard();
  loadState();
  initUpdatesChannel();
  drawAll();
  $(".boardsquare").click(onSquareClick);
  $(".pawn").click(onPawnClick);
  $(".card").click(onCardClick);
  $("#btn-sail").click(onSail);
  $("#btn-undo").click(onCancel);
});
