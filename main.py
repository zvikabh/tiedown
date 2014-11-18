import cgi
import copy
import json
import logging
import random
import webapp2

from google.appengine.api import channel
from google.appengine.api import users
from google.appengine.ext import db

import geometry

ANCHOR_LOCATIONS = [
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
    [14,9]]

INITIAL_PLAYERS_STATE = {
    'purple': {
        'pawns': [ [14,12], [13,13], [12,14] ],
        'cards': [],
        'links': [],
        'areas': [],
        'captures': 0,
    },
    'orange': {
        'pawns': [ [0,2], [1,1], [2,0] ],
        'cards': [],
        'links': [],
        'areas': [],
        'captures': 0,
    },
}
PLAYER_COLORS = [color for color in INITIAL_PLAYERS_STATE.iterkeys()]
PLAYERS_IN_GAME = len(PLAYER_COLORS)
NUM_CARDS_PER_PLAYER = 5
NUM_ANCHORS = 12

# Create cards.
CARDS=[]
#CARDS = ['switch', 'bomb', 'wind', 'joker']  # Uncomment after support for special cards is added.
for i in xrange(NUM_ANCHORS):
  CARDS.append(str(i+1))

JSON_SUCCESS = json.dumps({'status': 'ok'})
JSON_ERROR_GAME_NOT_FOUND = json.dumps({'status': 'ERROR', 'error': 'Game not found'})
JSON_ERROR_USER_NOT_AUTHORIZED = json.dumps({'status': 'ERROR', 'error': 'Unauthorized user'})
JSON_ERROR_GAME_NOT_AUTHORIZED = json.dumps({'status': 'ERROR', 'error': 'Unauthorized game'})
JSON_ERROR_NO_GAME_TO_JOIN = json.dumps({'status': 'ERROR', 'error': 'No game to join'})
JSON_ERROR_INVALID_MOVE = json.dumps({'status': 'ERROR', 'error': 'Invalid move'})

ALLOW_INTERSECTING_LINKS = True


def GetDiceRoll():
  return [random.randrange(1,7), random.randrange(1,7)]


def ChooseRandomCard():
  return random.choice(CARDS)


def IsLinkPossible(parsed_game_state, anchor1, anchor2):
  """Determines whether a link is possible.
  
  Args:
    parsed_game_state: Parsed game state
    anchor1: (string) First anchor in link, e.g. '7'
    anchor2: (string) Second anchor in link, e.g. '12'
  
  Returns: 'ok' if link creation is possible. Otherwise, a user-readable string
      explaining why link creation is not possible.
  """
  if anchor1 == anchor2:
    return 'Cannot create a link from an anchor to itself.'
  
  try:
    nanchor1 = int(anchor1)
    nanchor2 = int(anchor2)
  except ValueError, TypeError:
    return 'Invalid anchor identifier.'
  
  all_links = []
  for player_state in parsed_game_state['players'].itervalues():
    all_links.extend(player_state['links'])
  
  if [nanchor1,nanchor2] in all_links or [nanchor2,nanchor1] in all_links:
    return 'Link already exists.'
  
  if ALLOW_INTERSECTING_LINKS:
    return 'ok'  # Remove this line to disallow intersecting links.
  
  anchor_locs = parsed_game_state['anchors']
  anchor_locs_as_pts = {}
  for n, anchor_loc in anchor_locs.iteritems():
    anchor_locs_as_pts[n] = geometry.Point(anchor_loc[0], anchor_loc[1])
  links_as_segments = [geometry.Segment(anchor_locs_as_pts[str(link[0])],
                                        anchor_locs_as_pts[str(link[1])])
                       for link in all_links]

  # Check whether current link intersects with any of the existing links.
  proposed_segment = geometry.Segment(anchor_locs_as_pts[str(nanchor1)],
                                      anchor_locs_as_pts[str(nanchor2)])
  for link_segment in links_as_segments:
    if proposed_segment.Intersects(link_segment):
      return 'Link intersects an existing link.'

  return 'ok'


