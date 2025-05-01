import numpy as np
import random
import copy
import time
import json
from collections import defaultdict
import sys
sys.stdout.reconfigure(encoding='utf-8')

class Instance:
    def __init__(self):
        """
        Initialisation d'une instance du problème de transport par navettes entre les sites A et B
        sur un horizon de 12 semaines.
        """
        # Horizon de planification: 12 semaines
        self.T = list(range(1, 13))
        self.np = 12
        
        # Types de véhicules disponibles
        self.L = {
            1: {"Qw": 150, "Qv": 70},  # Véhicule de capacité moyenne
            2: {"Qw": 300, "Qv": 120}  # Véhicule de grande capacité
        }
        
        # Nombre maximal de véhicules disponibles par type
        self.m = {
            1: 6,  # 6 véhicules de type 1
            2: 4   # 4 véhicules de type 2
        }
        
        # Coût d'utilisation de chaque type de véhicule
        self.c = {
            1: 100,  # Coût du véhicule de type 1
            2: 180   # Coût du véhicule de type 2
        }
        
        # Coût de déplacement entre les sites (indépendant du type de véhicule)
        self.dc = 50
        
        # Demandes hebdomadaires (poids et volume)
        # Initialiser les demandes pour 12 semaines
        self.dw_AB = {}  # Demandes en poids de A vers B
        self.dv_AB = {}  # Demandes en volume de A vers B
        self.dw_BA = {}  # Demandes en poids de B vers A
        self.dv_BA = {}  # Demandes en volume de B vers A
        
        # Générer des demandes aléatoires mais réalistes
        for t in self.T:
            # Variation hebdomadaire pour rendre le problème plus réaliste
            week_factor_AB = 0.9 + 0.2 * random.random()
            week_factor_BA = 0.9 + 0.2 * random.random()
            
            # Demandes de A vers B
            self.dw_AB[t] = int(100 * week_factor_AB)  # Demande en poids base 100
            self.dv_AB[t] = int(40 * week_factor_AB)   # Demande en volume base 40
            
            # Demandes de B vers A
            self.dw_BA[t] = int(120 * week_factor_BA)  # Demande en poids base 120
            self.dv_BA[t] = int(50 * week_factor_BA)   # Demande en volume base 50

class Vehicle:
    def __init__(self, vtype):
        """
        Représente un véhicule spécifique
        
        Args:
            vtype: Type de véhicule (entier)
        """
        self.type = vtype
        self.weeks_used = set()  # Semaines où ce véhicule est utilisé
        
    def is_used(self):
        """Retourne True si le véhicule est utilisé au moins une fois"""
        return len(self.weeks_used) > 0

class Transport:
    def __init__(self, week, vehicle_idx, vehicle_type, weight_AB=0, volume_AB=0, weight_BA=0, volume_BA=0):
        """
        Représente un transport effectué par un véhicule pendant une semaine donnée
        
        Args:
            week: Semaine du transport
            vehicle_idx: Indice du véhicule utilisé
            vehicle_type: Type du véhicule
            weight_AB: Quantité en poids transportée de A vers B
            volume_AB: Quantité en volume transportée de A vers B
            weight_BA: Quantité en poids transportée de B vers A
            volume_BA: Quantité en volume transportée de B vers A
        """
        self.week = week
        self.vehicle_idx = vehicle_idx
        self.vehicle_type = vehicle_type
        self.weight_AB = weight_AB
        self.volume_AB = volume_AB
        self.weight_BA = weight_BA
        self.volume_BA = volume_BA
    
    def __str__(self):
        return f"Transport(semaine={self.week}, véhicule={self.vehicle_idx}(type {self.vehicle_type}), " \
               f"AB: {self.weight_AB}kg/{self.volume_AB}m³, BA: {self.weight_BA}kg/{self.volume_BA}m³)"

class Solution:
    def __init__(self, instance):
        """
        Représente une solution au problème de transport
        
        Args:
            instance: Instance du problème
        """
        self.instance = instance
        self.vehicles = {}  # Dictionnaire: clé = (type, idx), valeur = Vehicle
        self.transports = []  # Liste des transports effectués
        self.fitness = float('inf')
        self.feasible = False
        
        # Initialiser les véhicules disponibles
        for vtype, count in instance.m.items():
            for i in range(1, count + 1):
                self.vehicles[(vtype, i)] = Vehicle(vtype)
    
    def evaluate(self):
        """
        Évalue la solution en calculant la fonction objectif et en vérifiant sa faisabilité
        
        Returns:
            float: Valeur de la fonction objectif (nombre de véhicules utilisés)
        """
        # Réinitialiser les semaines d'utilisation des véhicules
        for vehicle in self.vehicles.values():
            vehicle.weeks_used.clear()
        
        # Marquer les semaines d'utilisation de chaque véhicule
        for transport in self.transports:
            self.vehicles[(transport.vehicle_type, transport.vehicle_idx)].weeks_used.add(transport.week)
        
        # Compter le nombre de véhicules utilisés (ceux utilisés au moins une fois)
        vehicles_used = sum(1 for vehicle in self.vehicles.values() if vehicle.is_used())
        
        # Vérifier la satisfaction des demandes
        self.feasible = self.check_demands_satisfaction()
        
        # Mettre à jour la fitness (objectif: minimiser le nombre de véhicules)
        self.fitness = vehicles_used if self.feasible else float('inf')
        
        return self.fitness
    
    def check_demands_satisfaction(self):
        """
        Vérifie si toutes les demandes sont satisfaites
        
        Returns:
            bool: True si toutes les demandes sont satisfaites, False sinon
        """
        # Calculer les quantités transportées par semaine
        transported_weight_AB = defaultdict(float)
        transported_volume_AB = defaultdict(float)
        transported_weight_BA = defaultdict(float)
        transported_volume_BA = defaultdict(float)
        
        for transport in self.transports:
            week = transport.week
            transported_weight_AB[week] += transport.weight_AB
            transported_volume_AB[week] += transport.volume_AB
            transported_weight_BA[week] += transport.weight_BA
            transported_volume_BA[week] += transport.volume_BA
        
        # Vérifier si toutes les demandes sont satisfaites
        for week in self.instance.T:
            if transported_weight_AB[week] < self.instance.dw_AB[week]:
                return False
            if transported_volume_AB[week] < self.instance.dv_AB[week]:
                return False
            if transported_weight_BA[week] < self.instance.dw_BA[week]:
                return False
            if transported_volume_BA[week] < self.instance.dv_BA[week]:
                return False
        
        return True
    
    def total_cost(self):
        """
        Calcule le coût total de transport (objectif secondaire)
        
        Returns:
            float: Coût total de transport
        """
        cost = 0
        for transport in self.transports:
            # Coût d'utilisation du véhicule + coût de déplacement
            cost += self.instance.c[transport.vehicle_type] + self.instance.dc
        
        return cost
    
    def __str__(self):
        vehicles_used = sum(1 for vehicle in self.vehicles.values() if vehicle.is_used())
        return f"Solution(transports={len(self.transports)}, véhicules utilisés={vehicles_used}, " \
               f"fitness={self.fitness}, faisable={self.feasible})"
    
    def detailed_str(self):
        """
        Retourne une représentation détaillée de la solution
        
        Returns:
            str: Description détaillée de la solution
        """
        result = [f"Solution avec {len(self.transports)} transports, fitness={self.fitness}, faisable={self.feasible}"]
        
        # Afficher les véhicules utilisés par type
        vehicles_by_type = defaultdict(int)
        for (vtype, _), vehicle in self.vehicles.items():
            if vehicle.is_used():
                vehicles_by_type[vtype] += 1
        
        result.append("Véhicules utilisés par type:")
        for vtype, count in vehicles_by_type.items():
            result.append(f"  Type {vtype}: {count} véhicules")
        
        # Afficher le détail des transports par semaine
        transports_by_week = defaultdict(list)
        for transport in self.transports:
            transports_by_week[transport.week].append(transport)
        
        result.append("\nDétail des transports par semaine:")
        for week in sorted(transports_by_week.keys()):
            result.append(f"  Semaine {week}:")
            for transport in transports_by_week[week]:
                result.append(f"    {transport}")
        
        return "\n".join(result)

