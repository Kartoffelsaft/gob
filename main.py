import discord
from discord.ext import commands
from enum import Enum, unique, auto
from collections import defaultdict, Iterable
import pickle
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=['!gob ', '$gob ', '-gob '], intents=intents)

def nonefn():
    return None

gameList = set()
preferences = defaultdict(nonefn)
gameProps = defaultdict(nonefn)

def saveData():
    pickle.dump(gameList, open('gameList.pickle', 'wb'))
    pickle.dump(preferences, open('preferences.pickle', 'wb'))
    pickle.dump(gameProps, open('gameProps.pickle', 'wb'))

def loadData():
    global gameList, preferences, gameProps

    def loadDatum(name):
        if os.path.isfile(name + '.pickle'):
            return pickle.load(open(name + '.pickle', 'rb'))
        else:
            print(f"NOTE: {name} pickle file not found")
            return None

    gameList = loadDatum('gameList') or gameList
    preferences = loadDatum('preferences') or preferences
    gameProps = loadDatum('gameProps') or gameProps

    print(gameList)
    print(preferences)
    print(gameProps)

async def validateGame(ctx, game):
    if game in gameList:
        return True
    else:
        await ctx.send("{game} not in list")
        return False

@unique
class Preference(Enum):
    UNRATED   = auto()
    WONT_PLAY = auto()
    DONT_OWN  = auto()
    PREF_NOT  = auto()
    NO_PREF   = auto()
    WANT_PLAY = auto()
    
    def default():
        return Preference.UNRATED

    def from_str(str: str):
        if str in ['\U0001F7E4', 'clear', 'unrated']:
            return Preference.UNRATED
        if str in ['\U0000274C', 'wontplay', 'cantplay', 'wontrun']:
            return Preference.WONT_PLAY
        if str in ['\U0001F4B8', 'dontown']:
            return Preference.DONT_OWN
        if str in ['\U00002B07', 'prefnot', 'prefernot']:
            return Preference.PREF_NOT
        if str in ['\U0001F937', 'nopref', 'nopreference']:
            return Preference.NO_PREF
        if str in ['\U00002B06', 'wantplay', 'wanttoplay', 'favorite']:
            return Preference.WANT_PLAY

    def __str__(self):
        if self == Preference.UNRATED:
            return "not rated"
        if self == Preference.WONT_PLAY:
            return "can't/won't play"
        if self == Preference.DONT_OWN:
            return "doesn't own"
        if self == Preference.PREF_NOT:
            return "prefers not to play"
        if self == Preference.NO_PREF:
            return "no preference"
        if self == Preference.WANT_PLAY:
            return "want to play"

    def to_emoji(self):
        if self == Preference.UNRATED:
            return '\U0001F7E4'
        if self == Preference.WONT_PLAY:
            return '\U0000274C'
        if self == Preference.DONT_OWN:
            return '\U0001F4B8'
        if self == Preference.PREF_NOT:
            return '\U00002B07'
        if self == Preference.NO_PREF:
            return '\U0001F937'
        if self == Preference.WANT_PLAY:
            return '\U00002B06'

class SuggestionWeights():
    def __init__(
        self, 
        unrated=0, 
        wontplay=-5, 
        dontown=-4, 
        prefnot=-1,
        nopref=0, 
        wantplay=1, 
        playercount=0, 
        idealplayercount=1, 
        playercountFail=-5
    ):
        self.unrated = unrated
        self.wontplay = wontplay
        self.dontown = dontown
        self.prefnot = prefnot
        self.nopref = nopref
        self.wantplay = wantplay
                                  
        self.playercount = playercount
        self.idealplayercount = idealplayercount
        self.playercountFail = playercountFail

    def getGameScore(self, game, players):
        totalScore = 0
        missingFrom = []

        for player in players:
            if preferences[player.id] is None:
                totalScore += self.unrated
                missingFrom.append(player.name)
                continue

            pref = preferences[player.id][game]

            if pref == Preference.UNRATED:
                totalScore += self.unrated
                missingFrom.append(player.name)
            elif pref == Preference.WONT_PLAY:
                totalScore += self.wontplay
            elif pref == Preference.DONT_OWN:
                totalScore += self.dontown
            elif pref == Preference.PREF_NOT:
                totalScore += self.prefnot
            elif pref == Preference.NO_PREF:
                totalScore += self.nopref
            elif pref == Preference.WANT_PLAY:
                totalScore += self.wantplay

        pc = len(players)
        mn, mx = gameProps[game] and gameProps[game]['playercount'] or (None, None)
        imn, imx = gameProps[game] and gameProps[game]['idealplayercount'] or (None, None)

        print(f"game: {game}, player count: {pc}, min: {mn}, max: {mx}, imin: {imn}, imax: {imx}")

        if mn and mx:
            if pc < mn or pc > mx:
                totalScore += self.playercountFail
            elif imn and imx:
                if pc < imn or pc > imx:
                    totalScore += self.playercount
                else:
                    totalScore += self.idealplayercount
            else:
                totalScore += self.playercount

        return (totalScore, missingFrom)