class GameState(db.Model):
  """The state of a game, as a JSON string."""
  state = db.TextProperty(required=True)
  
  """The value of the 'status' property in the state."""
  status = db.StringProperty(required=True)
  
  @staticmethod
  def NewGame(user_email):
    state = {
        'status': 'WAIT_FOR_JOIN',
        'players': copy.deepcopy(INITIAL_PLAYERS_STATE),
        'diceRoll': GetDiceRoll()}
    for player in state['players'].itervalues():
      for i in xrange(NUM_CARDS_PER_PLAYER):
        player['cards'].append(ChooseRandomCard())
    
    state['anchors'] = {}
    anchor_positions = random.sample(ANCHOR_LOCATIONS, NUM_ANCHORS)
    for n, anchor_position in enumerate(anchor_positions):
      state['anchors'][n+1] = anchor_position

    state['players'][PLAYER_COLORS[0]]['email'] = user_email
    state['currentPlayer'] = PLAYER_COLORS[0]
    status = state['status']
    return GameState(state=json.dumps(state), status=status)

  def PersonalizeGameState(self, user_email):
    """Returns a redacted version of the current game state, with personal data removed.
    
    Specifically, remove other players' cards and email address.
    """
    game_state = json.loads(self.state)
    your_color = None
    for player_color, player_state in game_state['players'].iteritems():
      if 'email' in player_state and player_state['email'] == user_email:
        your_color = player_color
        continue  # User is allowed to see their own details
      if 'email' in player_state:
        del player_state['email']
      del player_state['cards']
    if not your_color:
      logging.error('PersonalizeGameState: Player %s is not in game', user_email)
      return
    game_state['yourColor'] = your_color
    if game_state['status'] == 'READY':
      if your_color == game_state['currentPlayer']:
        game_state['status'] = 'SELECT_PAWN'
      else:
        game_state['status'] = 'WAIT_FOR_OTHER'
    return game_state
  
  def UpdateAllUsersExcept(self, current_user_email):
    """Sends a state update to all users except |current_user_email|."""
    parsed_game_state = json.loads(self.state)
    for player_color, player_data in parsed_game_state['players'].iteritems():
      if 'email' not in player_data:
        continue
      if player_data['email'] == current_user_email:
        continue
      personalized_game_state = self.PersonalizeGameState(player_data['email'])
      channel.send_message('%s:%d' % (player_data['email'], self.key().id()),
                           json.dumps(personalized_game_state))


class UserData(db.Model):
  """Information about a specific user, keyed by email."""
  
  """Space-separated list of ids of games the user is currently playing."""
  games = db.TextProperty(required=False)
  
  @staticmethod
  def GetCurrentUser():
    """Gets the UserData entity for the current user.
    
    Returns None if the current user email is unknown, or if the user was not found."""
    user = users.get_current_user()
    if not user:
      logging.warning('GetCurrentUser: User email unknown')
      return None

    return db.get(db.Key.from_path('UserData', user.email()))
    
  @staticmethod
  def GetOrCreateCurrentUser():
    """Gets the UserData entity for the current user, or creates it if this is a new user.

    Returns None if the current user email is unknown."""
    user = users.get_current_user()
    if not user:
      logging.warning('GetOrCreateCurrentUser: User email unknown')
      return None

    user_data = db.get(db.Key.from_path('UserData', user.email()))
    if not user_data:
      user_data = UserData(key_name=user.email(), games='')
      user_data.put()

    return user_data


def GenForm(url, button_text):
  FORM_TEMPLATE = """
  <html><head><link rel="stylesheet" type="text/css" href="css/board.css"></link></head><body>
  <form name="input" action="%s" method="post"><input type="submit" value="%s"></form>
  </body></html>
  """
  return FORM_TEMPLATE % (url, button_text)


class NewGameHandler(webapp2.RequestHandler):
  """Handles /newgame requests, which create a new game."""

  def get(self):
    self.response.write(GenForm('/newgame', 'Click to start a new game'))

  def post(self):
    user_data = UserData.GetOrCreateCurrentUser()
    if not user_data:
      self.response.write(JSON_ERROR_USER_NOT_AUTHORIZED)
      logging.warning('/newgame issued by unknown user')
      return

    user_email = users.get_current_user().email()
    new_game = GameState.NewGame(user_email)
    new_game.put()
    game_id = new_game.key().id()
    user_data.games += ' ' + str(game_id)
    user_data.put()
    logging.info('/newgame: Successfully created game %s for user %s', game_id, user_email)
    return self.redirect('/game.html?game_id=%d' % game_id)