def greedy_initial_solution(instance):
    """
    Crée une solution initiale en utilisant une heuristique gloutonne
    
    Args:
        instance: Instance du problème
        
    Returns:
        Solution: Solution initiale
    """
    solution = Solution(instance)
    
    # Pour chaque semaine
    for week in instance.T:
        # Initialiser les demandes restantes pour cette semaine
        remaining_weight_AB = instance.dw_AB[week]
        remaining_volume_AB = instance.dv_AB[week]
        remaining_weight_BA = instance.dw_BA[week]
        remaining_volume_BA = instance.dv_BA[week]
        
        # Trier les types de véhicules par ratio (capacité/coût) décroissant
        vehicle_types = sorted(instance.L.keys(), 
                              key=lambda vt: (instance.L[vt]["Qw"] + instance.L[vt]["Qv"]) / instance.c[vt], 
                              reverse=True)
        
        # Tant qu'il reste des demandes à satisfaire
        while (remaining_weight_AB > 0 or remaining_volume_AB > 0 or 
               remaining_weight_BA > 0 or remaining_volume_BA > 0):
            vehicle_assigned = False
            
            # Essayer chaque type de véhicule
            for vtype in vehicle_types:
                capacity_w = instance.L[vtype]["Qw"]
                capacity_v = instance.L[vtype]["Qv"]
                
                # Vérifier si ce type peut encore satisfaire une partie des demandes
                if ((remaining_weight_AB > 0 or remaining_volume_AB > 0 or 
                     remaining_weight_BA > 0 or remaining_volume_BA > 0) and
                    (remaining_weight_AB + remaining_weight_BA <= capacity_w or 
                     remaining_volume_AB + remaining_volume_BA <= capacity_v)):
                    
                    # Chercher un véhicule disponible de ce type
                    vehicle_found = False
                    for veh_idx in range(1, instance.m[vtype] + 1):
                        vehicle_key = (vtype, veh_idx)
                        
                        # Vérifier si ce véhicule n'est pas déjà utilisé cette semaine
                        if week not in solution.vehicles[vehicle_key].weeks_used:
                            # Calculer les quantités à transporter
                            weight_to_AB = min(remaining_weight_AB, capacity_w)
                            volume_to_AB = min(remaining_volume_AB, capacity_v)
                            
                            # Calculer la capacité restante pour B->A
                            remaining_capacity_w = capacity_w - weight_to_AB
                            remaining_capacity_v = capacity_v - volume_to_AB
                            
                            weight_to_BA = min(remaining_weight_BA, remaining_capacity_w)
                            volume_to_BA = min(remaining_volume_BA, remaining_capacity_v)
                            
                            # Créer le transport
                            transport = Transport(
                                week=week,
                                vehicle_idx=veh_idx,
                                vehicle_type=vtype,
                                weight_AB=weight_to_AB,
                                volume_AB=volume_to_AB,
                                weight_BA=weight_to_BA,
                                volume_BA=volume_to_BA
                            )
                            
                            # Mettre à jour la solution
                            solution.transports.append(transport)
                            solution.vehicles[vehicle_key].weeks_used.add(week)
                            
                            # Mettre à jour les demandes restantes
                            remaining_weight_AB -= weight_to_AB
                            remaining_volume_AB -= volume_to_AB
                            remaining_weight_BA -= weight_to_BA
                            remaining_volume_BA -= volume_to_BA
                            
                            vehicle_found = True
                            vehicle_assigned = True
                            break
                    
                    if vehicle_found:
                        break
            
            # Si aucun véhicule n'a pu être assigné, c'est que la solution est infaisable
            if not vehicle_assigned:
                # Dans ce cas, on crée un transport artificiel avec un véhicule du plus grand type
                vtype = max(vehicle_types)
                veh_idx = 1  # On prend arbitrairement le premier véhicule
                
                # Calculer les quantités restantes
                weight_to_AB = remaining_weight_AB
                volume_to_AB = remaining_volume_AB
                weight_to_BA = remaining_weight_BA
                volume_to_BA = remaining_volume_BA
                
                # Créer un transport spécial (qui dépassera les capacités)
                transport = Transport(
                    week=week,
                    vehicle_idx=veh_idx,
                    vehicle_type=vtype,
                    weight_AB=weight_to_AB,
                    volume_AB=volume_to_AB,
                    weight_BA=weight_to_BA,
                    volume_BA=volume_to_BA
                )
                
                solution.transports.append(transport)
                solution.vehicles[(vtype, veh_idx)].weeks_used.add(week)
                
                # Mettre à jour les demandes restantes
                remaining_weight_AB = 0
                remaining_volume_AB = 0
                remaining_weight_BA = 0
                remaining_volume_BA = 0
    
    # Évaluer la solution
    solution.evaluate()
    return solution

def crossover(parent1, parent2, instance):
    """
    Opérateur de croisement qui combine les transports des deux parents
    
    Args:
        parent1: Première solution parent
        parent2: Deuxième solution parent
        instance: Instance du problème
        
    Returns:
        Solution: Solution enfant
    """
    child = Solution(instance)
    
    # Pour chaque semaine, choisir aléatoirement les transports d'un des parents
    for week in instance.T:
        parent = parent1 if random.random() < 0.5 else parent2
        # Copier les transports de cette semaine
        for transport in parent.transports:
            if transport.week == week:
                # Créer une copie du transport
                new_transport = Transport(
                    week=transport.week,
                    vehicle_idx=transport.vehicle_idx,
                    vehicle_type=transport.vehicle_type,
                    weight_AB=transport.weight_AB,
                    volume_AB=transport.volume_AB,
                    weight_BA=transport.weight_BA,
                    volume_BA=transport.volume_BA
                )
                child.transports.append(new_transport)
    
    # Évaluer l'enfant
    child.evaluate()
    
    # Si l'enfant n'est pas faisable, réparer la solution
    if not child.feasible:
        repair_solution(child, instance)
    
    return child

