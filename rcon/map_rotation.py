import json
from datetime import datetime
from numpy.random import choice
import pytz


with open('maps_btw.txt', 'r') as f:
    MAPS_BTW = [line for line in f.readlines() if line.strip()]
with open('maps_squad.txt', 'r') as f:
    MAPS_SQUAD = [line for line in f.readlines() if line.strip()]



class MapRotation:
    def __init__(self, fp):
        self.import_file(fp)
        self.cooldowns = {}

    def import_file(self, fp):
        with open(fp, 'r') as f:
            content = json.loads(f.read())

        # Get map cooldown
        try: self.map_cooldown = content['map_cooldown']
        except KeyError: self.map_cooldown = 1
        else: self.map_cooldown = content['map_cooldown'] if content['map_cooldown'] > 0 else 1

        # Get maps
        self.pool = Pool(content['maps'])

    def _next_map(self):
        all_entries = self.pool.get_entries()
        for entry in all_entries[::-1]:
            if not entry.validate(20) or entry.name in self.cooldowns.keys():
                all_entries.remove(entry)

        weights = [entry.weight for entry in all_entries]
        total_weight = sum(weights)
        probabilities = [weight / total_weight for weight in weights]
        for i in range(len(weights)):
            print(probabilities[i], weights[i], all_entries[i].name, [cond.type for cond in all_entries[i].conditions])

        draw = choice(all_entries, p=probabilities)
        return draw



class Pool:
    def __init__(self, pool, weight = 1, conditions = {}):
        self.weight = weight
        self.conditions = [Condition(k, v) for k, v in conditions.items()]

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
                    weight = int(entry['weight']) if 'weight' in keys else 1
                    conditions = entry['conditions'] if 'conditions' in keys else {}
                    self.pool.append(Map(name, weight, conditions))
                elif 'pool' in keys:
                    pool = entry['pool']
                    weight = int(entry['weight']) if 'weight' in keys else 1
                    conditions = entry['conditions'] if 'conditions' in keys else {}
                    self.pool.append(Pool(pool, weight, conditions))

    @property
    def content(self):
        return self.pool

    def get_entries(self):
        all_entries = []
        for entry in self.pool:
            all_entries += entry.get_entries()

        total_weight = sum([entry.weight for entry in all_entries])
        for i, entry in enumerate(all_entries):
            entry.weight *= (self.weight / total_weight)
            entry.conditions += self.conditions
            all_entries[i] = entry
        return all_entries

    def validate(self, players=None):
        for condition in self.conditions:
            if not condition.validate(players):
                return False
        return True

class Map:
    def __init__(self, name, weight = 1, conditions = {}):
        self.name = name
        self.weight = weight if weight > 0 else 1
        self.conditions = [Condition(k, v) for k, v in conditions.items()]
    
    @property
    def content(self):
        return self.name

    def get_entries(self):
        return [self]

    def validate(self, players=None):
        for condition in self.conditions:
            if not condition.validate(players):
                return False
        return True



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
            self.min = int(h)*60+int(m)
            h, m = arguments['max'].split(":")
            self.max = int(h)*60+int(m)
            
            try: self.tz = pytz.timezone(arguments['timezone']) if arguments['timezone'] else pytz.utc
            except: raise MapRotationError('Unknown timezone: %s' % arguments['timezone'])
        
        else:
            raise MapRotationError('Invalid condition: %(condition)s')
    
    def validate(self, players=None):
        if self.type == 'players':
            if players:
                if players >= self.min and players <= self.max: return True
                else: return False
            else:
                return True
        elif self.type == 'time':
            t = datetime.now(tz=self.tz)
            time = t.hour*60+t.minute

            if time >= self.min and time <= self.max: return True
            else: return False




class MapRotationError(Exception):
    """Base exception for map rotations"""
    pass



if __name__ == '__main__':
    from pathlib import Path
    rotation = MapRotation(Path("./map_rot_example.json"))
    print("draw:", rotation._next_map().name)