def gameName(str):
    return str.lower().strip()

@bot.command(
    brief="Add a game to Gob's database"
)
async def addgame(ctx, *, game: gameName):
    if game in gameList:
        await ctx.send(f"{game} is already in the list")
        return
    gameList.add(game)
    await ctx.send(f"{game} added to the list")

    saveData()

@bot.command(
    brief="Remove a game from Gob (preferences unaffected)"
)
async def removegame(ctx, * game: gameName):
    if not await validateGame(ctx, game):
        return
    gameList.remove(game)
    await ctx.send(f"{game} has been removed. (note that this does not remove preferences set for it)")

    saveData()

@bot.command(
    aliases=['gamelist'],
    brief="List all of the games that Gob knows about"
)
async def listgames(ctx):
    print(gameList)
    await ctx.send('\n'.join(gameList))

@bot.command(
    brief="List all of the games you haven't rated yet"
)
async def listunrated(ctx):
    if preferences[ctx.author.id] is None:
        await listgames(ctx)
        return
    
    games = '\n'.join(filter(lambda g: preferences[ctx.author.id][g] == Preference.UNRATED, gameList))
    if len(games) > 0:
        await ctx.send(games)
    else:
        await ctx.send("all games have been rated")

@bot.command(
    aliases=['listratings', 'listpreferences', 'preflist'],
    brief="List all of the preferences you have set"
)
async def listprefs(ctx):
    if preferences[ctx.author.id] is None:
        await ctx.send("you have not rated any games")
        return

    gameDict = defaultdict(lambda: [])

    for game, pref in preferences[ctx.author.id].items():
        gameDict[pref].append(game)

    nl = '\n'
    games = '\n'.join(map(lambda kv: f"**{str(kv[0])}**{nl}{nl.join(kv[1])}", gameDict.items()))
    if len(games) > 0:
        await ctx.send(games)
    else:
        await ctx.send("no games have been rated")

def setpref_impl(author, pref: Preference, game: gameName):
    if preferences[author] is None:
        preferences[author] = defaultdict(Preference.default)

    preferences[author][game] = pref

    saveData()

@bot.command(
    aliases=['setpreference', 'setrating'],
    brief="Set the preference on a specific game",
    help="valid preferences are: wontplay, dontown, prefnot, nopref, wantplay"
)
async def setpref(ctx, preference: Preference.from_str, *, game: gameName):
    if not preference:
        await ctx.send(f"preference not recognized. \nvalid preferences are: wontplay, dontown, prefnot, nopref, wantplay")
        return
    if not await validateGame(ctx, game):
        return

    setpref_impl(ctx.author.id, preference, game)
    await ctx.send(f"preference for {game} set to {preference}")

class AskPrefMenu:
    def __init__(self, authId, msgId, game):
        self.authId = authId
        self.msgId = msgId
        self.game = game

    def getText(self):
        possiblePrefs = filter(lambda pref: pref != Preference.UNRATED, list(Preference))

        return f"what do you think of **{self.game}**?" + '\n' + '\n'.join(
            list(map(lambda pref: f"{pref.to_emoji()}: {str(pref)}", possiblePrefs))
        )

    async def updateMessage(self, msg: discord.Message):
        if preferences[self.authId] is None:
            preferences[self.authId] = defaultdict(Preference.default)
        unratedList = list(map(lambda m: m[0], filter(
            lambda rt: rt[1] == Preference.UNRATED and rt[0] in gameList, 
            preferences[self.authId].items()
        ))) + list(gameList.difference(preferences[self.authId].keys()))
        if len(unratedList) == 0:
            await msg.edit(content="All games rated")
            return "Done"
        self.game = unratedList[0]

        self.msgid = (await msg.edit(content=self.getText())).id

    async def answer(self, msg: discord.Message, setting: discord.Emoji):
        setpref_impl(self.authId, Preference.from_str(str(setting)), self.game)

        await self.updateMessage(msg)