def repair_solution(solution, instance):
    """
    Répare une solution infaisable en ajoutant des transports supplémentaires si nécessaire
    
    Args:
        solution: Solution à réparer
        instance: Instance du problème
    """
    for week in instance.T:
        # Calculer les quantités déjà transportées cette semaine
        transported_weight_AB = sum(t.weight_AB for t in solution.transports if t.week == week)
        transported_volume_AB = sum(t.volume_AB for t in solution.transports if t.week == week)
        transported_weight_BA = sum(t.weight_BA for t in solution.transports if t.week == week)
        transported_volume_BA = sum(t.volume_BA for t in solution.transports if t.week == week)
        
        # Calculer les demandes restantes
        remaining_weight_AB = max(0, instance.dw_AB[week] - transported_weight_AB)
        remaining_volume_AB = max(0, instance.dv_AB[week] - transported_volume_AB)
        remaining_weight_BA = max(0, instance.dw_BA[week] - transported_weight_BA)
        remaining_volume_BA = max(0, instance.dv_BA[week] - transported_volume_BA)
        
        # S'il reste des demandes à satisfaire
        if (remaining_weight_AB > 0 or remaining_volume_AB > 0 or 
            remaining_weight_BA > 0 or remaining_volume_BA > 0):
            
            # Chercher un véhicule disponible pour satisfaire les demandes restantes
            # Préférer les véhicules déjà utilisés pour minimiser le nombre total
            vehicles_used_this_week = {(t.vehicle_type, t.vehicle_idx) for t in solution.transports if t.week == week}
            
            # Trier les véhicules: d'abord ceux déjà utilisés dans d'autres semaines, puis les autres
            vehicles_by_priority = []
            
            # D'abord, les véhicules déjà utilisés dans d'autres semaines (mais pas celle-ci)
            for (vtype, idx), vehicle in solution.vehicles.items():
                if vehicle.is_used() and (vtype, idx) not in vehicles_used_this_week:
                    vehicles_by_priority.append((vtype, idx))
            
            # Ensuite, les véhicules jamais utilisés
            for (vtype, idx), vehicle in solution.vehicles.items():
                if not vehicle.is_used():
                    vehicles_by_priority.append((vtype, idx))
            
            # Trier par capacité décroissante au sein de chaque groupe
            vehicles_by_priority.sort(key=lambda v: instance.L[v[0]]["Qw"] + instance.L[v[0]]["Qv"], reverse=True)
            
            # Essayer d'assigner un véhicule
            vehicle_assigned = False
            for vtype, idx in vehicles_by_priority:
                capacity_w = instance.L[vtype]["Qw"]
                capacity_v = instance.L[vtype]["Qv"]
                
                # Vérifier si ce véhicule peut satisfaire les demandes restantes
                if (remaining_weight_AB + remaining_weight_BA <= capacity_w and
                    remaining_volume_AB + remaining_volume_BA <= capacity_v):
                    
                    # Créer un nouveau transport
                    transport = Transport(
                        week=week,
                        vehicle_idx=idx,
                        vehicle_type=vtype,
                        weight_AB=remaining_weight_AB,
                        volume_AB=remaining_volume_AB,
                        weight_BA=remaining_weight_BA,
                        volume_BA=remaining_volume_BA
                    )
                    
                    # Ajouter le transport à la solution
                    solution.transports.append(transport)
                    solution.vehicles[(vtype, idx)].weeks_used.add(week)
                    
                    vehicle_assigned = True
                    break
            
            # Si aucun véhicule ne peut satisfaire toutes les demandes, utiliser plusieurs véhicules
            if not vehicle_assigned:
                # Trier les types de véhicules par capacité décroissante
                vehicle_types = sorted(instance.L.keys(), 
                                      key=lambda vt: instance.L[vt]["Qw"] + instance.L[vt]["Qv"], 
                                      reverse=True)
                
                while (remaining_weight_AB > 0 or remaining_volume_AB > 0 or 
                       remaining_weight_BA > 0 or remaining_volume_BA > 0):
                    
                    vehicle_assigned = False
                    for vtype in vehicle_types:
                        capacity_w = instance.L[vtype]["Qw"]
                        capacity_v = instance.L[vtype]["Qv"]
                        
                        # Chercher un véhicule disponible de ce type
                        for idx in range(1, instance.m[vtype] + 1):
                            if (vtype, idx) not in vehicles_used_this_week:
                                # Calculer les quantités à transporter
                                weight_to_AB = min(remaining_weight_AB, capacity_w)
                                volume_to_AB = min(remaining_volume_AB, capacity_v)
                                
                                # Calculer la capacité restante pour B->A
                                remaining_capacity_w = capacity_w - weight_to_AB
                                remaining_capacity_v = capacity_v - volume_to_AB
                                
                                weight_to_BA = min(remaining_weight_BA, remaining_capacity_w)
                                volume_to_BA = min(remaining_volume_BA, remaining_capacity_v)
                                
                                # Créer le transport
                                transport = Transport(
                                    week=week,
                                    vehicle_idx=idx,
                                    vehicle_type=vtype,
                                    weight_AB=weight_to_AB,
                                    volume_AB=volume_to_AB,
                                    weight_BA=weight_to_BA,
                                    volume_BA=volume_to_BA
                                )
                                
                                # Mettre à jour la solution
                                solution.transports.append(transport)
                                solution.vehicles[(vtype, idx)].weeks_used.add(week)
                                vehicles_used_this_week.add((vtype, idx))
                                
                                # Mettre à jour les demandes restantes
                                remaining_weight_AB -= weight_to_AB
                                remaining_volume_AB -= volume_to_AB
                                remaining_weight_BA -= weight_to_BA
                                remaining_volume_BA -= volume_to_BA
                                
                                vehicle_assigned = True
                                break
                        
                        if vehicle_assigned:
                            break
                    
                    # Si aucun véhicule n'a pu être assigné, créer un transport artificiel
                    if not vehicle_assigned:
                        vtype = max(vehicle_types)
                        idx = 1
                        while (vtype, idx) in vehicles_used_this_week:
                            idx += 1
                            if idx > instance.m[vtype]:
                                idx = 1
                                break
                        
                        # Créer un transport pour satisfaire toutes les demandes restantes
                        transport = Transport(
                            week=week,
                            vehicle_idx=idx,
                            vehicle_type=vtype,
                            weight_AB=remaining_weight_AB,
                            volume_AB=remaining_volume_AB,
                            weight_BA=remaining_weight_BA,
                            volume_BA=remaining_volume_BA
                        )
                        
                        solution.transports.append(transport)
                        solution.vehicles[(vtype, idx)].weeks_used.add(week)
                        
                        # Toutes les demandes sont maintenant satisfaites
                        remaining_weight_AB = 0
                        remaining_volume_AB = 0
                        remaining_weight_BA = 0
                        remaining_volume_BA = 0
    
    # Réévaluer la solution
    solution.evaluate()

