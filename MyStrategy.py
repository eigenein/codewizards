#!/usr/bin/env python3
# coding: utf-8

import itertools
import math
import random
import time

from typing import Set, Tuple

from model.ActionType import ActionType
from model.CircularUnit import CircularUnit
from model.Faction import Faction
from model.Game import Game
from model.Move import Move
from model.SkillType import SkillType
from model.Wizard import Wizard
from model.World import World


MY_BASE_X, MY_BASE_Y = 200.0, 3800.0
ATTACK_BASE_X, ATTACK_BASE_Y = 3800.0, 200.0
BONUSES = [(1200.0, 1200.0), (2800.0, 2800.0)]

SKILL_ORDER = [
    SkillType.STAFF_DAMAGE_BONUS_PASSIVE_1,
    SkillType.STAFF_DAMAGE_BONUS_AURA_1,
    SkillType.STAFF_DAMAGE_BONUS_PASSIVE_2,
    SkillType.STAFF_DAMAGE_BONUS_AURA_2,
    SkillType.FIREBALL,

    SkillType.MAGICAL_DAMAGE_BONUS_PASSIVE_1,
    SkillType.MAGICAL_DAMAGE_BONUS_AURA_1,
    SkillType.MAGICAL_DAMAGE_BONUS_PASSIVE_2,
    SkillType.MAGICAL_DAMAGE_BONUS_AURA_2,
    SkillType.FROST_BOLT,

    SkillType.RANGE_BONUS_PASSIVE_1,
    SkillType.RANGE_BONUS_AURA_1,
    SkillType.RANGE_BONUS_PASSIVE_2,
    SkillType.RANGE_BONUS_AURA_2,
    SkillType.ADVANCED_MAGIC_MISSILE,

    SkillType.MOVEMENT_BONUS_FACTOR_PASSIVE_1,
    SkillType.MOVEMENT_BONUS_FACTOR_AURA_1,
    SkillType.MOVEMENT_BONUS_FACTOR_PASSIVE_2,
    SkillType.MOVEMENT_BONUS_FACTOR_AURA_2,
    SkillType.HASTE,

    SkillType.MAGICAL_DAMAGE_ABSORPTION_PASSIVE_1,
    SkillType.MAGICAL_DAMAGE_ABSORPTION_AURA_1,
    SkillType.MAGICAL_DAMAGE_ABSORPTION_PASSIVE_2,
    SkillType.MAGICAL_DAMAGE_ABSORPTION_AURA_2,
    SkillType.SHIELD,
]

# Half of tile size.
TILE_SPAN = 200.0 + 5.0

KEY_TILES = [
    # Top lane.
    (200.0, 200.0),
    (600.0, 200.0),
    (1000.0, 200.0),
    (1400.0, 200.0),
    (1800.0, 200.0),
    (2200.0, 200.0),
    (2600.0, 200.0),
    (3000.0, 200.0),
    (3400.0, 200.0),
    (3800.0, 200.0),
    # Bottom lane.
    (200.0, 3800.0),
    (600.0, 3800.0),
    (1000.0, 3800.0),
    (1400.0, 3800.0),
    (1800.0, 3800.0),
    (2200.0, 3800.0),
    (2600.0, 3800.0),
    (3000.0, 3800.0),
    (3400.0, 3800.0),
    (3800.0, 3800.0),
    # Left lane.
    (200.0, 600.0),
    (200.0, 1000.0),
    (200.0, 1400.0),
    (200.0, 1800.0),
    (200.0, 2200.0),
    (200.0, 2600.0),
    (200.0, 3000.0),
    (200.0, 3400.0),
    # Right lane.
    (3800.0, 600.0),
    (3800.0, 1000.0),
    (3800.0, 1400.0),
    (3800.0, 1800.0),
    (3800.0, 2200.0),
    (3800.0, 2600.0),
    (3800.0, 3000.0),
    (3800.0, 3400.0),
    # Main diagonal.
    (600.0, 3400.0),
    (800.0, 3200.0),
    (1000.0, 3000.0),
    (1200.0, 2800.0),
    (1400.0, 2600.0),
    (1600.0, 2400.0),
    (1800.0, 2200.0),
    (2000.0, 2000.0),
    (2200.0, 1800.0),
    (2400.0, 1600.0),
    (2600.0, 1400.0),
    (2800.0, 1200.0),
    (3000.0, 1000.0),
    (3200.0, 800.0),
    (3400.0, 600.0),
    # Other diagonal.
    (600.0, 600.0),
    (800.0, 800.0),
    (1000.0, 1000.0),
    (1200.0, 1200.0),
    (1400.0, 1400.0),
    (1600.0, 1600.0),
    (1800.0, 1800.0),
    (2200.0, 2200.0),
    (2400.0, 2400.0),
    (2600.0, 2600.0),
    (2800.0, 2800.0),
    (3000.0, 3000.0),
    (3200.0, 3200.0),
    (3400.0, 3400.0),
]

