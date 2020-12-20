# Custom Map Rotations
As of Archon v1.2.0, it is now possible to import your own, custom map rotations. These custom rotations are more detailed than any other. A couple of things that the system is capable of:

- Automatically queue maps (obviously)
- Select specified maps based on a set of (optional) conditions:
  - When the numbers of players online is within a specified range
  - Only at specified times of day
  - Only after a specified amount of other maps were queued
- Edit the rotation at any time without having to restart the server

## The `r!rotation` Command
This is what you'll be using to manage your custom rotation. The command itself is pretty simple:

- `r!rotation` - Shows the status of the module and the syntax to all of these subcommands
- `r!rotation upload` - Upload a new custom rotation
- `r!rotation enable` - Enable the custom rotation
- `r!rotation disable` - Disable custom rotation
- `r!rotation download` - Download your custom rotation

However, custom rotations have to be written in a specific format, which gets a bit more complicated...

# File Structure
Custom rotations have to be written in JSON. Furthermore, the `.json` extension is the only extension the bot will accept.

📦**The root tag**
<br> ┣ 📜int **map_cooldown**: How many other maps before a map can be queued again. Defaults to 1.
<br> ┗ 📂**maps**: An array of maps and/or pools
<br>   ┣ 📜The name of the map
<br>   ┣ 📦A map
<br>   ┃ ┣ 📜str **name**: The name of the map
<br>   ┃ ┣ 📜int **weight**: The weight applied to this map when selecting a map. Defaults to 1.
<br>   ┃ ┗ 📦**conditions**: A list of conditions
<br>   ┃   ┣ 📦**players**: How many players should be online
<br>   ┃   ┃ ┣ 📜int **min**: The minimum amount. Defaults to 0.
<br>   ┃   ┃ ┗ 📜int **max**: The maximum amount. Defaults to 100.
<br>   ┃   ┗ 📦**time**: What time of the day it should be
<br>   ┃     ┣ 📜str **min**: The minimum time, formatted as HH:MM. Defaults to 00:00.
<br>   ┃     ┣ 📜str **max**: The maximum time, formatted as HH:MM. Defaults to 24:00.
<br>   ┃     ┗ 📜str **timezone**: The timezone that is used. Can be a city as well. Defaults to UTC.
<br>   ┣ 📂An array of maps and/or more pools
<br>   ┗ 📦A pool of maps and/or more pools
<br>     ┣ 📂**pool**: An array of maps and/or more pools
<br>     ┃ ┗ ...
<br>     ┣ 📜int **weight**: The weight applied to this pool when selecting a map. Defaults to 1.
<br>     ┗ 📦**conditions**: A list of conditions
<br>       ┣ 📦**players**: How many players should be online
<br>       ┃ ┣ 📜int **min**: The minimum amount. Defaults to 0.
<br>       ┃ ┗ 📜int **max**: The maximum amount. Defaults to 100.
<br>       ┗ 📦**time**: What time of the day it should be
<br>         ┣ 📜int **min**: The minimum time, formatted as HH:MM. Defaults to 00:00.
<br>         ┣ 📜int **max**: The maximum time, formatted as HH:MM. Defaults to 24:00.
<br>         ┗ 📜str **timezone**: The timezone that is used. Can be a city as well. Defaults to UTC.

Simply put, a custom rotation is built out of a pool of maps and/or more pools. You can have as many pools as you want, and you can mention the same map several times throughout your custom rotation.

The below three map objects are all equivelant.
```json
"Kokan Skirmish v1"
```
```json
{
    "name": "Kokan Skirmish v1"
}
```
```json
{
    "pool": [
        {
            "name": "Kokan Skirmish v1",
            "weight": 1,
            "conditions": {}
        }
    ],
    "weight": 1,
    "conditions": {}
}
```
The same can be said about these two pool objects.
```json
[
    "Chora RAAS v1",
    "Chora RAAS v2"
]
```
```json
{
    "pool": [
        "Chora RAAS v1",
        "Chora RAAS v2"
    ]
}
```
# Examples
## Selecting a map
Take a look at the below example. In rotation we have Belaya, Fallujah and Gorodok.
```json
{
    "maps": [
        "Belaya RAAS v1",
        {
            "name": "Fallujah RAAS v1",
            "weight": 4
        },
        {
            "pool": [
                "Gorodok RAAS v1",
                "Gorodok RAAS v2",
            ],
            "weight": 5
        }
    ]
}
```
Selecting a map is approached pool by pool. The first pool that will be looked at is the `maps` array. Inside there, we see three different objects:

- Name: Belaya, Weight: 1
- Name: Fallujah, Weight: 4
- Another pool, Weight: 5

