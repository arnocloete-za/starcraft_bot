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



class Jasper(sc2.BotAI):
    NAME: str = "Jasper"
    RACE: Race = Race.Protoss


    def __init__(self):
        sc2.BotAI.__init__(self)

    async def on_start(self):
        print("Game started")


    async def on_step(self, iteration):

        if iteration % 500 == 0:
            print("interation:" + str(iteration))
        if iteration == 0:
            await self.chat_send("(gg)")
        await self.distribute_workers()
        await self.build_workers()
        await self.scout(iteration)
        await self.build_pylons()
        await self.build_gateway()
        await self.build_gas()
        await self.cyber_core()
        await self.stargate()
        await self.build_gateway_units(iteration)
        await self.build_void_rays()
        #await self.cannon_rush(iteration)
        await self.attack()
        await self.expand_base(iteration)
        await self.chrono_boost()
        pass

    def on_end(self, result):
        print("Game ended")

    async def build_workers(self):
        if self.townhalls:
            nexus = self.townhalls.random
            # Make probes until we have 16 total
            if self.supply_workers < 16 and nexus.is_idle:
                if self.can_afford(UnitTypeId.PROBE):
                    nexus.train(UnitTypeId.PROBE)
            # if nexus.assigned_harvesters < nexus.ideal_harvesters and nexus.is_idle:
            elif self.supply_workers + self.already_pending(
                    UnitTypeId.PROBE) < self.townhalls.amount * 22 and nexus.is_idle:
                if self.can_afford(UnitTypeId.PROBE):
                    nexus.train(UnitTypeId.PROBE)

    async def scout(self,iteration):
        targets = (self.enemy_units | self.enemy_structures).filter(
            lambda unit: unit.can_be_attacked)
        if not targets:
            #print("no targets")
            count_units = self.units(UnitTypeId.ZEALOT).amount + self.units(UnitTypeId.STALKER).amount
            if count_units > 4 and iteration > 2000:
                if self.units(UnitTypeId.ZEALOT):
                    scouter = self.units(UnitTypeId.ZEALOT)[0]
                else:
                    scouter = self.units(UnitTypeId.STALKER)[0]
                if scouter.is_idle:
                    print("!! SCOUT !!")
                    #enemy_location = self.enemy_start_locations[0]
                    move_to = self.random_location_variance()
                    print(move_to)
                    scouter.attack(move_to)

                    # this does not work:await scouter.move(move_to)

    async def build_pylons(self):

        # build first pylon
        if not self.structures(UnitTypeId.PYLON) and not self.already_pending(UnitTypeId.PYLON):
            print("build first pylon")
            own_pos = self.start_location.towards(self.game_info.map_center, random.randrange(8, 15))
            await self.build(UnitTypeId.PYLON, near=own_pos)

                # If we are low on supply, build pylon
        # else after first pylon
        elif (
                self.supply_left < 2
                and self.already_pending(UnitTypeId.PYLON) == 0
                or self.supply_used > 15
                and self.supply_left < 4
                and self.already_pending(UnitTypeId.PYLON) < 2
        ):
            # Always check if you can afford something before you build it
            if self.can_afford(UnitTypeId.PYLON):
                if self.supply_used < 200:
                    if self.structures(UnitTypeId.PYLON).amount > 5:
                        print("build pylons phase3")
                        if self.townhalls.amount > 1:
                            own_pos = self.townhalls[1]
                        else:
                            own_pos = self.start_location.towards(self.game_info.map_center, random.randrange(18, 40))
                    elif self.structures(UnitTypeId.PYLON).amount > 3:
                        print("build pylons phase2")
                        own_pos = self.start_location.towards(self.game_info.map_center, random.randrange(15, 22))
                        # own_pos = self.townhalls.random
                    else:
                        print("build pylons phase1")
                        own_pos = self.start_location.towards(self.game_info.map_center, random.randrange(6, 15))
                    await self.build(UnitTypeId.PYLON, near=own_pos)
            # if self.can_afford(UnitTypeId.PYLON):
            #     own_pos = self.start_location.towards(self.game_info.map_center, random.randrange(8, 15))
            #     if self.supply_used < 200:
            #         await self.build(UnitTypeId.PYLON, near=own_pos)

    async def build_gas(self):
        # Build gas near completed nexuses once we have a cybercore (does not need to be completed
        if self.townhalls:
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

    async def stargate(self):
        # If we have less than 3  but at least 3 nexuses, build stargate
        if self.structures(UnitTypeId.PYLON).ready and self.structures(
                UnitTypeId.CYBERNETICSCORE).ready:
            pylon = self.structures(UnitTypeId.PYLON).ready.random
            if (
                    self.townhalls.ready.amount + self.already_pending(UnitTypeId.NEXUS) >= 2
                    and self.structures(
                UnitTypeId.STARGATE).ready.amount + self.already_pending(
                UnitTypeId.STARGATE) < 5
            ):
                if self.can_afford(UnitTypeId.STARGATE):
                    await self.build(UnitTypeId.STARGATE, near=pylon)


    async def cyber_core(self):
        # Once we have a pylon completed
        # Research warp gate if cybercore is completed
        if (
                self.structures(UnitTypeId.CYBERNETICSCORE).ready
                and self.can_afford(AbilityId.RESEARCH_WARPGATE)
                and self.already_pending_upgrade(UpgradeId.WARPGATERESEARCH) == 0
        ):
            ccore = self.structures(UnitTypeId.CYBERNETICSCORE).ready.first
            ccore.research(UpgradeId.WARPGATERESEARCH)
        elif self.structures(UnitTypeId.PYLON).ready:
            pylon = self.structures(UnitTypeId.PYLON).ready.random
            if self.structures(UnitTypeId.GATEWAY).ready:
                # If we have gateway completed, build cyber core
                if not self.structures(UnitTypeId.CYBERNETICSCORE):
                    if (
                            self.can_afford(UnitTypeId.CYBERNETICSCORE)
                            and self.already_pending(UnitTypeId.CYBERNETICSCORE) == 0
                    ):
                        await self.build(UnitTypeId.CYBERNETICSCORE, near=pylon)
            # else:
            #     # If we have no gateway, build gateway
            #     if self.can_afford(UnitTypeId.GATEWAY) and self.already_pending(
            #             UnitTypeId.GATEWAY) == 0:
            #         await self.build(UnitTypeId.GATEWAY, near=pylon)

    async def build_gateway_units(self, iteration):

        train = False
        count_units = self.units(UnitTypeId.ZEALOT).amount + self.units(UnitTypeId.STALKER).amount
        if iteration < 700 and count_units < 10:
            train = True
        elif 700 < iteration < 900 and count_units < 5:
            train = True
        elif iteration > 900 and self.townhalls.amount >= 2 and self.structures(UnitTypeId.STARGATE).amount > 1 and count_units < 6:
            train = True
        if train:
            if self.structures(UnitTypeId.WARPGATE).ready:

                for warpgate in self.structures(UnitTypeId.WARPGATE).ready:
                    abilities = await self.get_available_abilities(warpgate)
                    # all the units have the same cooldown anyway so let's just look at ZEALOT
                    if AbilityId.WARPGATETRAIN_STALKER in abilities:
                        #print("TRY")
                        enenmy_pos = self.enemy_start_locations[0]
                        #print(enenmy_pos)
                        pylon = self.structures(UnitTypeId.PYLON).ready.random
                        # proxy = self.units(PYLON).closest_to(enenmy_pos)
                        #print(pylon)
                        placement = pylon.position.to2.random_on_distance(4)
                        #print(placement)
                        if placement is None:
                            # return ActionResult.CantFindPlacementLocation
                            print("can't place")
                            return
                        if self.can_afford(UnitTypeId.STALKER):
                            print("warp units now: stalker")
                            warpgate.warp_in(UnitTypeId.STALKER, placement)
                        elif self.can_afford(UnitTypeId.ZEALOT):
                            print("warp units now: zealot")
                            warpgate.warp_in(UnitTypeId.ZEALOT, placement)
            else:
                for sz in self.structures(UnitTypeId.GATEWAY).ready.idle:
                    if self.can_afford(UnitTypeId.ZEALOT):
                        print("train zealot now")
                        sz.train(UnitTypeId.ZEALOT)

    async def build_gateway(self):
        if self.townhalls:
            nexus = self.townhalls.random
            count_buildings = self.structures(UnitTypeId.WARPGATE).amount + self.structures(UnitTypeId.GATEWAY).amount

            if self.can_afford(UnitTypeId.GATEWAY) and count_buildings <= 3 and \
                    not self.already_pending(UnitTypeId.GATEWAY):
                print("build gateway!")
                print(count_buildings)
                # pylon = self.structures(UnitTypeId.PYLON).ready.random
                if not self.structures(UnitTypeId.GATEWAY):
                    await self.build(UnitTypeId.GATEWAY, near=nexus)
                    await self.build(UnitTypeId.GATEWAY, near=nexus)
                else:
                    await self.build(UnitTypeId.GATEWAY, near=nexus)

    async def build_void_rays(self):
        if self.townhalls.amount >= 2:
            for sg in self.structures(UnitTypeId.STARGATE).ready.idle:
                if self.can_afford(UnitTypeId.VOIDRAY):
                    sg.train(UnitTypeId.VOIDRAY)

    async def attack(self):
        count_units = self.units(UnitTypeId.ZEALOT).amount + self.units(UnitTypeId.STALKER).amount
        for zz in self.units(UnitTypeId.ZEALOT):
            targets = (self.enemy_units | self.enemy_structures).filter(
                lambda unit: unit.can_be_attacked)
            if targets:
                target = targets.closest_to(zz)
                #print("attack with zealots 10 now")
                if count_units > 2:
                    zz.attack(target)
            else:
                if count_units > 10:
                    #print("attack with zealots 10 now enemy base")
                    zz.attack(self.enemy_start_locations[0])
        for st in self.units(UnitTypeId.STALKER):
            targets = (self.enemy_units | self.enemy_structures).filter(
                lambda unit: unit.can_be_attacked)
            if targets:
                target = targets.closest_to(st)
                #print("attack with zealots 10 now")
                if count_units > 2:
                    st.attack(target)
            else:
                if count_units > 10:
                    #print("attack with zealots 10 now enemy base")
                    st.attack(self.enemy_start_locations[0])

        # If we have at least 5 void rays, attack closes enemy unit/building, or if none is visible: attack move towards enemy spawn


        #print("attack with voidrays now")
        for vr in self.units(UnitTypeId.VOIDRAY):
            # Activate charge ability if the void ray just attacked
            if vr.weapon_cooldown > 0:
                vr(AbilityId.EFFECT_VOIDRAYPRISMATICALIGNMENT)
            # Choose target and attack, filter out invisible targets
            targets = (self.enemy_units | self.enemy_structures).filter(
                lambda unit: unit.can_be_attacked)
            if targets:
                target = targets.closest_to(vr)
                if self.units(UnitTypeId.VOIDRAY).amount > 1:
                    vr.attack(target)
            else:
                if self.units(UnitTypeId.VOIDRAY).amount > 7:
                    vr.attack(self.enemy_start_locations[0])

    async def expand_base(self, iteration):
        #If  we        have        less        than        3        nexuses and none        pending        yet, expand
        if iteration > 700:
            if self.townhalls.ready.amount + self.already_pending(UnitTypeId.NEXUS) < 3:
                if self.can_afford(UnitTypeId.NEXUS) and not self.already_pending(UnitTypeId.NEXUS):
                    await self.expand_now()
        elif iteration > 2000:
            if self.townhalls.ready.amount + self.already_pending(UnitTypeId.NEXUS) < 6:
                if self.can_afford(UnitTypeId.NEXUS) and not self.already_pending(UnitTypeId.NEXUS):
                    await self.expand_now()

    async def cannon_rush(self, iteration):
        if iteration < 600:
            if self.townhalls:
                nexus = self.townhalls.random
                # If we have no forge, build one near the pylon that is closest to our starting nexus
                if not self.structures(UnitTypeId.FORGE):
                    pylon_ready = self.structures(UnitTypeId.PYLON).ready
                    if pylon_ready:
                        if self.can_afford(UnitTypeId.FORGE):
                            await self.build(UnitTypeId.FORGE, near=pylon_ready.closest_to(nexus))

                # If we have less than 2 pylons, build one at the enemy base
                elif self.structures(UnitTypeId.PYLON).amount < 2:
                    if self.can_afford(UnitTypeId.PYLON):
                        pos = self.enemy_start_locations[0].towards(self.game_info.map_center, random.randrange(8, 15))
                        await self.build(UnitTypeId.PYLON, near=pos)

                # If we have no cannons but at least 2 completed pylons, automatically find a placement location and build them near enemy start location
                elif not self.structures(UnitTypeId.PHOTONCANNON):
                    if self.structures(UnitTypeId.PYLON).ready.amount >= 2 and self.can_afford(UnitTypeId.PHOTONCANNON):
                        pylon = self.structures(UnitTypeId.PYLON).closer_than(20, self.enemy_start_locations[0]).random
                        await self.build(UnitTypeId.PHOTONCANNON, near=pylon)

                # Decide if we should make pylon or cannons, then build them at random location near enemy spawn
                elif self.can_afford(UnitTypeId.PYLON) and self.can_afford(UnitTypeId.PHOTONCANNON):
                    # Ensure "fair" decision
                    for _ in range(20):
                        pos = self.enemy_start_locations[0].random_on_distance(random.randrange(5, 12))
                        building = UnitTypeId.PHOTONCANNON if self.state.psionic_matrix.covers(pos) else UnitTypeId.PYLON
                        await self.build(building, near=pos)


    async def chrono_boost(self):
        if self.townhalls:
            nexus = self.townhalls.random
            # Chrono nexus if cybercore is not ready, else chrono cybercore
            if not self.structures(UnitTypeId.CYBERNETICSCORE).ready:
                if not nexus.has_buff(BuffId.CHRONOBOOSTENERGYCOST) and not nexus.is_idle:
                    if nexus.energy >= 50:
                        nexus(AbilityId.EFFECT_CHRONOBOOSTENERGYCOST, nexus)
            else:
                ccore = self.structures(UnitTypeId.CYBERNETICSCORE).ready.first
                if not ccore.has_buff(BuffId.CHRONOBOOSTENERGYCOST) and not ccore.is_idle:
                    if nexus.energy >= 50:
                        nexus(AbilityId.EFFECT_CHRONOBOOSTENERGYCOST, ccore)

    # functions
    def random_location_variance(self):
        ran = random.randrange(0, len(self.expansion_locations_list))
        enemy_location = self.expansion_locations_list[ran]
        print("next random location")
        print(enemy_location)
        return enemy_location
        # x =  self.enemy_start_location[0]
        # y =  self.enemy_start_location[1]
        #
        # x += ((random.randrange(-20, 20)) / 100) * enemy_start_location[0]
        # y += ((random.randrange(-20, 20)) / 100) * enemy_start_location[1]
        #
        # if x < 0:
        #     x = 0
        # if y < 0:
        #     y = 0
        # if x > self.game_info.map_size[0]:
        #     x = self.game_info.map_size[0]
        # if y > self.game_info.map_size[1]:
        #     y = self.game_info.map_size[1]
        #
        # go_to = position.Point2(position.Pointlike((x, y)))
        # return go_to


class ArnoBot(BotAI):
    async def on_step(self, iteration: int):
        #print(f"This is my bot in iteration {iteration}!")
        await self.distribute_workers()


class HumanPlayerBot(BotAI):
    async def on_step(self, iteration: int):
        print(f"This is my 2nd bot in iteration {iteration}!")


run_game(maps.get("AcropolisLE"), [
    # this works:
    #Human(Race.Protoss),
    #Bot(Race.Protoss, Jasper()),
    #test against ai
    Bot(Race.Protoss, Jasper()),
    Computer(Race.Terran, Difficulty.Easy),
], realtime=False)