class JoinGameHandler(webapp2.RequestHandler):
  """Handles /joingame requests, which add a player to a game."""
  
  def get(self):
    self.response.write(GenForm('/joingame?game_id=%s' % self.request.get('game_id'),
                        'Click to join the game.'))

  def post(self):
    user_data = UserData.GetOrCreateCurrentUser()
    if not user_data:
      logging.warning('/joingame issued by unknown user')
      self.response.write(JSON_ERROR_USER_NOT_AUTHORIZED)
      return
    user_email = users.get_current_user().email()
    
    query = GameState.all()
    query.filter('status =', 'WAIT_FOR_JOIN')
    available_games = query.fetch(100)

    requested_game = self.request.get('game_id', None)
    if requested_game:
      requested_game_state = db.get(db.Key.from_path('GameState', int(requested_game)))
      if not requested_game_state:
        logging.warning('/joingame: requested to join an nonexistant game: %s', requested_game)
        self.response.write(JSON_ERROR_GAME_NOT_AUTHORIZED)
        return
      if self._TryJoinGame(user_data, user_email, requested_game_state):
        game_id = requested_game_state.key().id()
        logging.info('/joingame: user %s successfully joined game %s',
                     user_email, game_id)
        return self.redirect('/game.html?game_id=%d' % game_id)
    else:
      for available_game in available_games:
        if self._TryJoinGame(user_data, user_email, available_game):
          game_id = available_game.key().id()
          logging.info('/joingame: user %s successfully joined game %s',
                       user_email, game_id)
          return self.redirect('/game.html?game_id=%d' % game_id)
    
    logging.warning('/joingame: user %s could not find a game to join', user_email)
  
  def _TryJoinGame(self, user_data, user_email, game_state):
    """Attempt to join |user_data| to |game_state|.
    
    On success, performs the join, notifies existing players, and returns True.
    On failure, writes an error message to the HTTP resoinse, and returns False.
    """
    requested_game = game_state.key().id()
    if game_state.status != 'WAIT_FOR_JOIN':
      self.response.write('This game already has the full number of players.')
      return False
    parsed_game_state = json.loads(game_state.state)

    # Check if player is already in game.
    for player in parsed_game_state['players'].itervalues():
      if 'email' in player and player['email'] == user_email:
        self.response.write('You cannot join a game in which you are already a player. '
                            'Please invite your friends!')
        return False

    # OK to join game.
    added_player = False
    for player in parsed_game_state['players'].itervalues():
      if 'email' not in player:
        player['email'] = user_email
        added_player = True
        break
    if not added_player:
      self.response.write('Internal server error, code 9201.')
      return False
    num_players = len([player for player in parsed_game_state['players'].itervalues()
                       if 'email' in player])
    if num_players == PLAYERS_IN_GAME:
      parsed_game_state['status'] = 'READY'
      game_state.status = 'READY'
    game_state.state = json.dumps(parsed_game_state)
    game_state.put()
    user_data.games += ' ' + str(requested_game)
    user_data.put()

    game_state.UpdateAllUsersExcept(user_email)
    return True


class GetStateHandler(webapp2.RequestHandler):
  """Handles /getstate requests."""

  def get(self):
    user_data = UserData.GetCurrentUser()
    if not user_data:
      logging.warning('/getstate issued by unknown user')
      self.response.write(JSON_ERROR_USER_NOT_AUTHORIZED)
      return

    user_email = users.get_current_user().email()
    valid_games = user_data.games.split(' ')
    requested_game = self.request.get('game_id', None)
    if requested_game not in valid_games:
      logging.warning('/getstate: user %s requested state of invalid game %s',
                      user_email, requested_game)
      self.response.write(JSON_ERROR_GAME_NOT_AUTHORIZED)
      return

    game_state = db.get(db.Key.from_path('GameState', int(requested_game)))
    if not game_state:
      self.response.write(JSON_ERROR_GAME_NOT_AUTHORIZED)
      logging.warning('/getstate: game %s not found for user %s', requested_game, user_email)
      return

    personalized_game_state = game_state.PersonalizeGameState(user_email)
    self.response.write(json.dumps(personalized_game_state, indent=2, sort_keys=True))
    self.response.content_type = 'application/json'
    logging.info('/getstate: successful for user %s, game %s', user_email, requested_game)


class GetTokenHandler(webapp2.RequestHandler):
  """Handles /gettoken requests."""
  
  def get(self):
    current_user = users.get_current_user()
    if not current_user:
      logging.warning('/gettoken issued by unknown user')
      self.response.write(JSON_ERROR_USER_NOT_AUTHORIZED)
      return
    user_email = current_user.email()

    game_id = self.request.get('game_id', None)
    if not game_id:
      logging.warning('/gettoken with invalid game id')
      self.response.write(JSON_ERROR_GAME_NOT_AUTHORIZED)
      return
    token = channel.create_channel(user_email + ':' + game_id)
    self.response.write(json.dumps({'token': token}))


