import json
from datetime import datetime
import pytz


with open('maps_btw.txt', 'r') as f:
    MAPS_BTW = [line for line in f.readlines() if line.strip()]
with open('maps_squad.txt', 'r') as f:
    MAPS_SQUAD = [line for line in f.readlines() if line.strip()]



class MapRotation:
    def __init__(self, fp):
        self.import_file(fp)

    def import_file(self, fp):
        with open(fp, 'r') as f:
            content = json.loads(f.read())

        # Get map cooldown
        try: self.map_cooldown = content['map_cooldown']
        except KeyError: self.map_cooldown = 1
        else: self.map_cooldown = content['map_cooldown'] if content['map_cooldown'] > 0 else 1

        # Get maps
        self.pool = Pool(content['maps'])
                


class Pool:
    def __init__(self, pool, weight = 1, conditions = {}):
        self.weight = weight
        self.conditions = conditions

        self.pool = []
        for entry in pool:
            if isinstance(entry, str):
                self.pool.append(Map(name=entry))
            elif isinstance(entry, list):
                self.pool.append(Pool(entry))
            elif isinstance(entry, dict):
                keys = entry.keys()
                if 'name' in keys:
                    name = str(entry['name'])
                    weight = int(entry['weight']) if weight in keys else 1
                    conditions = entry['conditions'] if conditions in keys else {}
                    self.pool.append(Map(name, weight, conditions))
                elif 'pool' in keys:
                    pool = entry['pool']
                    weight = int(entry['weight']) if weight in keys else 1
                    conditions = entry['conditions'] if conditions in keys else {}
                    self.pool.append(Pool(pool, weight, conditions))


class Map:
    def __init__(self, name, weight = 1, conditions = {}):
        self.name = name
        self.weight = weight if weight > 0 else 1
        self.conditions = conditions


class Condition:
    def __init__(self, condition, arguments):
        self.type = condition

        if self.type == 'players':
            self.min = int(arguments['min']) if 'min' in arguments.keys() else 0
            self.max = int(arguments['max']) if 'max' in arguments.keys() else 100

        elif self.type == 'time':
            if 'min' not in arguments.keys(): arguments['min'] = "0:00"
            if 'max' not in arguments.keys(): arguments['max'] = "24:00"            

            h, m = arguments['min'].split(":")
            self.hour_min = int(h)
            self.minutes_min = int(m) 
            h, m = arguments['max'].split(":")
            self.hour_max = int(h)
            self.minutes_max = int(m)
            
            try: self.tz = pytz.timezone(arguments['timezone']) if arguments['timezone'] else pytz.utc
            except: self.tz = pytz.utc
        
        else:
            raise MapRotationError("%s isn't a valid condition" % self.type)




class MapRotationError(Exception):
    """Base exception for map rotations"""
    pass



if __name__ == '__main__':
    from pathlib import Path
    rotation = MapRotation(Path("./map_rot_example.json"))
    print(rotation)
    print(rotation.pool)
    for entry in rotation.pool.pool:
        print(entry)