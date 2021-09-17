# Archon: Connecting your Squad, PS and BTW servers with Discord

<img align="right" width="250" height="250" src="images/icon.png">

Archon is a Discord bot made by timraay/Abusify that allows you to view and moderate your Squad, Post Scriptum or Beyond The Wire server through Discord with simple, yet powerful commands.

### License
Archon may be used by anyone under a MIT license. In short, you can obtain a copy of the code and modify it, but you can't claim you made it. It is also important to note that, if something *may* happen, I can not be held responsible for the consequences.

I'd like to add that any contributions to the project are welcome, no matter the size. This is an ambitious project and any help, feedback or even a thank you helps :)


## Features

### Team composition
Archon maintains a composition of the teams currently playing on the server at all times. Lots of information is stored about the teams and its players, all of which can be viewed.

### Moderation
Moderating your server is now a lot more accessible. Everyone with the right permissions can warn, kill, kick and ban players. Players can be switched sides, squads can be disbanded. Maps can be queued and replaced. Matches can be ended and restarted.

### Logs
The bot logs all sorts of actions up to 14 days old. This includes chat messages, players joining and leaving, matches ending and of course all actions taken with Archon. All of these can be viewed or exported to a text file. All logs can be logged directly into a text channel, and admins can be notified when called out or malicous words were used in-game ("!admin" triggers).


## Instances
Archon can handle connections with multiple servers at once. Each of these connections are called an instance. You can switch between instances using one simple command. Each instance can be configured differently.
### Permissions
Archon uses three types of permissions. Guild permissions, role permissions, and user permissions. Each instance can be "attached" to a guild (a Discord server). This guild is used for all sorts of systems such as the automatic logs and trigger words, but also the guild permissions. It is this guild you can set guild permissions for; the default permissions. These can then be overwritten by role and user permissions. 

As example, you can give every user of your guild access to view the status of your server, while only users with a specific role are able to actively moderate it, some of which may even grant or revoke permissions. For more info on this, you can use the command `r!perms help`.

## What's to come?
- [x] Log channels for more than just chat
- [x] Advanced map rotations
- [x] Server Seeding Profiles
- [x] Permissions overhaul
- [ ] Persistent player profiles
- [ ] Advanced graphs and stats
- [ ] Logs rework
- [ ] Steam API integration
- [ ] Custom command prefixes

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



# Getting started

### What you need:
- Administrator permissions on Discord
- Your server's IP address, RCON port and RCON password


To get started, you need to [invite the bot to your server](https://discord.com/oauth2/authorize?client_id=768095532651380786&scope=bot&permissions=510016). This requires administrator permissions.

### Creating an instance

Once the bot is there, you can use the `r!instance add` command to start creating your instance. When executed, the bot will guide you through the creation process in DMs. This too, requires administrator permissions.

You've now created your instance. But by default, no one other than you (the instance owner) will have permissions to interact with the instance.

### Granting permissions

> NOTE: It is highly advised you read `r!inst help` and `r!perms help` thorougly at some point.

As explained earlier, there are three types of permissions, guild/default, role and user permissions. I'll go over them one by one, starting with guild permissions.

Guild permissions or default permissions can be set using the `r!perms set guild <perms>` command. The "perms" argument should be **a comma-separated list** of permission types. A full list of available permissions can be found in the `r!perms help` command. But for now we'll just use `public,players`, which grants users permissions which allow viewing server status and team composition.

However, permissions still are not granted after doing this. That's because we also need to specify in which guild we want to give everyone permissions. By default, the guild this applies to is the one you used the `r!inst create` command in, but it can be changed with the `r!inst config guild_id <guild_id>` command. Now everyone in this guild should have permission to use `r!server`, `r!servers`, `r!player`, `r!players` and `r!map`.

If you have a server admin role in your guild, you can give members of that role specific perms, for instance to moderate the server. We can use `r!inst perms <role> <perms>` to **overwrite** the default permissions for everyone with the role. There's plenty of permission types regarding moderation, so make a list yourself.
> NOTE: Role permissions completely overwrite guild permissions. If a user has multiple roles with permissions tied to them, the highest role will count.

Now, we want one specific user to have special permissions, for instance to configurate the instance. We have to overwrite their permissions using user permissions. You can set user-specific permissions with the command `r!perms set <user> <perms>`. This user will also be able to access your instance from **outside the current guild**!
> NOTE: User permissions overwrite both guild and role permissions.

> NOTE: The instance owner's permissions can't ever be overwritten.

### Further configurations

There are more configuration options that can be done, with more to come as updates for the bot roll out. Using `r!inst config` you can view all config options and their values. When you add one of the options (the key) to the command, for instance `r!inst config chat_trigger_words`, information about that option is displayed. You can then set the value accordingly using `r!inst config <key> <value>`.

Certain groups of configuration options have been bundled into their own command. Chat trigger options can be more easily managed with `r!alerts`, and logging channels with `r!logging`.

> NOTE: Some configuration options (such as chat_trigger_words) rely on other options in other to work. Read the description of the option you're modifying before changing it in order to know what to input and whether it relies on other options.