class ActionHandler(webapp2.RequestHandler):
  """Handles /action requests, which perform a user action."""
  
  def post(self):
    self.response.content_type = 'application/json'

    user = users.get_current_user()
    if not user:
      logging.warning('GetCurrentUser: User email unknown')
      self.response.write(JSON_ERROR_USER_NOT_AUTHORIZED)
      return
    user_email = user.email()
    
    game_id = self.request.get('game_id')
    requested_action = json.loads(self.request.get('action'))
    response = self._ValidateAndPerformAction(user_email, game_id, requested_action)
    self.response.write(response)
    
  def _ValidateAndPerformAction(self, user_email, game_id, action):
    """Validate the user's action, and perform it, if it is legal.
    
    An action is a series of one or more moves.
    """
    logging.info('user %s game %s requested action %r', user_email, game_id, action)
    
    # Get the relevant game.
    try:
      game_id = int(game_id)
    except ValueError, TypeError:
      logging.warning('/action: game %s not found for user %s', game_id, user_email)
      return JSON_ERROR_GAME_NOT_AUTHORIZED
    game_state = db.get(db.Key.from_path('GameState', game_id))
    if not game_state:
      logging.warning('/action: game %s not found for user %s', game_id, user_email)
      return JSON_ERROR_GAME_NOT_AUTHORIZED
    
    # Get game state.
    parsed_game_state = json.loads(game_state.state)
    current_player = parsed_game_state['currentPlayer']
    current_player_state = parsed_game_state['players'][current_player]
    dice_roll = parsed_game_state['diceRoll']
    
    # Validate and perform each of the moves in the action.
    for move in action:
      if 'ncard' in move:
        move_success = self._ValidateAndPerformCardMove(parsed_game_state, move)
      else:
        move_success = self._ValidateAndPerformShipMove(parsed_game_state, move)
      if not move_success:
        return JSON_ERROR_INVALID_MOVE
    
    # Check that all dice rolls have been used.
    if dice_roll != [-1, -1]:
      logging.error('Not all dice rolls have been used: diceRoll=%s', dice_roll)
      return JSON_ERROR_INVALID_MOVE

    # Action is valid. Perform end-of-action steps:
    # Get new cards for player, if necessary.
    while len(current_player_state['cards']) < NUM_CARDS_PER_PLAYER:
      current_player_state['cards'].append(ChooseRandomCard())

    # Count number of captured anchors for each player.
    self._CountCaptures(parsed_game_state)
    
    # Check if somebody won.
    winner = self._FindWinner(parsed_game_state)
    if winner:
      # We have a winner!
      parsed_game_state['status'] = 'VICTORY'
      parsed_game_state['winner'] = winner
    else:
      # Switch to next player.
      current_player_index = PLAYER_COLORS.index(current_player)
      current_player_index = (current_player_index + 1) % PLAYERS_IN_GAME
      current_player = PLAYER_COLORS[current_player_index]
      parsed_game_state['currentPlayer'] = current_player
      parsed_game_state['status'] = 'READY'
      parsed_game_state['diceRoll'] = GetDiceRoll()
    
    # Store new game status.
    game_state.status = parsed_game_state['status']
    game_state.state = json.dumps(parsed_game_state)
    game_state.put()
    logging.info('/action: successful move by %s in game %d' % (user_email, game_id))
    
    # Send updates to other users.
    game_state.UpdateAllUsersExcept(user_email)
    
    # Send update to current user in the HTTP response.
    personalized_game_state = game_state.PersonalizeGameState(user_email)
    return json.dumps(personalized_game_state)

  def _ValidateAndPerformShipMove(self, parsed_game_state, move):
    """Perform a single ship move. (A move is a part of a user's action.)"""
    current_player = parsed_game_state['currentPlayer']
    current_player_state = parsed_game_state['players'][current_player]
    dice_roll = parsed_game_state['diceRoll']
    oldPos = current_player_state['pawns'][move['npawn']]
    newPos = move['target']
    dx = abs(newPos[0] - oldPos[0])
    dy = abs(newPos[1] - oldPos[1])
    if dx != 0 and dx != dice_roll[0]:
      logging.error('Invalid move: dx=%d but diceRoll[0]=%d', dx, parsed_game_state['diceRoll'][0])
      return False
    if dy != 0 and dy != dice_roll[1]:
      logging.error('Invalid move: dy=%d but diceRoll[1]=%d', dy, parsed_game_state['diceRoll'][1])
      return False
    current_player_state['pawns'][move['npawn']] = move['target']
    if dx != 0:
      dice_roll[0] = -1
    if dy != 0:
      dice_roll[1] = -1
    return True

  def _ValidateAndPerformCardMove(self, parsed_game_state, move):
    """Perform a single card play move. (A move is part of a user's action.)"""
    current_player = parsed_game_state['currentPlayer']
    current_player_state = parsed_game_state['players'][current_player]
    ncard = move['ncard']
    card_type = current_player_state['cards'][ncard]
    
    if card_type not in [str(i) for i in xrange(1,13)]:
      logging.error('Special cards are not yet supported: requested card_type %s', card_type)
      return False

    npawn = move['npawn']
    target = current_player_state['pawns'][npawn]
    if target not in ANCHOR_LOCATIONS:
      logging.error('Trying to move anchor to a non-anchor location: target=%r', target)
      return False
    if target in parsed_game_state['anchors'].itervalues():
      target_anchor = None
      for anchor, position in parsed_game_state['anchors'].iteritems():
        if position == target:
          target_anchor = anchor
          break
      source_anchor = current_player_state['cards'][ncard]
      success = self._ValidateAndPerformCreateLink(parsed_game_state, source_anchor, target_anchor)
    else:
      success = self._ValidateAndPerformMoveAnchor(parsed_game_state, ncard, target)
    
    if not success:
      return False
    
    # Successful move. Remove used card.
    del current_player_state['cards'][ncard]
    
    return success
    
  def _ValidateAndPerformCreateLink(self, parsed_game_state, anchor1, anchor2):
    is_link_possible = IsLinkPossible(parsed_game_state, anchor1, anchor2)
    current_player = parsed_game_state['currentPlayer']
    if is_link_possible != 'ok':
      logging.error('%s', is_link_possible)
      return False
    
    # Link possible. Create the link.
    links = parsed_game_state['players'][current_player]['links']
    links.append(sorted([int(anchor1), int(anchor2)]))
    
    # Check whether new area(s) are formed.
    areas = parsed_game_state['players'][current_player]['areas']
    for anchor3 in xrange(1,13):
      if sorted([int(anchor1), anchor3]) in links and sorted([int(anchor2), anchor3]) in links:
        areas.append(sorted([int(anchor1), int(anchor2), anchor3]))

    return True
  
  def _ValidateAndPerformMoveAnchor(self, parsed_game_state, ncard, target):
    """Moves an anchor to a new location. Returns True on success."""
    current_player = parsed_game_state['currentPlayer']
    current_player_state = parsed_game_state['players'][current_player]
    card_type = current_player_state['cards'][ncard]  # Already verified that it is a numeric card.
    
    # Check if there is a ship docking at this anchor. Anchored ships cannot move.
    anchor_pos = parsed_game_state['anchors'][card_type]
    for player_state in parsed_game_state['players'].itervalues():
      if anchor_pos in player_state['pawns']:
        logging.error('Attempting to move an anchor on which a ship is docking.')
        return False
        
    parsed_game_state['anchors'][card_type] = copy.copy(target)
    return True
    
  def _CountCaptures(self, parsed_game_state):
    """Counts the number of captured anchors for each player, and stores in parsed_game_state."""
    for player_color, player_state in parsed_game_state['players'].iteritems():
      logging.info('Counting captures for player %s' % player_color)
      captures = 0
      for area in player_state['areas']:
        anchor_locs = parsed_game_state['anchors']
        area_coords = [anchor_locs[str(anchor)] for anchor in area]
        # Check if any anchors are contained in this area.
        for nanchor in xrange(1,13):
          if nanchor in area:
            continue
          if geometry.PointInTriangle(
              geometry.Point.FromTuple(anchor_locs[str(nanchor)]),
              [geometry.Point.FromTuple(coord) for coord in area_coords]):
            logging.info('Anchor %d captured by area %r' % (nanchor, area))
            captures += 1
      player_state['captures'] = captures
  
  def _FindWinner(self, parsed_game_state):
    """Determines whether any player has won the game.
    
    Assumes capture counts are up-to-date.
    """
    for player_color, player_state in parsed_game_state['players'].iteritems():
      if player_state['captures'] >= 3:
        return player_color  # We have a winner!
    return None


app = webapp2.WSGIApplication(
    [
        ('/newgame', NewGameHandler),
        ('/joingame', JoinGameHandler),
        ('/getstate', GetStateHandler),
        ('/gettoken', GetTokenHandler),
        ('/action', ActionHandler),
    ], debug=True)