def mutate(solution, instance, mutation_rate=0.3):
    """
    Opérateur de mutation qui modifie certains transports
    
    Args:
        solution: Solution à muter
        instance: Instance du problème
        mutation_rate: Taux de mutation (probabilité de muter chaque semaine)
        
    Returns:
        Solution: Solution mutée
    """
    # Copier la solution pour éviter de modifier l'original
    mutated = copy.deepcopy(solution)
    
    # Pour chaque semaine, décider si on mute ou non
    for week in instance.T:
        if random.random() < mutation_rate:
            # Récupérer tous les transports de cette semaine
            week_transports = [t for t in mutated.transports if t.week == week]
            
            # Choisir une opération de mutation
            op = random.choice(["merge", "split", "reassign", "replace_vehicle"])
            
            if op == "merge" and len(week_transports) >= 2:
                # Fusionner deux transports si possible
                t1, t2 = random.sample(week_transports, 2)
                
                # Vérifier si la fusion est possible (même type de véhicule)
                if t1.vehicle_type == t2.vehicle_type:
                    vtype = t1.vehicle_type
                    capacity_w = instance.L[vtype]["Qw"]
                    capacity_v = instance.L[vtype]["Qv"]
                    
                    # Vérifier si la capacité est suffisante
                    if (t1.weight_AB + t2.weight_AB <= capacity_w and
                        t1.volume_AB + t2.volume_AB <= capacity_v and
                        t1.weight_BA + t2.weight_BA <= capacity_w and
                        t1.volume_BA + t2.volume_BA <= capacity_v):
                        
                        # Créer un nouveau transport fusionné
                        merged = Transport(
                            week=week,
                            vehicle_idx=t1.vehicle_idx,  # Garder le premier véhicule
                            vehicle_type=vtype,
                            weight_AB=t1.weight_AB + t2.weight_AB,
                            volume_AB=t1.volume_AB + t2.volume_AB,
                            weight_BA=t1.weight_BA + t2.weight_BA,
                            volume_BA=t1.volume_BA + t2.volume_BA
                        )
                        
                        # Remplacer les deux transports par celui fusionné
                        mutated.transports = [t for t in mutated.transports if t not in [t1, t2]]
                        mutated.transports.append(merged)
                        
                        # Mettre à jour les semaines d'utilisation des véhicules
                        mutated.vehicles[(t2.vehicle_type, t2.vehicle_idx)].weeks_used.discard(week)
            
            elif op == "split" and week_transports:
                # Diviser un transport en deux
                t = random.choice(week_transports)
                
                # Vérifier s'il y a quelque chose à diviser
                if (t.weight_AB > 0 or t.volume_AB > 0 or 
                    t.weight_BA > 0 or t.volume_BA > 0):
                    
                    # Chercher un véhicule non utilisé cette semaine
                    unused_vehicles = []
                    for (vtype, idx), vehicle in mutated.vehicles.items():
                        if week not in vehicle.weeks_used:
                            unused_vehicles.append((vtype, idx))
                    
                    if unused_vehicles:
                        # Choisir un véhicule au hasard
                        vtype, idx = random.choice(unused_vehicles)
                        
                        # Décider comment diviser la charge (au hasard entre 30% et 70%)
                        split_ratio = 0.3 + 0.4 * random.random()
                        
                        # Créer les deux nouveaux transports
                        t1 = Transport(
                            week=week,
                            vehicle_idx=t.vehicle_idx,
                            vehicle_type=t.vehicle_type,
                            weight_AB=t.weight_AB * (1 - split_ratio),
                            volume_AB=t.volume_AB * (1 - split_ratio),
                            weight_BA=t.weight_BA * (1 - split_ratio),
                            volume_BA=t.volume_BA * (1 - split_ratio)
                        )
                        
                        t2 = Transport(
                            week=week,
                            vehicle_idx=idx,
                            vehicle_type=vtype,
                            weight_AB=t.weight_AB * split_ratio,
                            volume_AB=t.volume_AB * split_ratio,
                            weight_BA=t.weight_BA * split_ratio,
                            volume_BA=t.volume_BA * split_ratio
                        )
                        
                        # Remplacer l'ancien transport par les deux nouveaux
                        mutated.transports = [trans for trans in mutated.transports if trans != t]
                        mutated.transports.extend([t1, t2])
                        
                        # Mettre à jour les semaines d'utilisation des véhicules
                        mutated.vehicles[(vtype, idx)].weeks_used.add(week)
            
            elif op == "reassign" and week_transports:
                # Réaffecter un transport à un autre véhicule
                t = random.choice(week_transports)
                
                # Chercher un véhicule non utilisé cette semaine
                unused_vehicles = []
                for (vtype, idx), vehicle in mutated.vehicles.items():
                    if week not in vehicle.weeks_used and (vtype, idx) != (t.vehicle_type, t.vehicle_idx):
                        unused_vehicles.append((vtype, idx))
                
                if unused_vehicles:
                    # Choisir un véhicule au hasard
                    vtype, idx = random.choice(unused_vehicles)
                    
                    # Vérifier si le nouveau véhicule a suffisamment de capacité
                    capacity_w = instance.L[vtype]["Qw"]
                    capacity_v = instance.L[vtype]["Qv"]
                    
                    if (t.weight_AB + t.weight_BA <= capacity_w and 
                        t.volume_AB + t.volume_BA <= capacity_v):
                        
                        # Créer un nouveau transport avec le nouveau véhicule
                        new_t = Transport(
                            week=week,
                            vehicle_idx=idx,
                            vehicle_type=vtype,
                            weight_AB=t.weight_AB,
                            volume_AB=t.volume_AB,
                            weight_BA=t.weight_BA,
                            volume_BA=t.volume_BA
                        )
                        
                        # Remplacer l'ancien transport par le nouveau
                        mutated.transports = [trans for trans in mutated.transports if trans != t]
                        mutated.transports.append(new_t)
                        
                        # Mettre à jour les semaines d'utilisation des véhicules
                        mutated.vehicles[(t.vehicle_type, t.vehicle_idx)].weeks_used.discard(week)
                        mutated.vehicles[(vtype, idx)].weeks_used.add(week)
            
            elif op == "replace_vehicle" and week_transports:
                # Remplacer un véhicule par un autre du même type ou d'un autre type
                t = random.choice(week_transports)
                
                # Déterminer les types de véhicules possibles (avec capacité suffisante)
                possible_types = []
                for vtype in instance.L.keys():
                    if (t.weight_AB + t.weight_BA <= instance.L[vtype]["Qw"] and 
                        t.volume_AB + t.volume_BA <= instance.L[vtype]["Qv"]):
                        possible_types.append(vtype)
                
                if possible_types and possible_types != [t.vehicle_type]:
                    # Choisir un type différent si possible
                    new_type = random.choice([vt for vt in possible_types if vt != t.vehicle_type] or possible_types)
                    
                    # Trouver un véhicule de ce type non utilisé cette semaine
                    available_vehicles = []
                    for idx in range(1, instance.m[new_type] + 1):
                        if week not in mutated.vehicles[(new_type, idx)].weeks_used:
                            available_vehicles.append(idx)
                    
                    if available_vehicles:
                        new_idx = random.choice(available_vehicles)
                        
                        # Créer un nouveau transport avec le nouveau véhicule
                        new_t = Transport(
                            week=week,
                            vehicle_idx=new_idx,
                            vehicle_type=new_type,
                            weight_AB=t.weight_AB,
                            volume_AB=t.volume_AB,
                            weight_BA=t.weight_BA,
                            volume_BA=t.volume_BA
                        )
                        
                        # Remplacer l'ancien transport par le nouveau
                        mutated.transports = [trans for trans in mutated.transports if trans != t]
                        mutated.transports.append(new_t)
                        
                        # Mettre à jour les semaines d'utilisation des véhicules
                        mutated.vehicles[(t.vehicle_type, t.vehicle_idx)].weeks_used.discard(week)
                        mutated.vehicles[(new_type, new_idx)].weeks_used.add(week)
    
    # Réévaluer la solution mutée
    mutated.evaluate()
    
    # Si la solution n'est pas faisable, la réparer
    if not mutated.feasible:
        repair_solution(mutated, instance)
    
    return mutated

def local_search(solution, instance, max_iterations=50, no_improvement_limit=10):
    """
    Effectue une recherche locale pour améliorer la solution
    
    Args:
        solution: Solution initiale
        instance: Instance du problème
        max_iterations: Nombre maximum d'itérations
        no_improvement_limit: Nombre d'itérations sans amélioration avant arrêt
        
    Returns:
        Solution: Solution améliorée
    """
    current = copy.deepcopy(solution)
    best = copy.deepcopy(solution)
    best_fitness = best.fitness
    no_improvement_count = 0
    
    # Liste des opérations de voisinage
    operations = ["consolidate_vehicles", "reassign_load", "change_vehicle_type", "balance_loads"]
    
    for iteration in range(max_iterations):
        # Choisir une opération aléatoirement
        op = random.choice(operations)
        neighbor = None
        
        if op == "consolidate_vehicles":
            neighbor = consolidate_vehicles(current, instance)
        elif op == "reassign_load":
            neighbor = reassign_load(current, instance)
        elif op == "change_vehicle_type":
            neighbor = change_vehicle_type(current, instance)
        elif op == "balance_loads":
            neighbor = balance_loads(current, instance)
        
        if neighbor and neighbor.feasible:
            # Si le voisin est meilleur, on le garde
            if neighbor.fitness < current.fitness:
                current = copy.deepcopy(neighbor)
                no_improvement_count = 0
                
                # Si c'est le meilleur trouvé jusqu'à présent, on met à jour best
                if current.fitness < best_fitness:
                    best = copy.deepcopy(current)
                    best_fitness = best.fitness
            else:
                # Accepter parfois des solutions moins bonnes pour éviter les optima locaux
                if random.random() < 0.3:  # Probabilité d'acceptation de 30%
                    current = copy.deepcopy(neighbor)
                no_improvement_count += 1
        else:
            no_improvement_count += 1
        
        # Critère d'arrêt: trop d'itérations sans amélioration
        if no_improvement_count >= no_improvement_limit:
            break
    
    return best

