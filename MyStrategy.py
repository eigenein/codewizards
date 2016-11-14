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


class MyStrategy:
    MY_BASE_X, MY_BASE_Y = 200.0, 3800.0
    ATTACK_BASE_X, ATTACK_BASE_Y = 3000.0, 1000.0

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

    def __init__(self):
        random.seed(time.time())

    # noinspection PyMethodMayBeStatic
    def move(self, me: Wizard, world: World, game: Game, move: Move):
        # First, initialize some common things.
        attack_faction = self.get_attack_faction(me.faction)
        skills = set(me.skills)

        # Learn some skill.
        move.skill_to_learn = self.skill_to_learn(skills)
        # Apply some skill.
        move.status_target_id = me.id

        # Check if I'm healthy.
        if me.life < 0.75 * me.max_life:
            if not self.is_in_danger(me, world, game, attack_faction):
                # Move forward if no danger.
                self.move_to(me, world, game, move, self.ATTACK_BASE_X, self.ATTACK_BASE_Y)
                return
            # Retreat.
            self.move_to(me, world, game, move, self.MY_BASE_X, self.MY_BASE_Y)
            # And try to attack anyone.
            for unit in itertools.chain(world.wizards, world.minions, world.buildings):
                if unit.faction == attack_faction:
                    if self.attack(me, game, move, skills, unit, False):
                        break
            return

        # Try to attack an enemy wizard.
        targets = [
            unit
            for unit in world.wizards
            if unit.faction == attack_faction and me.get_distance_to_unit(unit) < me.vision_range
        ]
        if targets:
            target = min(targets, key=(lambda unit: unit.life))
            if self.attack(me, game, move, skills, target, False):
                return
            # Chase for him.
            self.move_to(me, world, game, move, target.x, target.y)
            return

        # Else try to pick up bonus.
        if world.bonuses:
            target = min(world.bonuses, key=(lambda unit: me.get_distance_to_unit(unit)))
            self.move_to(me, world, game, move, target.x, target.y)
            return

        # Else try to attack an enemy minion.
        targets = [
            unit
            for unit in world.minions
            if unit.faction == attack_faction and me.get_distance_to_unit(unit) < me.cast_range
        ]
        if targets:
            target = min(targets, key=(lambda unit: unit.life))
            if self.attack(me, game, move, skills, target, False):
                return

        # Else try to attack an enemy building.
        targets = [
            unit
            for unit in world.buildings
            if unit.faction == attack_faction and me.get_distance_to_unit(unit) < me.vision_range
        ]
        if targets:
            target = min(targets, key=(lambda unit: me.get_distance_to_unit(unit)))
            if self.attack(me, game, move, skills, target, False):
                return
            # Move closer to the building.
            self.move_to(me, world, game, move, target.x, target.y)
            return

        # Nothing special to do, just move to the base.
        self.move_to(me, world, game, move, self.ATTACK_BASE_X, self.ATTACK_BASE_Y)
        move.turn = me.get_angle_to(self.ATTACK_BASE_X, self.ATTACK_BASE_Y)

    @staticmethod
    def skill_to_learn(skills: Set[SkillType]):
        for skill in MyStrategy.SKILL_ORDER:
            # Just look for the first skill in the list.
            if skill not in skills:
                return skill

    @staticmethod
    def get_attack_faction(faction: Faction):
        return Faction.ACADEMY if faction == Faction.RENEGADES else Faction.RENEGADES

    @staticmethod
    def is_in_danger(me: Wizard, world: World, game: Game, attack_faction) -> bool:
        span = 2.0 * me.radius
        for wizard in world.wizards:
            if wizard.faction == attack_faction and wizard.get_distance_to_unit(me) < wizard.cast_range + span:
                return True
        for minion in world.minions:
            if minion.faction == attack_faction and minion.get_distance_to_unit(me) < game.fetish_blowdart_attack_range + span:
                return True
        for building in world.buildings:
            if building.faction == attack_faction and building.get_distance_to_unit(me) < game.guardian_tower_attack_range + span:
                return True
        return False

    @staticmethod
    def move_to(me: Wizard, world: World, game: Game, move: Move, x: float, y: float):
        if me.get_distance_to(x, y) < me.radius:
            # Reached the destination.
            return
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
        if speed > 0.0:
            max_speed = max(game.wizard_forward_speed, game.wizard_strafe_speed)
            move.speed = speed * max_speed
            move.strafe_speed = strafe_speed * max_speed
        else:
            max_speed = max(game.wizard_backward_speed, game.wizard_strafe_speed)
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
        n, r, span = 20, 2.0 * me.radius, me.radius
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
    def attack(me: Wizard, game: Game, move: Move, skills: Set[SkillType], unit: CircularUnit, is_group: bool):
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
