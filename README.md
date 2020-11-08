# Archon: Connecting your Squad/BTW servers with Discord

<img align="right" width="250" height="250" src="images/icon.png">

Archon is a Discord bot made by timraay aka. Abusify that allows you to view and moderate your Squad or Beyond The Wire server through Discord with simple, yet powerful commands.

### License
Archon may be used by anyone under a MIT license. In short, you can obtain a copy of the code and modify it, but you can't claim you made it. It is also important to note that, if something *may* happen, I can not be held responsible for the consequences.

I'd like to add that any contributions to the project are welcome, no matter the size. This is an ambitious project and any help, feedback or even a thank you helps :)


## Features

### Team composition
Archon maintains a composition of the teams currently playing on the server at all times. Lots of information is stored about the teams and its players, all of which can be viewed.

### Moderation
Moderating your server is now a lot more accessible. Everyone with the right permissions can warn, kill, kick and ban players. Players can be switched sides, squads can be disbanded. Maps can be queued and replaced. Matches can be ended and restarted.

### Logs
The bot logs all sorts of actions up to 7 days old. This includes chat messages, players joining and leaving, matches ending and of course all actions taken with Archon. All of these can be viewed or exported to a text file. Chat messages can be logged directly into a text channel, and admins can be notified when called out or malicous words were used in-game.


## Instances
Archon can handle connections with multiple servers at once. Each of these connections are called an instance. You can switch between instances using one simple command. Each instance can be configured differently.
### Permissions
Archon uses two types of permissions. Guild permissions and user permissions. Each instance can be "attached" to a guild (a Discord server). This guild is used for all sorts of systems such as the automatic logs and trigger words, but also the guild permissions. It is this guild you can set default permission level for. These can then be overwritten per user. As example, you can give every user of your server access to view the status of your server, while only specific users are able to actively moderate it, some of which may even grant or revoke permissions. For more info on this, you can use the command `r!inst perms help`.

## What's to come?
- [ ] Advanced graphs and stats
- [ ] Log channels for more than just chat
- [ ] Advanced map rotations
- [ ] Automatic broadcasts
- [ ] Server Seeding Profiles
- [ ] Steam API integration
- [ ] Instances rework

## Images

Server statuses

![Player Info](/images/server_statuses.PNG)

Team compositions

![Team Composition](/images/team_composition.PNG)

Player information

![Player Info](/images/player_info.PNG)

Instances

![Player Info](/images/instances.PNG)

Permissions

![Player Info](/images/permissions.PNG)

Config & trigger words




# Getting started

### What you need:
- Administrator permissions on Discord
- Your server's IP address, RCON port and RCON password


To get started, you need to [invite the bot to your server](https://discord.com/oauth2/authorize?client_id=768095532651380786&scope=bot&permissions=510016). This requires administrator permissions.

### Creating an instance

Once the bot is there, you can use the `r!instance add` command to start creating your instance. When executed, the bot will guide you through the creation process in DMs. This too, requires administrator permissions.

You've now created your instance. But by default, no one except for you (the instance owner) will have permissions to interact with the instance.

### Granting permissions

> NOTE: It is highly advised you read `r!inst help` and `r!inst perms help` thorougly at some point.

As explained earlier, there are two types of permissions, guild and user permissions. I'll go over them one by one, starting with guild permissions.

Guild permissions can be set using the `r!inst perms guild set <perms>` command. The "perms" argument should be **a number**. More info on how that works is explained in the `r!inst perms help` command. But for now we'll just use `1`, which grants "public" permissions (which allows viewing server status and team composition).

However, permissions still are not granted after doing this. That's because we also need to specify in which guild we want to give everyone permissions. This can be done using the `r!inst config guild_id <guild_id>` command. Now everyone in this guild should have permission to use `r!server`, `r!servers`, `r!player`, `r!players` and `r!map`.

Now, we want our server admins to be able to moderate the server. We have to overwrite their permissions using user permissions. You can set user-specific permissions with the command `r!inst perms <user> set <perms>`.
> NOTE: User permissions completely overwrite guild permissions, no matter what permissions are granted.

### Further configurations

There are more configuration options that can be done, with more to come as updates for the bot roll out. Using `r!inst config` you can view all config options and their values. When you add one of the options (the key) to the command, for instance `r!inst config chat_trigger_words`, information about that option is displayed. You can then set the value accordingly using `r!inst config <key> <value>`.

> NOTE: Some configuration options (such as chat_trigger_words) rely on other options in other to work. Read the description of the option you're modifying before changing it in order to know whether it relies on other options.