def consolidate_vehicles(solution, instance):
    """
    Tente de consolider les charges de plusieurs véhicules pour en utiliser moins
    
    Args:
        solution: Solution à améliorer
        instance: Instance du problème
        
    Returns:
        Solution: Solution améliorée ou None si pas d'amélioration possible
    """
    improved = copy.deepcopy(solution)
    
    # Pour chaque semaine
    for week in instance.T:
        # Récupérer tous les transports de cette semaine
        week_transports = [t for t in improved.transports if t.week == week]
        
        # Trier les transports par charge croissante (pour essayer de consolider les petites charges)
        week_transports.sort(key=lambda t: t.weight_AB + t.volume_AB + t.weight_BA + t.volume_BA)
        
        # Essayer de consolider des transports
        for i in range(len(week_transports)):
            t1 = week_transports[i]
            if t1 is None:  # Si déjà fusionné
                continue
                
            for j in range(i+1, len(week_transports)):
                t2 = week_transports[j]
                if t2 is None:  # Si déjà fusionné
                    continue
                
                # Essayer de fusionner t1 et t2 dans chaque type de véhicule disponible
                for vtype in instance.L.keys():
                    capacity_w = instance.L[vtype]["Qw"]
                    capacity_v = instance.L[vtype]["Qv"]
                    
                    if (t1.weight_AB + t2.weight_AB <= capacity_w and
                        t1.volume_AB + t2.volume_AB <= capacity_v and
                        t1.weight_BA + t2.weight_BA <= capacity_w and
                        t1.volume_BA + t2.volume_BA <= capacity_v):
                        
                        # Chercher un véhicule disponible de ce type
                        available_idx = None
                        for idx in range(1, instance.m[vtype] + 1):
                            if (vtype, idx) != (t1.vehicle_type, t1.vehicle_idx) and \
                               (vtype, idx) != (t2.vehicle_type, t2.vehicle_idx) and \
                               week not in improved.vehicles[(vtype, idx)].weeks_used:
                                available_idx = idx
                                break
                        
                        # Utiliser un véhicule existant si possible
                        if available_idx is None and (t1.vehicle_type == vtype or t2.vehicle_type == vtype):
                            available_idx = t1.vehicle_idx if t1.vehicle_type == vtype else t2.vehicle_idx
                        
                        if available_idx is not None:
                            # Créer un nouveau transport fusionné
                            merged = Transport(
                                week=week,
                                vehicle_idx=available_idx,
                                vehicle_type=vtype,
                                weight_AB=t1.weight_AB + t2.weight_AB,
                                volume_AB=t1.volume_AB + t2.volume_AB,
                                weight_BA=t1.weight_BA + t2.weight_BA,
                                volume_BA=t1.volume_BA + t2.volume_BA
                            )
                            
                            # Retirer les anciens transports et ajouter le nouveau
                            improved.transports = [t for t in improved.transports 
                                               if t != t1 and t != t2]
                            improved.transports.append(merged)
                            
                            # Mettre à jour les semaines d'utilisation des véhicules
                            improved.vehicles[(t1.vehicle_type, t1.vehicle_idx)].weeks_used.discard(week)
                            improved.vehicles[(t2.vehicle_type, t2.vehicle_idx)].weeks_used.discard(week)
                            improved.vehicles[(vtype, available_idx)].weeks_used.add(week)
                            
                            # Marquer comme fusionnés
                            week_transports[i] = None
                            week_transports[j] = None
                            
                            # Sortir des boucles
                            break
                
                if week_transports[i] is None:  # Si fusion réussie, passer au prochain transport
                    break
    
    # Évaluer la solution améliorée
    improved.evaluate()
    
    # Retourner la solution améliorée si elle est meilleure ou la même
    if improved.feasible and improved.fitness <= solution.fitness:
        return improved
    else:
        return None

def reassign_load(solution, instance):
    """
    Tente de réaffecter des charges entre véhicules pour mieux utiliser les capacités
    
    Args:
        solution: Solution à améliorer
        instance: Instance du problème
        
    Returns:
        Solution: Solution améliorée ou None si pas d'amélioration possible
    """
    improved = copy.deepcopy(solution)
    
    # Pour chaque semaine
    for week in instance.T:
        # Récupérer tous les transports de cette semaine
        week_transports = [t for t in improved.transports if t.week == week]
        
        # Parcourir toutes les paires de transports
        for i in range(len(week_transports)):
            t1 = week_transports[i]
            
            for j in range(len(week_transports)):
                if i == j:
                    continue
                    
                t2 = week_transports[j]
                
                # Essayer de déplacer une partie de la charge de t1 vers t2
                capacity_w_remaining = instance.L[t2.vehicle_type]["Qw"] - (t2.weight_AB + t2.weight_BA)
                capacity_v_remaining = instance.L[t2.vehicle_type]["Qv"] - (t2.volume_AB + t2.volume_BA)
                
                # Si t2 a de la capacité restante et t1 a une charge à déplacer
                if capacity_w_remaining > 0 and capacity_v_remaining > 0:
                    # Décider quelle proportion de charge déplacer (entre 10% et 50%)
                    ratio = 0.1 + 0.4 * random.random()
                    
                    # Calculer les quantités à déplacer
                    move_weight_AB = min(t1.weight_AB * ratio, capacity_w_remaining)
                    move_volume_AB = min(t1.volume_AB * ratio, capacity_v_remaining)
                    
                    # Mise à jour de capacité restante après déplacement A→B
                    capacity_w_remaining -= move_weight_AB
                    capacity_v_remaining -= move_volume_AB
                    
                    move_weight_BA = min(t1.weight_BA * ratio, capacity_w_remaining)
                    move_volume_BA = min(t1.volume_BA * ratio, capacity_v_remaining)
                    
                    # Si le déplacement est significatif
                    if move_weight_AB > 0 or move_volume_AB > 0 or move_weight_BA > 0 or move_volume_BA > 0:
                        # Créer de nouveaux transports avec charges réaffectées
                        new_t1 = Transport(
                            week=week,
                            vehicle_idx=t1.vehicle_idx,
                            vehicle_type=t1.vehicle_type,
                            weight_AB=t1.weight_AB - move_weight_AB,
                            volume_AB=t1.volume_AB - move_volume_AB,
                            weight_BA=t1.weight_BA - move_weight_BA,
                            volume_BA=t1.volume_BA - move_volume_BA
                        )
                        
                        new_t2 = Transport(
                            week=week,
                            vehicle_idx=t2.vehicle_idx,
                            vehicle_type=t2.vehicle_type,
                            weight_AB=t2.weight_AB + move_weight_AB,
                            volume_AB=t2.volume_AB + move_volume_AB,
                            weight_BA=t2.weight_BA + move_weight_BA,
                            volume_BA=t2.volume_BA + move_volume_BA
                        )
                        
                        # Vérifier si t1 est complètement vide après réaffectation
                        if (new_t1.weight_AB == 0 and new_t1.volume_AB == 0 and
                            new_t1.weight_BA == 0 and new_t1.volume_BA == 0):
                            # Retirer t1 complètement et mettre à jour t2
                            improved.transports = [t for t in improved.transports if t != t1 and t != t2]
                            improved.transports.append(new_t2)
                            
                            # Mettre à jour les semaines d'utilisation
                            improved.vehicles[(t1.vehicle_type, t1.vehicle_idx)].weeks_used.discard(week)
                        else:
                            # Remplacer les deux transports
                            improved.transports = [t for t in improved.transports if t != t1 and t != t2]
                            improved.transports.extend([new_t1, new_t2])
                        
                        # Sortir de la boucle après un changement réussi
                        break
            
    # Évaluer la solution améliorée
    improved.evaluate()
    
    # Retourner la solution améliorée si elle est meilleure
    if improved.feasible and improved.fitness <= solution.fitness:
        return improved
    else:
        return None

