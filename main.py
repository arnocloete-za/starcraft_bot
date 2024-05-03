import sc2
from sc2.bot_ai import BotAI
from sc2 import run_game, maps, Race, Difficulty, position
from sc2.player import Bot, Computer, Human
from sc2.constants import NEXUS, PROBE, PYLON, GATEWAY
import random


from sc2 import Race, Difficulty
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.ids.upgrade_id import UpgradeId
from sc2.ids.buff_id import BuffId
from sc2.unit import Unit
from sc2.units import Units
from sc2.position import Point2



class CannonRushBot(sc2.BotAI):
    def random_location_variance(self, enemy_start_location):
        x = enemy_start_location[0]
        y = enemy_start_location[1]

        x += ((random.randrange(-20, 20)) / 100) * enemy_start_location[0]
        y += ((random.randrange(-20, 20)) / 100) * enemy_start_location[1]

        if x < 0:
            x = 0
        if y < 0:
            y = 0
        if x > self.game_info.map_size[0]:
            x = self.game_info.map_size[0]
        if y > self.game_info.map_size[1]:
            y = self.game_info.map_size[1]

        go_to = position.Point2(position.Pointlike((x, y)))
        return go_to

    async def on_step(self, iteration):
        # targets = (self.enemy_units | self.enemy_structures).filter(
        #     lambda unit: unit.can_be_attacked)
        # if not targets:
        #     if self.units(UnitTypeId.ZEALOT):
        #         scouter = self.units(UnitTypeId.ZEALOT)[0]
        #         if scouter.is_idle:
        #             print("!! SCOUT !!")
        #             enemy_location = self.enemy_start_locations[0]
        #             move_to = self.random_location_variance(enemy_location)
        #             print(move_to)
        #             scouter.attack(move_to)
                #await scouter.move(move_to)
        if iteration < 600:
            print("interation:" + str(iteration))
        if iteration == 0:
            await self.chat_send("(probe)(pylon)(cannon)(cannon)(gg)")

        if not self.townhalls:
            # Attack with all workers if we don't have any nexuses left, attack-move on enemy spawn (doesn't work on 4 player map) so that probes auto attack on the way
            for worker in self.workers:
                worker.attack(self.enemy_start_locations[0])
            return
        else:
            nexus = self.townhalls.random

        # Make probes until we have 16 total
        if self.supply_workers < 20 and nexus.is_idle:
            if self.can_afford(UnitTypeId.PROBE):
                nexus.train(UnitTypeId.PROBE)

        # If we have no pylon, build one near starting nexus
        elif not self.structures(UnitTypeId.PYLON) and not self.already_pending(UnitTypeId.PYLON):
            if self.can_afford(UnitTypeId.PYLON):
                own_pos = self.start_location.towards(self.game_info.map_center, random.randrange(8, 15))
                if self.supply_used < 200:
                    await self.build(UnitTypeId.PYLON, near=own_pos)

        # If we have no forge, build one near the pylon that is closest to our starting nexus
        elif not self.structures(UnitTypeId.FORGE):
            pylon_ready = self.structures(UnitTypeId.PYLON).ready
            if pylon_ready:
                if self.can_afford(UnitTypeId.FORGE):
                    await self.build(UnitTypeId.FORGE, near=pylon_ready.closest_to(nexus))

        # If we have less than 2 pylons, build one at the enemy base
        elif self.structures(UnitTypeId.PYLON).amount < 3 and not self.already_pending(UnitTypeId.PYLON) and iteration < 300:
            print("build pylon")
            if self.can_afford(UnitTypeId.PYLON):
                pos = self.enemy_start_locations[0].towards(self.game_info.map_center, random.randrange(8, 15))
                if self.supply_used < 200:
                    own_pos = self.start_location.towards(self.game_info.map_center, random.randrange(8, 15))
                    await self.build(UnitTypeId.PYLON, near=own_pos)

        # If we have no cannons but at least 2 completed pylons, automatically find a placement location and build them near enemy start location
        elif not self.structures(UnitTypeId.PHOTONCANNON) and not self.already_pending(UnitTypeId.PHOTONCANNON) and iteration < 300:
            print("Build first canon")
            if self.structures(UnitTypeId.PYLON).ready.amount >= 1 and self.can_afford(UnitTypeId.PHOTONCANNON):
                try:
                    pylon = self.structures(UnitTypeId.PYLON).closer_than(20, self.enemy_start_locations[0]).random
                    own_pos = self.start_location.towards(self.game_info.map_center, random.randrange(8, 15))
                    await self.build(UnitTypeId.PHOTONCANNON, near=own_pos)
                    # count_cannons = count_cannons + 1
                    # print("count_cannons")
                    # print(count_cannons)
                except:
                    print("except")
                    pos = self.enemy_start_locations[0].towards(self.game_info.map_center, random.randrange(8, 15))
                    if self.supply_used < 200:
                        await self.build(UnitTypeId.PYLON, near=pos)


        # Decide if we should make pylon or cannons, then build them at random location near enemy spawn
        elif self.structures(UnitTypeId.PHOTONCANNON).ready.amount <= 3 and not self.already_pending(UnitTypeId.PHOTONCANNON) and iteration < 600:
            print("build more cannons")
            print(self.structures(UnitTypeId.PHOTONCANNON).ready.amount)
            print(self.already_pending(UnitTypeId.PHOTONCANNON))
            # Ensure "fair" decision
            if self.can_afford(UnitTypeId.PYLON) and self.can_afford(UnitTypeId.PHOTONCANNON):
                for _ in range(20):
                    pos = self.enemy_start_locations[0].random_on_distance(random.randrange(5, 12))
                    building = UnitTypeId.PHOTONCANNON if self.state.psionic_matrix.covers(pos) else UnitTypeId.PYLON
                    await self.build(building, near=pos)
        elif self.units(UnitTypeId.ZEALOT).amount < 10:
            print("less 10 zealots")
            # If we are low on supply, build pylon
            if (
                    self.supply_left < 2
                    and self.already_pending(UnitTypeId.PYLON) == 0
                    or self.supply_used > 15
                    and self.supply_left < 4
                    and self.already_pending(UnitTypeId.PYLON) < 2
            ):
                # Always check if you can afford something before you build it
                if self.can_afford(UnitTypeId.PYLON):
                    if self.supply_used < 200:
                        await self.build(UnitTypeId.PYLON, near=nexus)
            if self.can_afford(UnitTypeId.GATEWAY) and self.structures(UnitTypeId.GATEWAY).ready.amount <= 3:
                print("build gateway")
                print(self.structures(UnitTypeId.GATEWAY).ready.amount)
                #pylon = self.structures(UnitTypeId.PYLON).ready.random
                await self.build(UnitTypeId.GATEWAY, near=nexus)
                if self.can_afford(UnitTypeId.PYLON):
                    pos = self.enemy_start_locations[0].towards(self.game_info.map_center, random.randrange(8, 15))
                    if self.supply_used < 200:
                        await self.build(UnitTypeId.PYLON, near=pos)
            else:
                print("zealots")
                if self.can_afford(UnitTypeId.ZEALOT):
                    if self.units(UnitTypeId.ZEALOT).amount < 10:
                        print("train zealot now")
                        for sz in self.structures(UnitTypeId.GATEWAY).ready.idle:
                            if self.can_afford(UnitTypeId.ZEALOT):
                                sz.train(UnitTypeId.ZEALOT)


        else:
            print("attack with zealots 2")
            for zz in self.units(UnitTypeId.ZEALOT):

                targets = (self.enemy_units | self.enemy_structures).filter(
                    lambda unit: unit.can_be_attacked)
                if targets:
                    target = targets.closest_to(zz)
                    zz.attack(target)
                else:
                    zz.attack(self.enemy_start_locations[0])
            # If we have at least 5 void rays, attack closes enemy unit/building, or if none is visible: attack move towards enemy spawn
            print("voidray")
            if self.units(UnitTypeId.VOIDRAY).amount > 5:
                for vr in self.units(UnitTypeId.VOIDRAY):
                    # Activate charge ability if the void ray just attacked
                    if vr.weapon_cooldown > 0:
                        vr(AbilityId.EFFECT_VOIDRAYPRISMATICALIGNMENT)
                    # Choose target and attack, filter out invisible targets
                    targets = (self.enemy_units | self.enemy_structures).filter(
                        lambda unit: unit.can_be_attacked)
                    if targets:
                        target = targets.closest_to(vr)
                        vr.attack(target)
                   # else:
                  #      vr.attack(self.enemy_start_locations[0])

            # Distribute workers in gas and across bases
            await self.distribute_workers()

            # If we are low on supply, build pylon
            if (
                    self.supply_left < 2
                    and self.already_pending(UnitTypeId.PYLON) == 0
                    or self.supply_used > 15
                    and self.supply_left < 4
                    and self.already_pending(UnitTypeId.PYLON) < 2
            ):
                # Always check if you can afford something before you build it
                if self.can_afford(UnitTypeId.PYLON):
                    if self.supply_used < 200:
                        await self.build(UnitTypeId.PYLON, near=nexus)

            # Train probe on nexuses that are undersaturated (avoiding distribute workers functions)
            # if nexus.assigned_harvesters < nexus.ideal_harvesters and nexus.is_idle:
            if self.supply_workers + self.already_pending(
                    UnitTypeId.PROBE) < self.townhalls.amount * 22 and nexus.is_idle:
                if self.can_afford(UnitTypeId.PROBE):
                    nexus.train(UnitTypeId.PROBE)

            # If we have less than 3 nexuses and none pending yet, expand
            if self.townhalls.ready.amount + self.already_pending(UnitTypeId.NEXUS) < 3:
                if self.can_afford(UnitTypeId.NEXUS):
                    await self.expand_now()

            # Once we have a pylon completed
            if self.structures(UnitTypeId.PYLON).ready:
                pylon = self.structures(UnitTypeId.PYLON).ready.random
                if self.structures(UnitTypeId.GATEWAY).ready:
                    # If we have gateway completed, build cyber core
                    if not self.structures(UnitTypeId.CYBERNETICSCORE):
                        if (
                                self.can_afford(UnitTypeId.CYBERNETICSCORE)
                                and self.already_pending(UnitTypeId.CYBERNETICSCORE) == 0
                        ):
                            await self.build(UnitTypeId.CYBERNETICSCORE, near=pylon)
                else:
                    # If we have no gateway, build gateway
                    if self.can_afford(UnitTypeId.GATEWAY) and self.already_pending(
                            UnitTypeId.GATEWAY) == 0:
                        await self.build(UnitTypeId.GATEWAY, near=pylon)

            # Build gas near completed nexuses once we have a cybercore (does not need to be completed
            if self.structures(UnitTypeId.CYBERNETICSCORE):
                for nexus in self.townhalls.ready:
                    vgs = self.vespene_geyser.closer_than(15, nexus)
                    for vg in vgs:
                        if not self.can_afford(UnitTypeId.ASSIMILATOR):
                            break

                        worker = self.select_build_worker(vg.position)
                        if worker is None:
                            break

                        if not self.gas_buildings or not self.gas_buildings.closer_than(1, vg):
                            worker.build(UnitTypeId.ASSIMILATOR, vg)
                            worker.stop(queue=True)

            # If we have less than 3  but at least 3 nexuses, build stargate
            if self.structures(UnitTypeId.PYLON).ready and self.structures(
                    UnitTypeId.CYBERNETICSCORE).ready:
                pylon = self.structures(UnitTypeId.PYLON).ready.random
                if (
                        self.townhalls.ready.amount + self.already_pending(UnitTypeId.NEXUS) >= 3
                        and self.structures(
                    UnitTypeId.STARGATE).ready.amount + self.already_pending(
                    UnitTypeId.STARGATE) < 3
                ):
                    if self.can_afford(UnitTypeId.STARGATE):
                        await self.build(UnitTypeId.STARGATE, near=pylon)

            # Save up for expansions, loop over idle completed stargates and queue void ray if we can afford
            if self.townhalls.amount >= 3:
                for sg in self.structures(UnitTypeId.STARGATE).ready.idle:
                    if self.can_afford(UnitTypeId.VOIDRAY):
                        sg.train(UnitTypeId.VOIDRAY)


class ArnoBot(BotAI):
    async def on_step(self, iteration: int):
        #print(f"This is my bot in iteration {iteration}!")
        await self.distribute_workers()
    #     await self.select_build_worker(self)
    #     await self.build_pylons(self)
    #
    # async def build_workers(self):
    #     for nexus in self.units(NEXUS).ready.noqueue:
    #         if self.can_afford(PROBE):
    #             await self.do(nexus.train(PROBE))
    #
    # async def build_pylons(self):
    #     if self.supply_left < 5 and not self.already_pending(PYLON):
    #         nexuses = self.units(NEXUS).ready
    #         if nexuses.exists:
    #             if self.can_afford(PYLON):
    #                 await self.build(PYLON, near=nexuses.first)

class HumanPlayerBot(BotAI):
    async def on_step(self, iteration: int):
        print(f"This is my 2nd bot in iteration {iteration}!")
run_game(maps.get("AcropolisLE"), [

    # this works:
    Human(Race.Terran),
    Bot(Race.Protoss, CannonRushBot()),

    #test against ai
    #Bot(Race.Protoss, CannonRushBot()),
    #Computer(Race.Terran, Difficulty.Hard),


    #Computer(Race.Terran, Difficulty.Easy)
], realtime=True)