#!/usr/bin/env python3
# coding: utf-8

import math

from model.ActionType import ActionType
from model.BuildingType import BuildingType
from model.CircularUnit import CircularUnit
from model.Game import Game
from model.Move import Move
from model.Player import Player
from model.Wizard import Wizard
from model.World import World


class MyStrategy:
    OPPONENT_FACTION_BASE_X = 4000.0 - 400.0
    OPPONENT_FACTION_BASE_Y = 400.0

    def __init__(self):
        self.ally_id = None

    def move(self, me: Wizard, world: World, game: Game, move: Move):
        my_player = world.get_my_player()  # type: Player
        min_ally_distance = game.wizard_radius * 3.0
        max_ally_distance = game.wizard_radius * 6.0
        wizards = {wizard.id: wizard for wizard in world.wizards}

        if self.ally_id is None or self.ally_id not in wizards or wizards[self.ally_id].life < 10.0:
            allies = [
                wizard
                for wizard in world.wizards
                if wizard.faction == my_player.faction and wizard.owner_player_id != my_player.id
            ]
            self.ally_id = min(allies, key=(lambda wizard: me.get_distance_to_unit(wizard))).id
        ally = wizards[self.ally_id]

        targets = list(world.trees)
        if me.get_distance_to_unit(ally) > max_ally_distance:
            move.turn = me.get_angle_to_unit(ally)
            move.speed = game.wizard_forward_speed
        elif me.get_distance_to_unit(ally) < min_ally_distance:
            move.turn = me.get_angle_to_unit(ally)
            move.speed = -game.wizard_backward_speed
        else:
            enemies = [wizard for wizard in world.wizards if wizard.faction != my_player.faction]
            enemies.extend(minion for minion in world.minions if minion.faction != my_player.faction)
            if enemies:
                enemy = min(enemies, key=(lambda target_: me.get_distance_to_unit(target_)))
                if me.get_distance_to_unit(enemy) < me.cast_range:
                    move.turn = me.get_angle_to_unit(enemy)
                    targets.append(enemy)
            else:
                tree = min(world.trees, key=(lambda tree_: me.get_distance_to_unit(tree_)))
                if me.get_distance_to_unit(tree) < (me.radius + tree.radius + 10.0):
                    move.turn = me.get_angle_to_unit(tree)

        for target in targets:
            if me.get_distance_to_unit(target) < me.cast_range:
                if abs(me.get_angle_to_unit(target)) < math.atan(target.radius / me.get_distance_to_unit(target)):
                    move.action = ActionType.MAGIC_MISSILE
                    break