def change_vehicle_type(solution, instance):
    """
    Tente de remplacer un véhicule par un autre type qui serait plus adapté
    
    Args:
        solution: Solution à améliorer
        instance: Instance du problème
        
    Returns:
        Solution: Solution améliorée ou None si pas d'amélioration possible
    """
    improved = copy.deepcopy(solution)
    
    # Identifier les véhicules peu utilisés (pour potentiellement les éliminer)
    vehicle_usage = {}
    for (vtype, idx), vehicle in improved.vehicles.items():
        vehicle_usage[(vtype, idx)] = len(vehicle.weeks_used)
    
    # Trouver les véhicules utilisés mais avec peu de charge
    for week in instance.T:
        week_transports = [t for t in improved.transports if t.week == week]
        
        for transport in week_transports:
            # Calculer le taux d'utilisation du véhicule (poids et volume)
            vtype = transport.vehicle_type
            capacity_w = instance.L[vtype]["Qw"]
            capacity_v = instance.L[vtype]["Qv"]
            
            weight_usage = (transport.weight_AB + transport.weight_BA) / capacity_w
            volume_usage = (transport.volume_AB + transport.volume_BA) / capacity_v
            
            # Si le véhicule est peu utilisé (moins de 70% de sa capacité), essayer un véhicule plus petit
            if max(weight_usage, volume_usage) < 0.7:
                for new_vtype in instance.L.keys():
                    # Ne considérer que les types de véhicules plus petits (ou de même taille mais moins chers)
                    if (new_vtype != vtype and 
                        instance.c[new_vtype] < instance.c[vtype] and
                        transport.weight_AB + transport.weight_BA <= instance.L[new_vtype]["Qw"] and
                        transport.volume_AB + transport.volume_BA <= instance.L[new_vtype]["Qv"]):
                        
                        # Chercher un véhicule disponible de ce type
                        available_idx = None
                        for idx in range(1, instance.m[new_vtype] + 1):
                            if week not in improved.vehicles[(new_vtype, idx)].weeks_used:
                                available_idx = idx
                                break
                        
                        if available_idx is not None:
                            # Créer un nouveau transport avec le nouveau type de véhicule
                            new_transport = Transport(
                                week=week,
                                vehicle_idx=available_idx,
                                vehicle_type=new_vtype,
                                weight_AB=transport.weight_AB,
                                volume_AB=transport.volume_AB,
                                weight_BA=transport.weight_BA,
                                volume_BA=transport.volume_BA
                            )
                            
                            # Remplacer l'ancien transport
                            improved.transports = [t for t in improved.transports if t != transport]
                            improved.transports.append(new_transport)
                            
                            # Mettre à jour les semaines d'utilisation
                            improved.vehicles[(vtype, transport.vehicle_idx)].weeks_used.discard(week)
                            improved.vehicles[(new_vtype, available_idx)].weeks_used.add(week)
                            break
    
    # Évaluer la solution améliorée
    improved.evaluate()
    
    # Retourner la solution améliorée si elle est meilleure
    if improved.feasible and improved.fitness <= solution.fitness:
        return improved
    else:
        return None

def balance_loads(solution, instance):
    """
    Tente de mieux équilibrer les charges entre les semaines pour réduire le nombre de véhicules
    
    Args:
        solution: Solution à améliorer
        instance: Instance du problème
        
    Returns:
        Solution: Solution améliorée ou None si pas d'amélioration possible
    """
    improved = copy.deepcopy(solution)
    
    # Identifier les véhicules utilisés une seule fois ou très peu
    rare_vehicles = []
    for (vtype, idx), vehicle in improved.vehicles.items():
        if 0 < len(vehicle.weeks_used) <= 3:  # Véhicules utilisés 1, 2 ou 3 fois
            rare_vehicles.append((vtype, idx))
    
    if not rare_vehicles:
        return None  # Pas de véhicules rarement utilisés
    
    # Pour chaque véhicule rarement utilisé
    for vtype, idx in rare_vehicles:
        # Récupérer les semaines où ce véhicule est utilisé
        weeks_used = list(improved.vehicles[(vtype, idx)].weeks_used)
        
        # Pour chaque semaine d'utilisation
        for week in weeks_used:
            # Trouver le transport correspondant
            transport = None
            for t in improved.transports:
                if t.week == week and t.vehicle_type == vtype and t.vehicle_idx == idx:
                    transport = t
                    break
            
            if not transport:
                continue
            
            # Chercher un autre véhicule déjà utilisé qui pourrait prendre cette charge
            for other_week in instance.T:
                if other_week != week:
                    # Trouver les véhicules utilisés dans cette autre semaine
                    vehicles_in_other_week = set()
                    for t in improved.transports:
                        if t.week == other_week:
                            vehicles_in_other_week.add((t.vehicle_type, t.vehicle_idx))
                    
                    # Vérifier si un de ces véhicules peut prendre la charge additionnelle
                    for other_vtype, other_idx in vehicles_in_other_week:
                        # Vérifier si le véhicule a assez de capacité restante
                        capacity_w = instance.L[other_vtype]["Qw"]
                        capacity_v = instance.L[other_vtype]["Qv"]
                        
                        # Calculer la charge actuelle du véhicule dans l'autre semaine
                        current_weight = 0
                        current_volume = 0
                        for t in improved.transports:
                            if (t.week == other_week and 
                                t.vehicle_type == other_vtype and 
                                t.vehicle_idx == other_idx):
                                current_weight += t.weight_AB + t.weight_BA
                                current_volume += t.volume_AB + t.volume_BA
                        
                        # Vérifier si le véhicule peut prendre la charge additionnelle
                        if (current_weight + transport.weight_AB + transport.weight_BA <= capacity_w and
                            current_volume + transport.volume_AB + transport.volume_BA <= capacity_v):
                            
                            # Créer un nouveau transport pour cette autre semaine
                            new_transport = Transport(
                                week=other_week,
                                vehicle_idx=other_idx,
                                vehicle_type=other_vtype,
                                weight_AB=transport.weight_AB,
                                volume_AB=transport.volume_AB,
                                weight_BA=transport.weight_BA,
                                volume_BA=transport.volume_BA
                            )
                            
                            # Retirer l'ancien transport et ajouter le nouveau
                            improved.transports = [t for t in improved.transports if t != transport]
                            improved.transports.append(new_transport)
                            
                            # Mettre à jour les semaines d'utilisation
                            improved.vehicles[(vtype, idx)].weeks_used.discard(week)
                            improved.vehicles[(other_vtype, other_idx)].weeks_used.add(other_week)
                            
                            # Sortir des boucles
                            break
                    else:
                        continue  # Continuer si aucun véhicule trouvé
                    break  # Sortir si un véhicule a été trouvé
    
    # Évaluer la solution améliorée
    improved.evaluate()
    
    # Retourner la solution améliorée si elle est meilleure
    if improved.feasible and improved.fitness <= solution.fitness:
        return improved
    else:
        return None

