#!/usr/bin/env python3
# coding: utf-8

import itertools
import math
import operator
import random
import time

from typing import Optional, Set, Tuple

from model.ActionType import ActionType
from model.CircularUnit import CircularUnit
from model.Faction import Faction
from model.Game import Game
from model.LaneType import LaneType
from model.Move import Move
from model.Player import Player
from model.SkillType import SkillType
from model.Wizard import Wizard
from model.World import World


class MyStrategy:
    # Порядок изучения навыков.
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

    # Ways to move around the map.
    WAY_POINTS = {
        LaneType.TOP: [
            # Move upwards.
            (200.0, 3400.0),
            (200.0, 3000.0),
            (200.0, 2600.0),
            (200.0, 2200.0),
            (200.0, 1800.0),
            (200.0, 1400.0),
            (200.0, 1000.0),
            (200.0, 600.0),
            # Move right.
            (600.0, 200.0),
            (1000.0, 200.0),
            (1400.0, 200.0),
            (1800.0, 200.0),
            (2200.0, 200.0),
            (2600.0, 200.0),
        ],
        LaneType.MIDDLE: [
            # Move around the base.
            (200.0, 3400.0),
            (600.0, 3400.0),
            # Move along diagonal.
            (1000.0, 3000.0),
            (1400.0, 2600.0),
            (1800.0, 2200.0),
            (2200.0, 1800.0),
            (2600.0, 1400.0),
            (3000.0, 1000.0),
        ],
        LaneType.BOTTOM: [
            # Move right.
            (600.0, 3800.0),
            (1000.0, 3800.0),
            (1400.0, 3800.0),
            (1800.0, 3800.0),
            (2200.0, 3800.0),
            (2600.0, 3800.0),
            (3000.0, 3800.0),
            (3400.0, 3800.0),
            # Move upwards.
            (3800.0, 3400.0),
            (3800.0, 3000.0),
            (3800.0, 2600.0),
            (3800.0, 2200.0),
            (3800.0, 1800.0),
            (3800.0, 1400.0),
        ],
    }

    def __init__(self):
        random.seed(time.time() + id(self))
        # Choose random lane by default.
        self.lane_type = random.choice([LaneType.TOP, LaneType.MIDDLE, LaneType.BOTTOM])
        self.way_point_index = 0
        self.reverse = False

    # noinspection PyMethodMayBeStatic
    def move(self, me: Wizard, world: World, game: Game, move: Move):
        # First, initialize some common things.
        my_player = world.get_my_player()  # type: Player
        opponent_faction = self.opponent_faction_to(my_player.faction)
        skills = set(me.skills)

        # Learn some skill.
        move.skill_to_learn = self.skill_to_learn(skills)
        # Apply some skill.
        move.status_target_id = me.id

        # Attack an enemy unit if possible.
        for target_lists in ([world.wizards], [world.minions, world.buildings]):
            # Look for the weakest wizard, then for everyone else.
            targets = list(self.filter_units(me, opponent_faction, me.cast_range, *target_lists))
            if targets:
                target = min(targets, key=operator.attrgetter("life"))
                is_group = len(targets) > 1  # Let's make it simple for the first time.
                is_attacking = self.attack(me, game, move, skills, target, is_group)
                break
        else:
            is_attacking = False

        # Try to avoid collisions.
        if self.avoid_collisions(me, game, world, move, opponent_faction):
            return

        # Sum up enemies lives within their attack ranges that are oriented to me.
        my_diameter = 2.0 * me.radius
        staff_angle = game.staff_range / 2.0
        enemies_life = (
            sum(
                unit.life
                for unit in self.filter_units(me, opponent_faction, me.cast_range + my_diameter, world.wizards)
                if abs(unit.get_angle_to_unit(me)) < staff_angle
            ) +
            sum(
                unit.life
                for unit in self.filter_units(me, opponent_faction, game.fetish_blowdart_attack_range + my_diameter, world.minions)
                if abs(unit.get_angle_to_unit(me)) < staff_angle
            )
        )
        # And check if there is an enemy building nearby.
        is_building_nearby = any(self.filter_units(me, opponent_faction, game.guardian_tower_attack_range + my_diameter, world.buildings))

        # Check if I'm healthy.
        if me.life < 0.5 * me.max_life and (enemies_life > 0.0 or is_building_nearby):
            # Retreat if I'm unhealthy and there is an enemy nearby.
            self.move_to_next_way_point(me, game, move, reverse=True)
            return

        # Strafe speed positive direction.
        strafe_x, strafe_y = -math.sin(me.angle), math.cos(me.angle)
        # Sum up allies lives in front of me.
        allies_life = me.life + sum(
            unit.life
            for unit in self.filter_units(me, me.faction, me.vision_range, world.minions, world.wizards, world.buildings)
            if unit.id != me.id and self.is_in_front_of_me(me.x, me.y, strafe_x, strafe_y, unit.x, unit.y)
        )
        # Compare lives of attacking units. Let's be a little bit risky.
        if enemies_life > 1.25 * allies_life:
            # Retreat if enemies in front of me are healthier.
            self.move_to_next_way_point(me, game, move, reverse=True)
            return

        # If not attacking, just move straight to the next way point.
        if is_attacking:
            return
        way_point = self.move_to_next_way_point(me, game, move)
        if way_point is not None:
            # noinspection PyArgumentList
            move.turn = me.get_angle_to(*way_point)

    @staticmethod
    def opponent_faction_to(faction: Faction):
        """
        Get enemy faction.
        """
        return Faction.ACADEMY if faction == Faction.RENEGADES else Faction.RENEGADES

    @staticmethod
    def is_oriented_to_unit(me: Wizard, game: Game, unit: CircularUnit) -> (bool, float):
        """
        Check if the wizard is oriented to the unit.
        """
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

    @staticmethod
    def get_action(me: Wizard, game: Game, skills: Set[SkillType], unit: CircularUnit, is_group: bool) -> (ActionType, float):
        """
        Checks distance to the unit and returns appropriate action type if possible.
        """
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
            distance_to_unit > game.fireball_explosion_min_damage_range
        ):
            return ActionType.FIREBALL, min_cast_distance
        if SkillType.FROST_BOLT in skills and me.mana > game.frost_bolt_manacost:
            return ActionType.FROST_BOLT, min_cast_distance
        if me.mana > game.magic_missile_manacost:
            return ActionType.MAGIC_MISSILE, min_cast_distance
        return ActionType.NONE, min_cast_distance

    def attack(self, me: Wizard, game: Game, move: Move, skills: Set[SkillType], unit: CircularUnit, is_group: bool):
        """
        Attacks the unit or turns around to attack it.
        """
        action_type, min_cast_distance = self.get_action(me, game, skills, unit, is_group)
        if action_type == ActionType.NONE:
            return False
        # We can cast something.
        is_oriented, cast_angle = self.is_oriented_to_unit(me, game, unit)
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
    def skill_to_learn(skills: Set[SkillType]) -> SkillType:
        """
        Get the next skill to learn.
        """
        for skill in MyStrategy.SKILL_ORDER:
            # Just look for the first skill in the list.
            if skill not in skills:
                return skill

    @staticmethod
    def filter_units(me: Wizard, faction: Faction, distance: float, *iterables):
        return (
            unit
            for unit in itertools.chain(*iterables)
            if unit.faction == faction and me.get_distance_to_unit(unit) < distance
        )

    def move_to_next_way_point(self, me: Wizard, game: Game, move: Move, reverse=False) -> Optional[Tuple[float, float]]:
        way_points = MyStrategy.WAY_POINTS[self.lane_type]
        if me.x < 400.0 and me.y > 3600.0:
            # We appeared near the base.
            self.way_point_index = 0
        if self.reverse != reverse:
            # Moving direction has been changed. Fix the way point.
            self.way_point_index += +1 if not reverse else -1
            self.reverse = reverse
        if self.way_point_index <= -1 or self.way_point_index >= len(way_points):
            # Reached the final destination. Stop.
            return
        # Move towards the way point.
        x, y = way_points[self.way_point_index]
        self.move_to(me, game, move, x, y)
        # Check if we reached the destination.
        if me.get_distance_to(x, y) < me.radius:
            # We reached the destination. Switch the next way point.
            self.way_point_index = self.way_point_index + 1 if not reverse else self.way_point_index - 1
        return x, y

    @staticmethod
    def move_to(me: Wizard, game: Game, move: Move, x: float, y: float):
        """
        Moves wizard towards the given direction.
        """
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
    def is_in_front_of_me(my_x: float, my_y: float, strafe_x: float, strafe_y: float, x: float, y: float) -> bool:
        return strafe_x * (y - my_y) - strafe_y * (x - my_x) < 0.0

    def avoid_collisions(self, me: Wizard, game: Game, world: World, move: Move, opponent_faction: Faction):
        # Let's imagine that there is a kind of spring between me and each other unit.
        spring_length = me.radius / 2.0
        k = 1000.0
        # Sum up all forces.
        force_x = force_y = 0.0
        is_activated = False
        for unit in itertools.chain(world.wizards, world.buildings):
            if unit.id == me.id or unit.faction == opponent_faction:
                continue
            distance = me.get_distance_to_unit(unit)
            true_distance = distance - me.radius - unit.radius
            if true_distance < spring_length:
                force_x += k * (spring_length - true_distance) * (me.x - unit.x) / distance
                force_y += k * (spring_length - true_distance) * (me.y - unit.y) / distance
                is_activated = True
        # Let's move.
        if is_activated:
            force = math.sqrt(force_x * force_x + force_y * force_y)
            self.move_to(me, game, move, me.x + me.radius * force_x / force, me.y + me.radius * force_y / force)
        return is_activated