DIRECT_MOVE_DISTANCE = 600.0

KEY_ADJACENT = {
    i: [
        j
        for j, (jx, jy) in enumerate(KEY_TILES)
        if i != j and math.hypot(ix - jx, iy - jy) < DIRECT_MOVE_DISTANCE
    ]
    for i, (ix, iy) in enumerate(KEY_TILES)
}


class MyStrategy:

    def __init__(self):
        random.seed(time.time())
        self.pick_up_bonus = None

    # noinspection PyMethodMayBeStatic
    def move(self, me: Wizard, world: World, game: Game, move: Move):
        # First, initialize some common things.
        attack_faction = self.get_attack_faction(me.faction)
        skills = set(me.skills)

        # Learn some skill.
        move.skill_to_learn = self.skill_to_learn(skills)
        # Apply some skill.
        move.status_target_id = me.id

        # Bonus pick up.
        bonus_tick_index = world.tick_index % 2500
        if self.pick_up_bonus is None and (me.x > 1600.0 or me.y < 2400.0) and bonus_tick_index >= 2000:
            self.pick_up_bonus = min(BONUSES, key=(lambda bonus: me.get_distance_to(*bonus)))
        if me.x < 400.0 and me.y > 3600.0:
            self.pick_up_bonus = None
        if self.pick_up_bonus is not None:
            x, y = self.pick_up_bonus
            if not MyStrategy.attack_nearest_enemy(me, world, game, move, skills, attack_faction):
                move.turn = me.get_angle_to(x, y)
            if bonus_tick_index >= 2000 and me.get_distance_to(x, y) < me.radius + 2.0 * game.bonus_radius:
                # Bonus hasn't appeared yet. Stay nearby.
                return
            if 0 < bonus_tick_index < 2000 and (
                # Bonus has just been picked up.
                me.get_distance_to(x, y) < me.radius or
                # No bonus there.
                (me.get_distance_to(x, y) < me.vision_range and not world.bonuses)
            ):
                self.pick_up_bonus = None
            return

        # Check if I'm healthy.
        if self.is_in_danger(me, world, game, me.x, me.y, attack_faction):
            # Retreat to the nearest safe tile.
            x, y = min((
                (x, y)
                for x, y in KEY_TILES
                if not self.is_in_danger(me, world, game, x, y, attack_faction)
            ), key=(lambda point: me.get_distance_to(*point)))
            self.move_by_tiles_to(me, world, game, move, x, y)
            MyStrategy.attack_nearest_enemy(me, world, game, move, skills, attack_faction)
            return

        # Else try to attack the best target.
        if MyStrategy.attack_best_target(me, world, game, move, skills, attack_faction):
            return

        # Quick and dirty fix to avoid being stuck near the base.
        if me.x < 400.0 and me.y > 3600.0:
            move.turn = me.get_angle_to(*self.move_by_tiles_to(me, world, game, move, 200.0, 200.0))
            return

        # Nothing to do. Just go to enemy base.
        x, y = self.move_by_tiles_to(me, world, game, move, ATTACK_BASE_X, ATTACK_BASE_Y)
        move.turn = me.get_angle_to(x, y)

    @staticmethod
    def skill_to_learn(skills: Set[SkillType]):
        for skill in SKILL_ORDER:
            # Just look for the first skill in the list.
            if skill not in skills:
                return skill

    @staticmethod
    def get_attack_faction(faction: Faction):
        return Faction.ACADEMY if faction == Faction.RENEGADES else Faction.RENEGADES

    @staticmethod
    def is_in_danger(me: Wizard, world: World, game: Game, x: float, y: float, attack_faction) -> bool:
        max_life_risk = me.life - 0.25 * me.max_life
        span = 2.0 * me.radius
        for wizard in world.wizards:
            if wizard.faction != attack_faction:
                continue
            if wizard.get_distance_to(x, y) > wizard.cast_range + span:
                continue
            if wizard.remaining_action_cooldown_ticks > 0.5 * game.wizard_action_cooldown_ticks:
                continue
            if max_life_risk < 0.0:
                return True
            if SkillType.FIREBALL in wizard.skills:
                return True
            if max_life_risk < max(game.staff_damage, game.magic_missile_direct_damage, game.frost_bolt_direct_damage):
                return True
        if any(
            minion.get_distance_to(x, y) < game.fetish_blowdart_attack_range + span
            for minion in world.minions
            if minion.faction == attack_faction
        ):
            return True
        for building in world.buildings:
            if building.faction != attack_faction:
                continue
            if building.get_distance_to(x, y) > game.guardian_tower_attack_range + span:
                continue
            if max_life_risk < 0.0:
                return True
            if max_life_risk > game.guardian_tower_damage:
                continue
            if building.remaining_action_cooldown_ticks > 0.5 * building.cooldown_ticks:
                continue
            return True
        return False

    @staticmethod
    def move_by_tiles_to(me: Wizard, world: World, game: Game, move: Move, x: float, y: float) -> Tuple[float, float]:
        # We're already there?
        if me.get_distance_to(x, y) < 1.0:
            # Reached the destination.
            return x, y
        if me.get_distance_to(x, y) < DIRECT_MOVE_DISTANCE:
            # We can just move there.
            MyStrategy.move_to(me, world, game, move, x, y)
            return x, y
        # Find the nearest tile.
        my_index, (my_tile_x, my_tile_y) = min(enumerate(KEY_TILES), key=(lambda tile: me.get_distance_to(*tile[1])))
        if not MyStrategy.is_in_tile(my_tile_x, my_tile_y, me.x, me.y):
            # We're away. Go to this tile.
            MyStrategy.move_to(me, world, game, move, my_tile_x, my_tile_y)
            return my_tile_x, my_tile_y
        # Find the destination tile.
        destination_index = next(
            i for i, (tile_x, tile_y) in enumerate(KEY_TILES)
            if MyStrategy.is_in_tile(tile_x, tile_y, x, y)
        )
        # Find route between tiles.
        bfs_queue = [destination_index]
        bfs_visited = {destination_index}
        while bfs_queue:
            current_index = bfs_queue.pop(0)
            for previous_index in KEY_ADJACENT[current_index]:
                if previous_index == my_index:
                    move_x, move_y = KEY_TILES[current_index]
                    MyStrategy.move_to(me, world, game, move, move_x, move_y)
                    return move_x, move_y
                if previous_index not in bfs_visited:
                    bfs_queue.append(previous_index)
                    bfs_visited.add(current_index)
        print("Failed to find route from %s, %s to %s, %s" % (me.x, me.y, x, y))
        return x, y

    @staticmethod
    def is_in_tile(tile_x: float, tile_y: float, x: float, y: float) -> bool:
        return tile_x - TILE_SPAN < x < tile_x + TILE_SPAN and tile_y - TILE_SPAN < y < tile_y + TILE_SPAN

    @staticmethod
    def move_to(me: Wizard, world: World, game: Game, move: Move, x: float, y: float):
        x, y = MyStrategy.avoid_collisions(me, world, x, y)
        direction_x, direction_y = x - me.x, y - me.y
        # Normalize the destination vector.
        distance = math.sqrt(direction_x * direction_x + direction_y * direction_y)
        if abs(distance) < 1.0:
            return
        direction_x /= distance
        direction_y /= distance
        # Wizard's turn vector.
        turn_x, turn_y = math.cos(me.angle), math.sin(me.angle)
        # Project the destination vector onto the speed vector.
        speed = direction_x * turn_x + direction_y * turn_y
        # Project the destination vector onto the strafe speed vector.
        strafe_speed = direction_x * (-turn_y) + direction_y * turn_x
        # Finally, set up the movement.
        max_speed = 10.0
        if speed > 0.0:
            move.speed = speed * max_speed
            move.strafe_speed = strafe_speed * max_speed
        else:
            move.speed = speed * max_speed
            move.strafe_speed = strafe_speed * max_speed

    @staticmethod
    def avoid_collisions(me: Wizard, world: World, x: float, y: float) -> Tuple[float, float]:
        # Units to check for collisions against.
        units = [
            unit
            for unit in itertools.chain(world.buildings, world.minions, world.wizards, world.trees)
            if unit.id != me.id
        ]
        # Let's do grid search!
        new_x, new_y, min_distance = x, y, float("+inf")
        n, r, span = 40, 4.0, 4.0
        for i in range(n):
            angle = 2 * i * math.pi / n
            test_x, test_y = me.x + r * math.cos(angle), me.y + r * math.sin(angle)
            # Check for collisions in test point.
            if any(math.hypot(unit.x - test_x, unit.y - test_y) < me.radius + unit.radius + span for unit in units):
                continue
            # Check if we found a better distance.
            distance = math.hypot(x - test_x, y - test_y)
            if distance < min_distance:
                new_x, new_y, min_distance = test_x, test_y, distance
        # Return new destination.
        return new_x, new_y

    @staticmethod
    def attack_best_target(me: Wizard, world: World, game: Game, move: Move, skills: Set, attack_faction):
        targets = [
            unit
            for unit in world.wizards
            if unit.faction == attack_faction and me.get_distance_to_unit(unit) < me.vision_range
        ]
        if targets:
            # Try to attack the weakest wizard.
            target = min(targets, key=(lambda unit: unit.life))
            if MyStrategy.attack(me, game, move, skills, target, False):
                return True
            # Try to attack the nearest wizard.
            target = min(targets, key=(lambda unit: me.get_distance_to_unit(unit)))
            if MyStrategy.attack(me, game, move, skills, target, False):
                return True
            # Chase for it.
            MyStrategy.move_to(me, world, game, move, target.x, target.y)
            return True

        # Else try to attack an enemy building.
        targets = [
            unit
            for unit in world.buildings
            if unit.faction == attack_faction and me.get_distance_to_unit(unit) < me.vision_range
        ]
        if targets:
            target = min(targets, key=(lambda unit: me.get_distance_to_unit(unit)))
            if MyStrategy.attack(me, game, move, skills, target, False):
                return True
            # Move closer to the building.
            MyStrategy.move_to(me, world, game, move, target.x, target.y)
            return True

        # Else try to attack an enemy minion.
        targets = [
            unit
            for unit in world.minions
            if unit.faction == attack_faction and me.get_distance_to_unit(unit) < me.cast_range
        ]
        if targets:
            target = min(targets, key=(lambda unit: unit.life))
            if MyStrategy.attack(me, game, move, skills, target, False):
                return True

        # Couldn't attack anyone.
        return False

    @staticmethod
    def attack_nearest_enemy(me: Wizard, world: World, game: Game, move: Move, skills: Set, attack_faction):
        targets = sorted((
            unit
            for unit in itertools.chain(world.wizards, world.minions, world.buildings)
            if unit.faction == attack_faction
        ), key=(lambda unit: me.get_distance_to_unit(unit)))
        for target in targets:
            if MyStrategy.attack(me, game, move, skills, target, False):
                return True
        return False

    @staticmethod
    def attack(me: Wizard, game: Game, move: Move, skills: Set, unit: CircularUnit, is_group: bool):
        action_type, min_cast_distance = MyStrategy.get_action(me, game, skills, unit, is_group)
        if action_type == ActionType.NONE:
            return False
        # We can cast something.
        is_oriented, cast_angle = MyStrategy.is_oriented_to_unit(me, game, unit)
        if is_oriented:
            # Attack!
            move.cast_angle = cast_angle
            move.action = action_type
            move.min_cast_distance = min_cast_distance
            return True
        # Turn around to the enemy.
        move.turn = me.get_angle_to_unit(unit)
        return True

    @staticmethod
    def get_action(me: Wizard, game: Game, skills: Set[SkillType], unit: CircularUnit, is_group: bool) -> (ActionType, float):
        distance_to_unit = me.get_distance_to_unit(unit)
        min_cast_distance = distance_to_unit - unit.radius
        if distance_to_unit < game.staff_range:
            return ActionType.STAFF, min_cast_distance
        if distance_to_unit > me.cast_range:
            return ActionType.NONE, min_cast_distance
        if (
            SkillType.FIREBALL in skills and
            is_group and
            me.mana > game.fireball_manacost and
            distance_to_unit > game.fireball_explosion_min_damage_range + me.radius
        ):
            return ActionType.FIREBALL, min_cast_distance
        if SkillType.FROST_BOLT in skills and me.mana > game.frost_bolt_manacost:
            return ActionType.FROST_BOLT, min_cast_distance
        if me.mana > game.magic_missile_manacost:
            return ActionType.MAGIC_MISSILE, min_cast_distance
        return ActionType.NONE, min_cast_distance

    @staticmethod
    def is_oriented_to_unit(me: Wizard, game: Game, unit: CircularUnit) -> (bool, float):
        angle_to_unit = me.get_angle_to_unit(unit)
        cast_angle = abs(angle_to_unit) - math.atan(unit.radius / me.get_distance_to_unit(unit))
        if cast_angle < 0.0:
            # We can attack.
            return True, 0.0
        # Attack with some cast angle.
        if cast_angle < game.staff_sector / 2.0:
            # Cast angle has the same sign as turn angle.
            return True, math.copysign(cast_angle, angle_to_unit)
        # :(
        return False, None
