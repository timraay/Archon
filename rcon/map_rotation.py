import json
from datetime import datetime
from numpy.random import choice
import pytz
from copy import deepcopy

import logging

with open('maps_btw.txt', 'r') as f:
    MAPS_BTW = [line for line in f.readlines() if line.strip() and not line.startswith('#')]
with open('maps_squad.txt', 'r') as f:
    MAPS_SQUAD = [line for line in f.readlines() if line.strip() and not line.startswith('#')]
with open('maps_ps.txt', 'r') as f:
    MAPS_PS = [line for line in f.readlines() if line.strip() and not line.startswith('#')]



class MapRotation:
    def import_rotation(self, fp=None, content=None):
        if fp:
            with open(fp, 'r') as f:
                try: content = json.loads(f.read())
                except json.JSONDecodeError as e:
                    raise MapRotationError("Invalid format: %s" % str(e))
        elif not content:
            raise ValueError('Expected File-like object or string')

        # Get map cooldown
        try: content['map_cooldown']
        except KeyError: self.map_cooldown = 1
        else: self.map_cooldown = content['map_cooldown'] if content['map_cooldown'] > 0 else 1

        # Get maps
        try: self.map_rotation = Pool(content['maps'])
        except Exception as e:
            if isinstance(e, MapRotationError): raise e
            else: raise MapRotationError('An unexpected exception occured: %s: %s' % (type(e).__name__, e))

        # Set current and upcoming map
        self.cooldowns = {str(self.current_map): 0}
        self.current_map = Map(self.current_map)
        self.next_map = self.map_changed(self.current_map)

    def _get_next_map(self):
        all_entries = self.map_rotation.get_entries()
        validated = list()
        for entry in all_entries:
            cooldown = entry.cooldown if entry.cooldown else self.map_cooldown
            if entry.validate(len(self.players)) and not (entry.name in self.cooldowns.keys() and self.cooldowns[entry.name] < cooldown) and not entry.name == str(self.current_map):
                validated.append(entry)
        
        weights = [entry.weight for entry in validated]
        total_weight = sum(weights)
        probabilities = [(weight / total_weight) for weight in weights]

        log_maps = '\n'.join([' '.join([str(probabilities[i]), str(weights[i]), str(validated[i].name), str([cond.type for cond in validated[i].conditions])]) for i in range(len(weights))])
        logging.info('Inst %s: MAPROT: Available maps:\n%s', self.id, log_maps)

        try: draw = choice(validated, p=probabilities)
        except ValueError:
            logging.warning('Inst %s: MAPROT: Failed to draw a map, returning none...', self.id)
            draw = None

        return draw

    def _decrease_cooldown(self):
        for i in list(self.cooldowns):
            self.cooldowns[i] += 1

    def map_changed(self, new_map):
        self._decrease_cooldown()
        self.cooldowns[str(new_map)] = 0
        if str(new_map) == str(self.next_map) or (self.next_map and not self.next_map.validate(len(self.players))) or self.is_transitioning:
            self.next_map = self._get_next_map()
            if self.next_map:
                self.rcon.set_next_map(self.next_map)

        return self.next_map
        
    def validate_next_map(self):
        if not self.next_map.validate(len(self.players)):
            logging.warning('Inst %s: MAPROT: %s failed to validate. Changing map...', self.id, self.next_map)
            self.next_map = self._get_next_map()
            if self.next_map:
                self.rcon.set_next_map(str(self.next_map))


class Pool:
    def __init__(self, pool, weight = 1.0, conditions = {}):
        self.weight = weight
        self.conditions = [Condition(k, v) for k, v in conditions.items()]
        try: self.cooldown = [c.value for c in self.conditions if c.type == 'cooldown'][0]
        except IndexError: self.cooldown = 0

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
                    weight = float(entry['weight']) if 'weight' in keys else 1.0
                    conditions = entry['conditions'] if 'conditions' in keys else {}
                    self.pool.append(Map(name, weight, conditions))
                elif 'pool' in keys:
                    pool = entry['pool']
                    weight = float(entry['weight']) if 'weight' in keys else 1.0
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
            if not entry.cooldown: entry.cooldown = self.cooldown
            all_entries[i] = entry
        return all_entries

    def validate(self, players=None):
        for condition in self.conditions:
            if not condition.validate(players):
                return False
        return True

class Map:
    def __init__(self, name, weight = 1.0, conditions = {}):
        self.name = str(name)
        self.weight = weight if weight > 0.0 else 1.0
        self.conditions = [Condition(k, v) for k, v in conditions.items()]
        try: self.cooldown = [c.value for c in self.conditions if c.type == 'cooldown'][0]
        except IndexError: self.cooldown = 0

    def __str__(self):
        return self.name

    def __eq__(self, other):
        if isinstance(other, (Map, str)):
            return str(self) == str(other)
        return NotImplemented

    @property
    def content(self):
        return self.name

    def get_entries(self):
        return [deepcopy(self)]

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
        
        elif self.type == 'cooldown':
            if int(arguments) > 0: self.value = int(arguments)
            else: raise MapRotationError('Invalid condition: %(condition)s requires a value greater than 0')
        
        else:
            raise MapRotationError('Invalid condition: %(condition)s')
    
    def validate(self, players=None):
        if self.type == 'players':
            if players != None:
                if players >= self.min and players <= self.max: return True
                else: return False
            else:
                return True
        elif self.type == 'time':
            t = datetime.now(tz=self.tz)
            time = t.hour*60+t.minute

            if time >= self.min and time <= self.max: return True
            else: return False
        elif self.type == 'cooldown':
            # This is validated elsewhere
            return True





class MapRotationError(Exception):
    """Base exception for map rotations"""
    pass
