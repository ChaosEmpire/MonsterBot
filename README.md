# MonsterBot

Telegram Bot for individual selection

## Installation Guide:

```
pip install -r requirements.txt
```

### Install the Database

If you want to choose another schema please edit createdb.sql.

```
mysql -u <dbuser> < createdb.sql
```

### Upgrade the Database

To upgrade the Database please stop all bots and webhooks and execute

```
dbupdate.py
```

### Telegram

Create a Telegram Bot and put the APIToken in the config.ini File.

### Customize config.ini

You can use the following text substitution in the Message strings:

```
<pkmn>    : Pokemonname
<pkmnid>  : PokemonID
<despawn> : Despawntime 24h
<iv>      : Pokemon IV
<cp>      : Pokemon CP
<atk>     : Pokemon Attack
<def>     : Pokemon Defence
<sta>     : Pokemon Stamina
<lvl>     : Pokemon Level
```

```
token=xxxxxxxxxx      # Bot API Token
locale=de             # Language Settings

port=6000             # Port for webhook
reorgdays=180         # Days for reorg inactive users

dbname=tgbotdb        # Database name
dbhost=127.0.0.1      # Database hostname
dbport=3306           # Database port
dbuser=rocketmapuser  # Database user
dbpassword=xxxxxxxxx  # Database user password

# startmsg=           # individual Startmessagefile default startmsg_<locale>.txt

venuetitle="<pkmn>(<pkmnid>)"
venuemsg="until <despawn>"

ivmsg="<pkmn>(<pkmnid>)\nIV:<iv> CP:<cp> L:<lvl>\nA:<atk>/D:<def>/S:<sta>\nuntil <despawn>"
```

You can also send the user a start message. Edit the files in "locales/startmsg_<locale>.txt".

## Programs:

1. **mtgbot.py** is the program for the Telegram bot commands. It manages the settings of the users.

   It knows the folowing commands:

   ```
   help - : Help
   status - : Status of the Bot
   list - : list your Pokemon and Type List
   add - <PokedexID> [IV]: add a Pokemon to the List. IV is not necessary, default 0
   del - <PokedexID>: delete a Pokemon from the List
   setiv - <PokedexID> <IV>: set the IV% from which reportet
   delpos - Deletes your GeoData Info you send with TG to the Bot before
   distance - VALUE set size of geofence around your location
   pvponly - (0/1) Only send PvP Pokemon 1 or send all 0(default)
   setiv - <PokedexID> <IV>: set the IV% from which reportet
   stop - : deactivate the Bot
   start - : activate the Bot
   mydata - : show your stored personal data
   deleteall - : delete all your data, no recover
   ```
   
   You can use this for the command list in Telegram ;-)

   The Users Pokemonlist is shared between all the bots connected to the same Database. So a user can switch between the bots by stopping the one and starting another one. He can now use the same List on multiple Bots.
   
2. **mtgbotwh.py** is the webhook for MAD. It sends the Pokemon to the users chatid.

   A Venue message is send if no IV are present.
   
   If IV are present it send an message and a location.
   
   If a user set the IV level and no IV are present then no message is send. The webhook log this with `No message send to {}. SearchIV to low for Pokemon {}({})`
   
   The script got extended to handle longer webhooks by the pvpporaclehelper plugin for MAD

3. **userreorg.py** reorganize users who have not used the bot for a long time. Days are set in the inifile.

## Changes

### 13. Jan 2020

Initial Version.
   
### 13. Feb 2021
   The script got extended to handle longer webhooks by the pvpporaclehelper plugin for MAD