This results in a total weight of 10. The chance of a map or pool being picked is its weight divided by the total weight. So in this case, Belaya has a 1/10 = 10% chance, and Fallujah 4/10 = 40%. The other pool has a 50% chance of being chosen.

Lets pretend like that pool was chosen. Inside the pool we see two layers of Gorodok, each with a weight of 1. So both maps have a 50% chance of being chosen, after that initial 50% required to select something from this pool. 50% multiplied by 50% is 25%. This results in the following outcome:

- Name: Belaya, Chance: 10%
- Name: Fallujah, Chance: 40%
- Name: Gorodok v1, Chance: 25%
- Name: Gorodok v2, Chance: 25%

## Applying conditions
Now, I'm taking the same structure as above but rearranging it a bit and adding some extra conditions. Take a look.
```json
{
    "maps": [
        {
            "pool": [
                "Gorodok RAAS v1",
                {
                    "name": "Gorodok Skirmish v1",
                    "conditions": {
                        "players": {
                            "max": 20
                        }
                    }
                }
            ],
            "conditions": {
                "players": {
                    "max": 70
                }
            }
        },
        {
            "name": "Belaya RAAS v1",
            "conditions": {
                "time": {
                    "min": "14:00"
                }
            }
        },
        {
            "name": "Fallujah RAAS v1",
            "conditions": {
                "time": {
                    "max": "13:59"
                },
                "players": {
                    "min": 71
                }
            }
        }        
    ]
}
```
First in the pool we see another pool. This pool has a condition that requires a maximum of 70 players online. If that condition is not met no map from this pool will be queued for the next round. Instead, one of the other maps that meet their requirements will be queued. But for now let's pretend that this condition is met. In that case, we have two layers of Gorodok: RAAS and Skirmish. However, Skirmish has a condition that only allows a max of 20 players. So if we have 40 players online, only RAAS can be chosen from that pool.

## What happens when no conditions are met?
If a pool is selected, but then no item in that pool has its conditions met, that pool is simply ignored, and it will look for other maps and pools. In the below example, normally it would pick a layer of Gorodok, but if the playercount is below 50 Belaya will be chosen.
```json
{
    "maps": [
        {
            "pool": [
                {
                    "name": "Gorodok RAAS v1",
                    "conditions": {
                        "players": {
                            "min": 50
                        }
                    }
                },
                {
                    "name": "Gorodok RAAS v2",
                    "conditions": {
                        "players": {
                            "min": 60
                        }
                    }
                }
            ],
            "weight": 99999
        },
        {
            "name": "Belaya RAAS v1",
            "conditions": {
                "time": {
                    "min": "14:00"
                }
            }
        }
    ]
}
```
However, if the time is below 2 PM, the conditions applied to Belaya won't be met either. In that case there is no other map or pool to fall back to, and no map will be queued by RCON. Note that when a map invalidates after it was first queued and there is no other map to fall back to that map will still remain queued.

## Map Cooldown
Every time a map is played a cooldown is applied. This value is nothing more than the amount of maps that have to be inbetween the same map being queued again. So if I have a cooldown of 3, the map needs to be changed 3 times first before it can be queued again, since every map change the value is decreased by 1. Since map change has to be detected, the default and minimum map cooldown is 1.

In the below example, 4 maps are in the rotation. The cooldown completely ignores pools and duplicate maps, meaning that if Gorodok RAAS v1 has a cooldown, Gorodok RAAS v2 can still be selected. Following that same logic, if I'd have Gorodok RAAS v1 elsewhere in my custom rotation as well, that still couldn't be selected.
```json
{
    "map_cooldown": 3,
    "maps": [
        [
            "Gorodok RAAS v1",
            "Gorodok RAAS v2"
        ],
        "Belaya RAAS v1",
        "Fallujah RAAS v1"
    ]
}
```

## Server seeding maps
Using this system, maps used for server seeding can be automatically queued. Below is an example of how that could work.
```json
{
    "map_cooldown": 2,
    "maps": [
        {
            "pool": [
                "Gorodok Skirmish v1",
                "Kokan Skirmish v1",
                "Fools Road Skirmish v1"
            ],
            "conditions": {
                "players": {
                    "max": 20
                }
            }
        },
        {
            "pool": [
                "Gorodok RAAS v1",
                "Belaya RAAS v1",
                "Fallujah RAAS v1"
            ],
            "conditions": {
                "players": {
                    "min": 21
                }
            }
        }
    ]
}
```

# List of all maps
[Maps currently in Squad](maps_squad.txt)

[Maps currently in Beyond The Wire](maps_squad.txt)