def memetic_algorithm(instance, population_size=20, generations=100, mutation_rate=0.3, local_search_freq=5):
    """
    Algorithme mémétique pour résoudre le problème de transport
    
    Args:
        instance: Instance du problème
        population_size: Taille de la population
        generations: Nombre de générations
        mutation_rate: Taux de mutation
        local_search_freq: Fréquence d'application de la recherche locale (toutes les x générations)
        
    Returns:
        Solution: Meilleure solution trouvée
    """
    # Initialiser la population
    population = []
    for _ in range(population_size):
        solution = greedy_initial_solution(instance)
        population.append(solution)
    
    # Évaluer la population initiale
    for solution in population:
        solution.evaluate()
    
    # Tri de la population par fitness
    population.sort(key=lambda s: s.fitness)
    
    best_solution = copy.deepcopy(population[0])
    best_fitness = best_solution.fitness
    
    for generation in range(generations):
        # Créer une nouvelle génération
        new_population = []
        
        # Élitisme: garder le meilleur individu
        new_population.append(copy.deepcopy(population[0]))
        
        # Créer des enfants par croisement et mutation
        while len(new_population) < population_size:
            # Sélection des parents par tournoi
            parent1 = tournament_selection(population, tournament_size=3)
            parent2 = tournament_selection(population, tournament_size=3)
            
            # Croisement
            child = crossover(parent1, parent2, instance)
            
            # Mutation
            if random.random() < mutation_rate:
                child = mutate(child, instance)
            
            # Ajouter l'enfant à la nouvelle population
            new_population.append(child)
        
        # Appliquer la recherche locale périodiquement
        if generation % local_search_freq == 0:
            # Appliquer la recherche locale au meilleur individu
            new_population[0] = local_search(new_population[0], instance)
            
            # Appliquer aussi à quelques individus aléatoires
            for i in random.sample(range(1, len(new_population)), min(3, len(new_population) - 1)):
                new_population[i] = local_search(new_population[i], instance)
        
        # Mettre à jour la population
        population = new_population
        
        # Trier la population par fitness
        population.sort(key=lambda s: s.fitness)
        
        # Mettre à jour la meilleure solution si nécessaire
        if population[0].fitness < best_fitness:
            best_solution = copy.deepcopy(population[0])
            best_fitness = best_solution.fitness
            print(f"Génération {generation}: Nouvelle meilleure solution trouvée avec {best_fitness} véhicules")
        
        # Afficher des informations tous les 10 générations
        if generation % 10 == 0:
            avg_fitness = sum(s.fitness for s in population) / len(population)
            print(f"Génération {generation}: Meilleure fitness = {population[0].fitness}, Moyenne = {avg_fitness:.2f}")
    
    return best_solution

def tournament_selection(population, tournament_size=3):
    """
    Sélection par tournoi
    
    Args:
        population: Population actuelle
        tournament_size: Taille du tournoi
        
    Returns:
        Solution: Solution sélectionnée
    """
    # Sélectionner aléatoirement des individus pour le tournoi
    tournament = random.sample(population, tournament_size)
    
    # Retourner le meilleur
    return min(tournament, key=lambda s: s.fitness)

# Fonction principale
def main():
    # Créer une instance du problème
    instance = Instance()
    
    # Afficher les informations de l'instance
    print("Instance créée avec succès:")
    print(f"Nombre de semaines: {len(instance.T)}")
    print(f"Types de véhicules disponibles: {instance.L}")
    print(f"Nombre de véhicules par type: {instance.m}")
    
    # Afficher les demandes
    print("\nDemandes de transport:")
    for t in instance.T:
        print(f"Semaine {t}:")
        print(f"  A→B: {instance.dw_AB[t]} kg, {instance.dv_AB[t]} m³")
        print(f"  B→A: {instance.dw_BA[t]} kg, {instance.dv_BA[t]} m³")
    
    # Résoudre le problème avec l'algorithme mémétique
    print("\nRésolution du problème avec l'algorithme mémétique...")
    start_time = time.time()
    best_solution = memetic_algorithm(instance, population_size=20, generations=100, local_search_freq=5)
    end_time = time.time()
    
    # Afficher les résultats
    print("\nMeilleure solution trouvée:")
    print(best_solution.detailed_str())
    print(f"\nTemps d'exécution: {end_time - start_time:.2f} secondes")
    
    # Sauvegarder la solution dans un fichier
    save_solution(best_solution, "best_solution.json")
    
    # Visualiser les résultats
    visualize_solution(best_solution, instance)
    # Vérifier et afficher si la solution est optimale
    optimal = is_optimal(best_solution, instance)
    print(f"\nLa solution est-elle optimale? {'Oui' if optimal else 'Non'}")    
    
    return best_solution

def save_solution(solution, filename):
    """
    Sauvegarde une solution dans un fichier JSON
    
    Args:
        solution: Solution à sauvegarder
        filename: Nom du fichier de sortie
    """
    # Créer un dictionnaire avec les informations de la solution
    solution_dict = {
        "fitness": solution.fitness,
        "feasible": solution.feasible,
        "vehicles_used": [],
        "transports": []
    }
    
    # Ajouter les informations sur les véhicules utilisés
    for (vtype, idx), vehicle in solution.vehicles.items():
        if vehicle.weeks_used:
            solution_dict["vehicles_used"].append({
                "type": vtype,
                "index": idx,
                "weeks_used": list(vehicle.weeks_used)
            })
    
    # Ajouter les informations sur les transports
    for transport in solution.transports:
        solution_dict["transports"].append({
            "week": transport.week,
            "vehicle_type": transport.vehicle_type,
            "vehicle_idx": transport.vehicle_idx,
            "weight_AB": transport.weight_AB,
            "volume_AB": transport.volume_AB,
            "weight_BA": transport.weight_BA,
            "volume_BA": transport.volume_BA
        })
    
    # Écrire dans le fichier
    with open(filename, 'w') as f:
        json.dump(solution_dict, f, indent=4)
    
    print(f"Solution sauvegardée dans le fichier {filename}")

def visualize_solution(solution, instance):
    """
    Visualise la solution avec matplotlib
    
    Args:
        solution: Solution à visualiser
        instance: Instance du problème
    """
    try:
        import matplotlib.pyplot as plt # type: ignore
        import matplotlib.patches as patches # type: ignore
        import numpy as np
    except ImportError:
        print("Matplotlib est nécessaire pour la visualisation. Installation avec 'pip install matplotlib'.")
        return
    
    # Calculer le nombre de véhicules utilisés par type et par semaine
    vehicles_per_week = {}
    for t in instance.T:
        vehicles_per_week[t] = {vtype: 0 for vtype in instance.L.keys()}
    
    for transport in solution.transports:
        vehicles_per_week[transport.week][transport.vehicle_type] += 1
    
    # Préparer les données pour le graphique
    weeks = sorted(instance.T)
    vehicle_types = sorted(instance.L.keys())
    
    # Créer une figure avec deux sous-graphiques
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Graphique 1: Nombre de véhicules utilisés par semaine et par type
    bottom = np.zeros(len(weeks))
    
    for vtype in vehicle_types:
        values = [vehicles_per_week[week][vtype] for week in weeks]
        ax1.bar(weeks, values, bottom=bottom, label=f'Type {vtype}')
        bottom += values
    
    ax1.set_xlabel('Semaine')
    ax1.set_ylabel('Nombre de véhicules')
    ax1.set_title('Nombre de véhicules utilisés par semaine')
    ax1.legend()
    
    # Graphique 2: Taux d'utilisation des véhicules
    vehicle_usage = []
    vehicle_labels = []
    
    for transport in solution.transports:
        vtype = transport.vehicle_type
        capacity_w = instance.L[vtype]["Qw"]
        capacity_v = instance.L[vtype]["Qv"]
        
        weight_usage = (transport.weight_AB + transport.weight_BA) / (2 * capacity_w) * 100
        volume_usage = (transport.volume_AB + transport.volume_BA) / (2 * capacity_v) * 100
        
        avg_usage = (weight_usage + volume_usage) / 2
        
        vehicle_usage.append(avg_usage)
        vehicle_labels.append(f"S{transport.week}-{vtype}{transport.vehicle_idx}")
    
    # Trier par taux d'utilisation
    sorted_indices = np.argsort(vehicle_usage)
    sorted_usage = [vehicle_usage[i] for i in sorted_indices]
    sorted_labels = [vehicle_labels[i] for i in sorted_indices]
    
    # Afficher les 15 premiers et les 15 derniers pour la lisibilité
    if len(sorted_usage) > 30:
        show_indices = list(range(15)) + list(range(len(sorted_usage) - 15, len(sorted_usage)))
        sorted_usage = [sorted_usage[i] for i in show_indices]
        sorted_labels = [sorted_labels[i] for i in show_indices]
        # Ajouter une séparation
        sorted_usage.insert(15, 0)
        sorted_labels.insert(15, "...")
    
    ax2.bar(range(len(sorted_usage)), sorted_usage)
    ax2.set_xticks(range(len(sorted_labels)))
    ax2.set_xticklabels(sorted_labels, rotation=90)
    ax2.set_ylabel('Taux d\'utilisation (%)')
    ax2.set_title('Taux d\'utilisation moyen des véhicules')
    ax2.axhline(y=70, color='r', linestyle='--', label='Seuil 70%')
    ax2.legend()
    
    plt.tight_layout()
    plt.savefig('solution_visualization.png')
    print("Visualisation sauvegardée dans le fichier solution_visualization.png")
    plt.close()

