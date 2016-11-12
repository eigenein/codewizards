#!/usr/bin/env python3
# coding: utf-8

import itertools
import math
import operator
import random

from typing import Iterable, Set

from model.ActionType import ActionType
from model.BuildingType import BuildingType
from model.CircularUnit import CircularUnit
from model.Faction import Faction
from model.Game import Game
from model.LaneType import LaneType
from model.Move import Move
from model.Player import Player
from model.SkillType import SkillType
from model.Unit import Unit
from model.Wizard import Wizard
from model.World import World


class MyStrategy:
    # Порядок изучения навыков.
    SKILL_ORDER = [
        SkillType.RANGE_BONUS_PASSIVE_1,
        SkillType.MAGICAL_DAMAGE_BONUS_PASSIVE_1,
        SkillType.STAFF_DAMAGE_BONUS_PASSIVE_1,
        SkillType.MOVEMENT_BONUS_FACTOR_PASSIVE_1,
        SkillType.MAGICAL_DAMAGE_ABSORPTION_PASSIVE_1,

        SkillType.RANGE_BONUS_AURA_1,
        SkillType.MAGICAL_DAMAGE_BONUS_AURA_1,
        SkillType.STAFF_DAMAGE_BONUS_AURA_1,
        SkillType.MOVEMENT_BONUS_FACTOR_AURA_1,
        SkillType.MAGICAL_DAMAGE_ABSORPTION_AURA_1,

        SkillType.RANGE_BONUS_PASSIVE_2,
        SkillType.MAGICAL_DAMAGE_BONUS_PASSIVE_2,
        SkillType.STAFF_DAMAGE_BONUS_PASSIVE_2,
        SkillType.MOVEMENT_BONUS_FACTOR_PASSIVE_2,
        SkillType.MAGICAL_DAMAGE_ABSORPTION_PASSIVE_2,

        SkillType.RANGE_BONUS_AURA_2,
        SkillType.MAGICAL_DAMAGE_BONUS_AURA_2,
        SkillType.STAFF_DAMAGE_BONUS_AURA_2,
        SkillType.MOVEMENT_BONUS_FACTOR_AURA_2,
        SkillType.MAGICAL_DAMAGE_ABSORPTION_AURA_2,

        SkillType.ADVANCED_MAGIC_MISSILE,
        SkillType.FROST_BOLT,
        SkillType.FIREBALL,
        SkillType.HASTE,
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
            (200.0, 200.0),
            # Move right.
            (600.0, 200.0),
            (1000.0, 200.0),
            (1400.0, 200.0),
            (1800.0, 200.0),
            (2200.0, 200.0),
            (2600.0, 200.0),
            (3000.0, 200.0),
            (3400.0, 200.0),
            (3800.0, 200.0),
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
            (3400.0, 600.0),
            # Move around the base.
            (3400.0, 200.0),
            (3800.0, 200.0),
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
            (3800.0, 3800.0),
            # Move upwards.
            (3800.0, 3400.0),
            (3800.0, 3000.0),
            (3800.0, 2600.0),
            (3800.0, 2200.0),
            (3800.0, 1800.0),
            (3800.0, 1400.0),
            (3800.0, 1000.0),
            (3800.0, 600.0),
            (3800.0, 200.0),
        ],
    }

    def __init__(self):
        # Choose random lane by default.
        self.lane_type = random.choice([LaneType.TOP, LaneType.MIDDLE, LaneType.BOTTOM])
        self.way_point_index = 0
        self.reverse = False

    # noinspection PyMethodMayBeStatic
    def move(self, me: Wizard, world: World, game: Game, move: Move):
        # First, common things.
        my_player = world.get_my_player()  # type: Player
        opponent_faction = self.opponent_faction_to(my_player.faction)
        skills = set(me.skills)

        # Learn some skill.
        move.skill_to_learn = self.skill_to_learn(skills)
        # Shake sometimes to avoid complete blocking.
        if world.tick_index % 100 == 0:
            move.speed = random.choice([-game.wizard_backward_speed, +game.wizard_forward_speed])
            move.strafe_speed = random.choice([-game.wizard_strafe_speed, +game.wizard_strafe_speed])
            return

        # Save my own life.
        if me.life < 0.5 * me.max_life:
            # We're unhealthy. Retreat.
            self.move_to_next_way_point(me, game, move, reverse=True)
            return
        # Sum up allies and enemies lives.
        allies_life = sum(map(operator.attrgetter("life"), itertools.chain(
            self.filter_units_by_distance(me, self.filter_units_by_faction(world.minions, me.faction), me.vision_range),
            self.filter_units_by_distance(me, self.filter_units_by_faction(world.wizards, me.faction), me.vision_range),
        )))
        enemies_life = sum(map(operator.attrgetter("life"), itertools.chain(
            self.filter_units_by_distance(me, self.filter_units_by_faction(world.minions, opponent_faction), me.vision_range),
            self.filter_units_by_distance(me, self.filter_units_by_faction(world.wizards, opponent_faction), me.vision_range),
        )))
        if enemies_life > 1.2 * allies_life:
            # Enemies life is much greater. Retreat.
            self.move_to_next_way_point(me, game, move, reverse=True)
            return
        # Discover targets.
        targets = list(itertools.chain(
            self.filter_units_by_faction(world.minions, opponent_faction),
            self.filter_units_by_faction(world.wizards, opponent_faction),
            self.filter_units_by_faction(world.buildings, opponent_faction),
        ))
        if targets:
            # Just look for the nearest target.
            target = min(targets, key=(lambda target_: me.get_distance_to_unit(target_)))
            action_type, min_cast_distance = self.check_attack_distance(me, game, skills, target)
            is_oriented, cast_angle = self.is_oriented_to_unit(me, game, target)
            if action_type != ActionType.NONE:
                # We can cast something.
                if is_oriented:
                    # Attack!
                    move.cast_angle = cast_angle
                    move.action = action_type
                    move.min_cast_distance = min_cast_distance
                    return
                # Turn around to the enemy.
                move.turn = me.get_angle_to_unit(target)
                return
        # Just move straight.
        self.move_to_next_way_point(me, game, move)

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
    def check_attack_distance(me: Wizard, game: Game, skills: Set[SkillType], unit: CircularUnit) -> (ActionType, float):
        """
        Checks distance to the unit and returns action type if possible.
        """
        distance_to_unit = me.get_distance_to_unit(unit)
        min_cast_distance = distance_to_unit - unit.radius
        if distance_to_unit < game.staff_range:
            return ActionType.STAFF, min_cast_distance
        if distance_to_unit > me.cast_range:
            return ActionType.NONE, min_cast_distance
        if SkillType.FIREBALL in skills and me.mana > game.fireball_manacost:
            return ActionType.FIREBALL, min_cast_distance
        if SkillType.FROST_BOLT in skills and me.mana > game.frost_bolt_manacost:
            return ActionType.FROST_BOLT, min_cast_distance
        if me.mana > game.magic_missile_manacost:
            return ActionType.MAGIC_MISSILE, min_cast_distance
        return ActionType.NONE, min_cast_distance

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
    def filter_units_by_faction(units: Iterable[Unit], faction: Faction):
        return (unit for unit in units if unit.faction == faction)

    @staticmethod
    def filter_units_by_distance(me: Wizard, units: Iterable[Unit], distance: float):
        return (unit for unit in units if me.get_distance_to_unit(unit) < distance)

    def move_to_next_way_point(self, me: Wizard, game: Game, move: Move, reverse=False):
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
        move.turn = me.get_angle_to(x, y)
        if abs(move.turn) < game.staff_sector / 2.0:
            # Turn is finished. We can move.
            move.speed = game.wizard_forward_speed
        # Check if we reached the destination.
        if me.get_distance_to(x, y) < me.radius:
            # We reached the destination. Switch the next way point.
            self.way_point_index = self.way_point_index + 1 if not reverse else self.way_point_index - 1