prefmenus = []

@bot.command(
    brief="Display a menu to allow you to quickly set all of your preferences"
)
async def askprefs(ctx):
    msg = await ctx.send("Loading menu, please wait...")    

    newMenu = AskPrefMenu(ctx.author.id, msg.id, "")
    
    for possiblePref in filter(lambda pref: pref != Preference.UNRATED, list(Preference)):
        await msg.add_reaction(possiblePref.to_emoji())

    if await newMenu.updateMessage(msg) == "Done":
        return
    else:
        prefmenus.append(newMenu)

@bot.event
async def on_reaction_add(reaction, user):
    print(reaction)
    print(user)
    print(prefmenus)

    candidateMenus = list(filter(lambda m: user.id == m.authId and reaction.message.id == m.msgId, prefmenus))

    if len(candidateMenus) > 1:
        print("WARNING: possible duplicate menus")

    if len(candidateMenus) > 0:
        if await candidateMenus[0].answer(reaction.message, reaction.emoji) == "Done":
            prefmenus.remove(candidateMenus[0])

@bot.group(
    brief="set a property for a particular game"
)
async def setprop(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send(
            "Available game properties as of now:\n"
            "playercount <min> <max> <game>\n"
            "idealplayercount <min> <max> <game>\n"
        )

@bot.command(
    aliases=['proplist'],
    brief="list properties set for a particular game"
)
async def listprops(ctx, *, game: gameName):
    if not await validateGame(ctx, game):
        return
    if not gameProps[game]:
        await ctx.send(f"{game} does not have any properties set")
        return

    await ctx.send('\n'.join(list(map(lambda pv: f"{pv[0]}: {pv[1]}", gameProps[game].items()))))

@setprop.command()
async def playercount(ctx, mn: int, mx: int, *, game: gameName):
    if not await validateGame(ctx, game):
        return
    if not gameProps[game]:
        gameProps[game] = defaultdict(nonefn)

    gameProps[game]['playercount'] = (mn, mx)

    print(gameProps)
    saveData()
    await ctx.send(f"player count set to {mn}-{mx}")

@setprop.command()
async def idealplayercount(ctx, mn: int, mx: int, *, game: gameName):
    if not await validateGame(ctx, game):
        return
    if not gameProps[game]:
        gameProps[game] = defaultdict(nonefn)

    gameProps[game]['idealplayercount'] = (mn, mx)

    print(gameProps)
    saveData()
    await ctx.send(f"ideal player count set to {mn}-{mx}")

def suggest_impl(recCount, who: Iterable[discord.User]):
    def gameRate(game):
        score, missing = SuggestionWeights().getGameScore(game, list(who))
        return (game, score, missing)

    gameRatings = list(map(gameRate, gameList))
    gameRatings.sort(key=lambda gr: gr[1])

    print(gameRatings)
    gameRatings = gameRatings[-recCount:len(gameRatings)]

    return '\n'.join(map(
        lambda gsm: f"`{str(gsm[1]).ljust(4)}`| {gsm[0]}" +
            (f"(Note: {', '.join(gsm[2])} has/have not rated)" if len(gsm[2]) else ""),
        gameRatings
    ))

@bot.command(
    brief="suggest a game to play based off of who is in your voice chat"
)
async def suggest(ctx, recCount: int = 5):
    vc = ctx.author.voice and ctx.author.voice.channel
    if not vc:
        await ctx.send("you must be in a vc to use this command")
        return


    await ctx.send(suggest_impl(recCount, vc.members))

@bot.command(
    brief="suggest a game for the members you list"
)
async def suggestfor(ctx, who: commands.Greedy[discord.User], recCount=5):
    await ctx.send(suggest_impl(recCount, who))

loadData()

with open('.token') as f: bot.run(f.read().strip())