def repair_solution(solution, instance):
    """
    Répare une solution non faisable en ajoutant des transports manquants
    
    Args:
        solution: Solution à réparer
        instance: Instance du problème
    """
    # Pour chaque semaine, vérifier si toutes les demandes sont satisfaites
    for week in instance.T:
        # Calculer les charges actuellement transportées
        current_weight_AB = 0
        current_volume_AB = 0
        current_weight_BA = 0
        current_volume_BA = 0
        
        for t in solution.transports:
            if t.week == week:
                current_weight_AB += t.weight_AB
                current_volume_AB += t.volume_AB
                current_weight_BA += t.weight_BA
                current_volume_BA += t.volume_BA
        
        # Calculer les demandes non satisfaites
        missing_weight_AB = max(0, instance.dw_AB[week] - current_weight_AB)
        missing_volume_AB = max(0, instance.dv_AB[week] - current_volume_AB)
        missing_weight_BA = max(0, instance.dw_BA[week] - current_weight_BA)
        missing_volume_BA = max(0, instance.dv_BA[week] - current_volume_BA)
        
        # S'il manque des transports, ajouter des véhicules
        if missing_weight_AB > 0 or missing_volume_AB > 0 or missing_weight_BA > 0 or missing_volume_BA > 0:
            # Trouver des véhicules disponibles qui peuvent transporter les charges manquantes
            for vtype in sorted(instance.L.keys(), key=lambda v: instance.c[v]):
                capacity_w = instance.L[vtype]["Qw"]
                capacity_v = instance.L[vtype]["Qv"]
                
                # Continuer à ajouter des véhicules tant qu'il reste des demandes non satisfaites
                while (missing_weight_AB > 0 or missing_volume_AB > 0 or 
                      missing_weight_BA > 0 or missing_volume_BA > 0):
                    
                    # Chercher un véhicule disponible de ce type
                    available_idx = None
                    for idx in range(1, instance.m[vtype] + 1):
                        if week not in solution.vehicles[(vtype, idx)].weeks_used:
                            available_idx = idx
                            break
                    
                    if available_idx is None:
                        # Pas de véhicule disponible de ce type, essayer le suivant
                        break
                    
                    # Calculer les quantités à transporter avec ce véhicule
                    weight_AB = min(missing_weight_AB, capacity_w)
                    volume_AB = min(missing_volume_AB, capacity_v)
                    
                    # La capacité restante pour B→A
                    remaining_w = capacity_w - weight_AB
                    remaining_v = capacity_v - volume_AB
                    
                    weight_BA = min(missing_weight_BA, remaining_w)
                    volume_BA = min(missing_volume_BA, remaining_v)
                    
                    # Créer un nouveau transport
                    transport = Transport(
                        week=week,
                        vehicle_idx=available_idx,
                        vehicle_type=vtype,
                        weight_AB=weight_AB,
                        volume_AB=volume_AB,
                        weight_BA=weight_BA,
                        volume_BA=volume_BA
                    )
                    
                    # Ajouter le transport à la solution
                    solution.transports.append(transport)
                    
                    # Mettre à jour le véhicule comme utilisé cette semaine
                    solution.vehicles[(vtype, available_idx)].weeks_used.add(week)
                    
                    # Mettre à jour les demandes non satisfaites
                    missing_weight_AB = max(0, missing_weight_AB - weight_AB)
                    missing_volume_AB = max(0, missing_volume_AB - volume_AB)
                    missing_weight_BA = max(0, missing_weight_BA - weight_BA)
                    missing_volume_BA = max(0, missing_volume_BA - volume_BA)
                    
                    # Si toutes les demandes sont satisfaites, sortir de la boucle
                    if (missing_weight_AB == 0 and missing_volume_AB == 0 and
                        missing_weight_BA == 0 and missing_volume_BA == 0):
                        break
    
    # Réévaluer la solution réparée
    solution.evaluate()
    
    # Vérifier que la solution est maintenant faisable
    if not solution.feasible:
        print("ATTENTION: La solution n'a pas pu être réparée correctement!")

def is_optimal(solution, instance):
    """
    Vérifie si une solution est optimale (ou proche de l'optimal) en utilisant une borne inférieure simple
    
    Args:
        solution: Solution à évaluer
        instance: Instance du problème
        
    Returns:
        bool: True si la solution est potentiellement optimale
    """
    # Calcul d'une borne inférieure simple: le nombre minimum de véhicules pour la semaine la plus chargée
    min_vehicles_needed = float('inf')
    
    # Pour chaque semaine, calculer le nombre minimum de véhicules nécessaires
    for week in instance.T:
        # Demande totale pour cette semaine (somme des deux directions)
        total_demand_weight = instance.dw_AB[week] + instance.dw_BA[week]
        total_demand_volume = instance.dv_AB[week] + instance.dv_BA[week]
        
        # Calculer combien de véhicules de chaque type seraient nécessaires
        vehicles_needed = float('inf')
        
        # D'abord, essayons avec uniquement des véhicules de type 2 (plus grande capacité)
        if 2 in instance.L:  # Vérifie si le type 2 existe
            capacity_w_type2 = instance.L[2]["Qw"]
            capacity_v_type2 = instance.L[2]["Qv"]
            
            # Nombre de véhicules type 2 nécessaires basé sur le poids
            vehicles_needed_weight = max(1, total_demand_weight / capacity_w_type2)
            # Nombre de véhicules type 2 nécessaires basé sur le volume
            vehicles_needed_volume = max(1, total_demand_volume / capacity_v_type2)
            
            # Le max des deux est le nombre minimal de véhicules type 2 nécessaires
            vehicles_needed = max(vehicles_needed_weight, vehicles_needed_volume)
            
            # Arrondir au nombre entier supérieur
            vehicles_needed = math.ceil(vehicles_needed)
        
        # Mettre à jour la borne inférieure globale
        min_vehicles_needed = min(min_vehicles_needed, vehicles_needed)
    
    # Nombre de véhicules distincts utilisés dans la solution
    vehicles_used = len({(t.vehicle_type, t.vehicle_idx) for t in solution.transports})
    
    # Afficher les détails pour le debug
    print(f"\nBorne inférieure théorique: {min_vehicles_needed} véhicule(s)")
    print(f"Véhicules distincts utilisés: {vehicles_used}")
    
    # La solution est optimale si elle utilise exactement le nombre minimum de véhicules
    return vehicles_used <= min_vehicles_needed

if __name__ == "__main__":
    import math  # Ajout de l'import math nécessaire pour la fonction is_optimal
    
    # Exécuter la fonction principale
    best_solution = main()