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

    # Пути перемещения по карте.
    WAY_POINTS = {
        LaneType.TOP: [
            # Идем наверх.
            (200.0, 3400.0),
            (200.0, 3000.0),
            (200.0, 2600.0),
            (200.0, 2200.0),
            (200.0, 1800.0),
            (200.0, 1400.0),
            (200.0, 1000.0),
            (200.0, 600.0),
            (200.0, 200.0),
            # Идем вправо.
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
            # Обойти базу.
            (200.0, 3400.0),
            (600.0, 3400.0),
            # Бредем по диагонали.
            (1000.0, 3000.0),
            (1400.0, 2600.0),
            (1800.0, 2200.0),
            (2200.0, 1800.0),
            (2600.0, 1400.0),
            (3000.0, 1000.0),
            (3400.0, 600.0),
            # Обходим базу.
            (3400.0, 200.0),
            (3800.0, 200.0),
        ],
        LaneType.BOTTOM: [
            # Идем вправо.
            (600.0, 3800.0),
            (1000.0, 3800.0),
            (1400.0, 3800.0),
            (1800.0, 3800.0),
            (2200.0, 3800.0),
            (2600.0, 3800.0),
            (3000.0, 3800.0),
            (3400.0, 3800.0),
            (3800.0, 3800.0),
            # Идем наверх.
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
        # По умолчанию выбираем случайное направление.
        self.lane_type = random.choice([LaneType.TOP, LaneType.MIDDLE, LaneType.BOTTOM])
        self.way_point_index = 0

    # noinspection PyMethodMayBeStatic
    def move(self, me: Wizard, world: World, game: Game, move: Move):
        # Сначала всякие общие вещи.
        my_player = world.get_my_player()  # type: Player
        opponent_faction = self.opponent_faction_to(my_player.faction)
        skills = set(me.skills)

        # Изучаем следующий навык.
        move.skill_to_learn = self.skill_to_learn(skills)

        # Спасаем свою жизнь.
        if me.life < 0.2 * me.max_life:
            # У нас осталось мало жизни. Отступаем.
            self.move_to_next_way_point(me, game, move, reverse=True)
            return
        allies_life = sum(map(operator.attrgetter("life"), itertools.chain(
            self.filter_units(world.minions, me.faction),
            self.filter_units(world.wizards, me.faction),
        )))
        enemies_life = sum(map(operator.attrgetter("life"), itertools.chain(
            self.filter_units(world.minions, opponent_faction),
            self.filter_units(world.wizards, opponent_faction),
        )))
        if enemies_life > 2.0 * allies_life:
            # Враги сильнее, спасаемся бегством.
            self.move_to_next_way_point(me, game, move, reverse=True)
            return
        # Обнаруживаем цели.
        targets = list(itertools.chain(
            self.filter_units(world.minions, opponent_faction),
            self.filter_units(world.wizards, opponent_faction),
            self.filter_units(world.buildings, opponent_faction),
        ))
        if targets:
            # Просто ищем ближайшую цель.
            target = min(targets, key=(lambda target_: me.get_distance_to_unit(target_)))
            action_type, min_cast_distance = self.check_attack_distance(me, game, skills, target)
            is_oriented, cast_angle = self.is_oriented_to_unit(me, game, target)
            if action_type != ActionType.NONE:
                # Можем что-то кастануть.
                if is_oriented:
                    # Атаковать.
                    move.cast_angle = cast_angle
                    move.action = action_type
                    move.min_cast_distance = min_cast_distance
                    return
                # Поворачиваемся на врага.
                move.turn = me.get_angle_to_unit(target)
                return
        # Просто двигаемся вперед.
        self.move_to_next_way_point(me, game, move)

    @staticmethod
    def opponent_faction_to(faction: Faction):
        """
        Возвращает фракцию противника.
        """
        return Faction.ACADEMY if faction == Faction.RENEGADES else Faction.RENEGADES

    @staticmethod
    def is_oriented_to_unit(me: Wizard, game: Game, unit: CircularUnit) -> (bool, float):
        """
        Проверяет, наведен ли маг на цель.
        """
        angle_to_unit = me.get_angle_to_unit(unit)
        cast_angle = abs(angle_to_unit) - math.atan(unit.radius / me.get_distance_to_unit(unit))
        if cast_angle < 0.0:
            # Уже смотрим в сторону противника. Можно стрелять прямо перед собой.
            return True, 0.0
        # Пробуем стрелять под углом.
        if cast_angle < game.staff_sector / 2.0:
            # Кастуем в ту же сторону, что и угол до цели.
            return True, math.copysign(cast_angle, angle_to_unit)
        # :(
        return False, None

    @staticmethod
    def check_attack_distance(me: Wizard, game: Game, skills: Set[SkillType], unit: CircularUnit) -> (ActionType, float):
        """
        Проверяет расстояние до цели и возвращает тип действия для атаки.
        """
        distance_to_unit = me.get_distance_to_unit(unit)
        min_cast_distance = distance_to_unit - unit.radius
        if distance_to_unit < game.staff_range:
            # Бьем посохом в ближнем бою.
            return ActionType.STAFF, min_cast_distance
        if distance_to_unit > me.cast_range:
            # Слишком далеко.
            return ActionType.NONE, min_cast_distance
        # Пытаемся кастануть магию.
        if SkillType.FIREBALL in skills and me.mana > game.fireball_manacost:
            return ActionType.FIREBALL, min_cast_distance
        if SkillType.FROST_BOLT in skills and me.mana > game.frost_bolt_manacost:
            return ActionType.FROST_BOLT, min_cast_distance
        if me.mana > game.magic_missile_manacost:
            return ActionType.MAGIC_MISSILE, min_cast_distance
        # Ничего не выходит.
        return ActionType.NONE, min_cast_distance

    @staticmethod
    def skill_to_learn(skills: Set[SkillType]) -> SkillType:
        """
        Возвращает следующий навык для изучения.
        """
        for skill in MyStrategy.SKILL_ORDER:
            # Просто ищем первый не изученный навык в порядке приоритета.
            if skill not in skills:
                return skill

    @staticmethod
    def filter_units(units: Iterable[Unit], faction: Faction):
        """
        Фильтрует юниты по фракции.
        """
        return (unit for unit in units if unit.faction == faction)

    def move_to_next_way_point(self, me: Wizard, game: Game, move: Move, reverse=False):
        """
        Движение к следующей ключевой точке.
        """
        way_points = MyStrategy.WAY_POINTS[self.lane_type]
        if me.x < 400.0 and me.y > 3600.0:
            # Появились возле базы.
            self.way_point_index = 0
        if self.way_point_index <= -1 or self.way_point_index >= len(way_points):
            # Достигли крайней точки. Стоим на месте.
            return
        # Двигаемся в сторону точки назначения.
        x, y = way_points[self.way_point_index]
        move.turn = me.get_angle_to(x, y)
        if abs(move.turn) < game.staff_sector / 2.0:
            # Повернулись на точку, можно идти.
            move.speed = game.wizard_forward_speed
        # Проверяем достижение точки назначения.
        if me.get_distance_to(x, y) < me.radius:
            # Достигли точки назначения, берем следующую или предыдущую.
            self.way_point_index = self.way_point_index + 1 if not reverse else self.way_point_index - 1
