import numpy as np
import random
import copy
import time
import json
from collections import defaultdict
import sys
import math
sys.stdout.reconfigure(encoding='utf-8')

class Instance:
    def __init__(self):
        """
        Initialisation d'une instance du problème de transport par navettes entre les sites A et B
        sur un horizon de 12 semaines, avec transport uniquement dans le sens A vers B.
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
        
        # Vitesse moyenne des véhicules (km/h)
        self.V = {
            1: 70,  # Vitesse du véhicule de type 1
            2: 60   # Vitesse du véhicule de type 2
        }
        
        # Coût de déplacement entre les sites (indépendant du type de véhicule)
        self.dc = 50
        
        # Demandes hebdomadaires (poids et volume) uniquement A vers B
        # Initialiser les demandes pour 12 semaines
        self.dw_AB = {}  # Demandes en poids de A vers B
        self.dv_AB = {}  # Demandes en volume de A vers B
        
        # Générer des demandes aléatoires mais réalistes
        for t in self.T:
            # Variation hebdomadaire pour rendre le problème plus réaliste
            week_factor_AB = 0.9 + 0.2 * random.random()
            
            # Demandes de A vers B
            self.dw_AB[t] = int(200 * week_factor_AB)  # Demande en poids base 200
            self.dv_AB[t] = int(80 * week_factor_AB)   # Demande en volume base 80
        
        # Paramètres liés aux contraintes temporelles
        self.T_start = 7      # Heure de début de la journée de travail (en heures depuis minuit)
        self.T_end = 18       # Heure de fin de la journée de travail (en heures depuis minuit)
        self.T_drive = 2      # Durée maximale de conduite continue (en heures)
        self.T_break = 0.25   # Durée d'une pause obligatoire (en heures, soit 15 minutes)
        
        # Distances entre les sites (en km)
        self.d_AB = 120  # Distance A vers B
        self.d_BA = 120  # Distance B vers A (trajet retour)
        
        # Temps de chargement et déchargement (en heures)
        self.T_load_A = 0.5    # Temps de chargement au site A
        self.T_unload_B = 0.5  # Temps de déchargement au site B

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
    def __init__(self, week, vehicle_idx, vehicle_type, weight_AB=0, volume_AB=0, 
                 load_start_A=None, load_end_A=None, departure_A=None, arrival_B=None,
                 unload_start_B=None, unload_end_B=None, departure_B=None, arrival_A=None,
                 breaks_AB=0, breaks_BA=0, seq=1):
        """
        Représente un transport effectué par un véhicule pendant une semaine donnée
        
        Args:
            week: Semaine du transport
            vehicle_idx: Indice du véhicule utilisé
            vehicle_type: Type du véhicule
            weight_AB: Quantité en poids transportée de A vers B
            volume_AB: Quantité en volume transportée de A vers B
            load_start_A: Heure de début du chargement au site A
            load_end_A: Heure de fin du chargement au site A
            departure_A: Heure de départ du site A
            arrival_B: Heure d'arrivée au site B
            unload_start_B: Heure de début du déchargement au site B
            unload_end_B: Heure de fin du déchargement au site B
            departure_B: Heure de départ du site B pour retour à vide
            arrival_A: Heure d'arrivée au site A du véhicule vide
            breaks_AB: Nombre de pauses prises pendant le trajet A→B
            breaks_BA: Nombre de pauses prises pendant le trajet retour B→A
            seq: Numéro de séquence du transport dans la journée
        """
        self.week = week
        self.vehicle_idx = vehicle_idx
        self.vehicle_type = vehicle_type
        self.weight_AB = weight_AB
        self.volume_AB = volume_AB
        
        # Variables temporelles
        self.load_start_A = load_start_A if load_start_A is not None else 7.0  # Par défaut: début journée
        self.load_end_A = load_end_A
        self.departure_A = departure_A
        self.arrival_B = arrival_B
        self.unload_start_B = unload_start_B
        self.unload_end_B = unload_end_B
        self.departure_B = departure_B
        self.arrival_A = arrival_A
        
        # Variables liées aux pauses
        self.breaks_AB = breaks_AB
        self.breaks_BA = breaks_BA
        
        # Séquence du transport dans la journée
        self.seq = seq
        
        # Variable pour indiquer si le trajet continue sur le jour suivant
        self.overnight_AB = False
        self.overnight_BA = False
    
    def __str__(self):
        return f"Transport(semaine={self.week}, véhicule={self.vehicle_idx}(type {self.vehicle_type}), " \
               f"AB: {self.weight_AB}kg/{self.volume_AB}m³, seq={self.seq})"

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
        
        # Vérifier la satisfaction des demandes et les contraintes temporelles
        self.feasible = self.check_feasibility()
        
        # Mettre à jour la fitness (objectif: minimiser le nombre de véhicules)
        self.fitness = vehicles_used if self.feasible else float('inf')
        
        return self.fitness
    
    def check_feasibility(self):
        """
        Vérifie si la solution est faisable (demandes satisfaites + contraintes temporelles)
        
        Returns:
            bool: True si la solution est faisable, False sinon
        """
        # Vérifier la satisfaction des demandes
        if not self.check_demands_satisfaction():
            return False
        
        # Vérifier les contraintes temporelles
        if not self.check_temporal_constraints():
            return False
        
        return True
    
    def check_demands_satisfaction(self):
        """
        Vérifie si toutes les demandes sont satisfaites
        
        Returns:
            bool: True si toutes les demandes sont satisfaites, False sinon
        """
        # Calculer les quantités transportées par semaine (uniquement A→B)
        transported_weight_AB = defaultdict(float)
        transported_volume_AB = defaultdict(float)
        
        for transport in self.transports:
            week = transport.week
            transported_weight_AB[week] += transport.weight_AB
            transported_volume_AB[week] += transport.volume_AB
        
        # Vérifier si toutes les demandes sont satisfaites
        for week in self.instance.T:
            if transported_weight_AB[week] < self.instance.dw_AB[week]:
                return False
            if transported_volume_AB[week] < self.instance.dv_AB[week]:
                return False
        
        return True
    
    def check_temporal_constraints(self):
        """
        Vérifie si toutes les contraintes temporelles sont respectées
        
        Returns:
            bool: True si toutes les contraintes temporelles sont respectées, False sinon
        """
        # Regrouper les transports par semaine et véhicule
        transports_by_week_veh = {}
        for transport in self.transports:
            key = (transport.week, transport.vehicle_type, transport.vehicle_idx)
            if key not in transports_by_week_veh:
                transports_by_week_veh[key] = []
            transports_by_week_veh[key].append(transport)
        
        # Pour chaque semaine et véhicule, vérifier la séquence temporelle
        for (week, vtype, vidx), week_veh_transports in transports_by_week_veh.items():
            # Trier les transports par séquence
            week_veh_transports.sort(key=lambda t: t.seq)
            
            # Vérifier la journée de travail et les pauses
            for transport in week_veh_transports:
                # 1. Vérifier les heures de travail (sauf si overnight)
                if not transport.overnight_AB and not transport.overnight_BA:
                    if (transport.load_start_A < self.instance.T_start or 
                        (transport.arrival_A is not None and transport.arrival_A > self.instance.T_end)):
                        return False
                
                # 2. Vérifier cohérence temporelle des opérations
                if (transport.load_end_A is None or transport.departure_A is None or 
                    transport.arrival_B is None or transport.unload_start_B is None or 
                    transport.unload_end_B is None):
                    # Si les temps ne sont pas définis, les définir
                    self.compute_times_for_transport(transport)
                
                # 3. Vérifier les séquences d'opérations
                if (transport.load_end_A > transport.departure_A or 
                    transport.departure_A > transport.arrival_B or 
                    transport.arrival_B > transport.unload_start_B or 
                    transport.unload_start_B > transport.unload_end_B):
                    return False
                
                # 4. Si le véhicule revient à A, vérifier les séquences de retour
                if transport.departure_B is not None:
                    if (transport.unload_end_B > transport.departure_B or 
                        transport.departure_B > transport.arrival_A):
                        return False
            
            # Vérifier la séquence des transports dans la journée
            for i in range(1, len(week_veh_transports)):
                prev_transport = week_veh_transports[i-1]
                curr_transport = week_veh_transports[i]
                
                # Le transport suivant doit commencer après la fin du précédent
                if prev_transport.arrival_A is not None:
                    if curr_transport.load_start_A < prev_transport.arrival_A:
                        return False
        
        return True
    
    def compute_times_for_transport(self, transport):
        """
        Calcule les temps pour un transport (si non définis)
        
        Args:
            transport: Transport à traiter
        """
        instance = self.instance
        vtype = transport.vehicle_type
        
        # 1. Temps de chargement
        if transport.load_end_A is None:
            transport.load_end_A = transport.load_start_A + instance.T_load_A
        
        # 2. Départ du site A
        if transport.departure_A is None:
            transport.departure_A = transport.load_end_A
        
        # 3. Calcul du nombre de pauses pour A→B
        drive_time_AB = instance.d_AB / instance.V[vtype]
        if transport.breaks_AB == 0:
            transport.breaks_AB = math.floor(drive_time_AB / instance.T_drive)
        
        # 4. Arrivée au site B
        if transport.arrival_B is None:
            transport.arrival_B = (transport.departure_A + drive_time_AB + 
                                  transport.breaks_AB * instance.T_break)
        
        # 5. Début et fin du déchargement
        if transport.unload_start_B is None:
            transport.unload_start_B = transport.arrival_B
        if transport.unload_end_B is None:
            transport.unload_end_B = transport.unload_start_B + instance.T_unload_B
        
        # 6. Si retour à A, calculer les temps de retour
        if transport.departure_B is not None:
            # Départ de B
            if transport.departure_B < transport.unload_end_B:
                transport.departure_B = transport.unload_end_B
            
            # Nombre de pauses pour B→A
            drive_time_BA = instance.d_BA / instance.V[vtype]
            if transport.breaks_BA == 0:
                transport.breaks_BA = math.floor(drive_time_BA / instance.T_drive)
            
            # Arrivée à A
            if transport.arrival_A is None:
                transport.arrival_A = (transport.departure_B + drive_time_BA + 
                                      transport.breaks_BA * instance.T_break)
            
            # Vérifier si le retour dépasse la journée de travail
            if transport.arrival_A > instance.T_end:
                transport.overnight_BA = True
        
        # Vérifier si le trajet dépasse la journée de travail
        if transport.unload_end_B > instance.T_end:
            transport.overnight_AB = True
    
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
            
            # Trier les transports par véhicule et séquence
            week_transports = sorted(transports_by_week[week], 
                                     key=lambda t: (t.vehicle_type, t.vehicle_idx, t.seq))
            
            for transport in week_transports:
                result.append(f"    {transport}")
                # Ajouter les détails horaires
                if transport.load_start_A is not None:
                    result.append(f"      Chargement A: {transport.load_start_A:.2f}h - {transport.load_end_A:.2f}h")
                    result.append(f"      Départ A: {transport.departure_A:.2f}h, Arrivée B: {transport.arrival_B:.2f}h")
                    result.append(f"      Déchargement B: {transport.unload_start_B:.2f}h - {transport.unload_end_B:.2f}h")
                    if transport.departure_B is not None:
                        result.append(f"      Départ B: {transport.departure_B:.2f}h, Arrivée A: {transport.arrival_A:.2f}h")
                    result.append(f"      Pauses: {transport.breaks_AB} (A→B), {transport.breaks_BA} (B→A)")
                    overnight = []
                    if transport.overnight_AB:
                        overnight.append("A→B")
                    if transport.overnight_BA:
                        overnight.append("B→A")
                    if overnight:
                        result.append(f"      Overnight: {', '.join(overnight)}")
        
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
            # Initialiser les demandes restantes pour cette semaine (uniquement A→B)
            remaining_weight_AB = instance.dw_AB[week]
            remaining_volume_AB = instance.dv_AB[week]
            
            # Trier les types de véhicules par ratio (capacité/coût) décroissant
            vehicle_types = sorted(instance.L.keys(), 
                                key=lambda vt: (instance.L[vt]["Qw"] + instance.L[vt]["Qv"]) / instance.c[vt], 
                                reverse=True)
            
            # Tant qu'il reste des demandes à satisfaire
            while remaining_weight_AB > 0 or remaining_volume_AB > 0:
                vehicle_assigned = False
                
                # Essayer chaque type de véhicule
                for vtype in vehicle_types:
                    capacity_w = instance.L[vtype]["Qw"]
                    capacity_v = instance.L[vtype]["Qv"]
                    
                    # Vérifier si ce type peut encore satisfaire une partie des demandes
                    if (remaining_weight_AB > 0 or remaining_volume_AB > 0):
                        
                        # Chercher un véhicule disponible de ce type
                        vehicle_found = False
                        
                        # On regarde d'abord les véhicules déjà utilisés cette semaine
                        vehicles_used_this_week = {}
                        for t in solution.transports:
                            if t.week == week and (t.vehicle_type, t.vehicle_idx) not in vehicles_used_this_week:
                                vehicles_used_this_week[(t.vehicle_type, t.vehicle_idx)] = max(
                                    [t2.seq for t2 in solution.transports 
                                    if t2.week == week and t2.vehicle_type == t.vehicle_type and t2.vehicle_idx == t.vehicle_idx]
                                )
                        
                        # D'abord, essayer les véhicules déjà utilisés cette semaine
                        for (used_vtype, used_vidx), max_seq in sorted(vehicles_used_this_week.items()):
                            if used_vtype == vtype:
                                # Vérifier si le véhicule peut faire un transport supplémentaire
                                # En regardant le dernier transport programmé
                                last_transports = [t for t in solution.transports 
                                                if t.week == week and t.vehicle_type == used_vtype 
                                                and t.vehicle_idx == used_vidx and t.seq == max_seq]
                                
                                if last_transports:
                                    last_transport = last_transports[0]
                                    
                                    # Calculer les temps si nécessaire
                                    if last_transport.arrival_A is None and last_transport.departure_B is not None:
                                        solution.compute_times_for_transport(last_transport)
                                    
                                    # Vérifier si le véhicule peut faire un transport supplémentaire
                                    # (s'il est de retour au site A et qu'il reste du temps dans la journée)
                                    next_start_time = (last_transport.arrival_A if last_transport.arrival_A is not None 
                                                    else instance.T_start)
                                    
                                    if next_start_time <= instance.T_end - 2:  # Au moins 2h avant la fin
                                        # Calculer les quantités à transporter
                                        weight_to_AB = min(remaining_weight_AB, capacity_w)
                                        volume_to_AB = min(remaining_volume_AB, capacity_v)
                                        
                                        # Créer le transport
                                        transport = Transport(
                                            week=week,
                                            vehicle_idx=used_vidx,
                                            vehicle_type=vtype,
                                            weight_AB=weight_to_AB,
                                            volume_AB=volume_to_AB,
                                            load_start_A=next_start_time,
                                            seq=max_seq + 1
                                        )
                                        
                                        # Calculer les temps
                                        solution.compute_times_for_transport(transport)
                                        
                                        # Si le transport est réalisable dans la journée
                                        if (not transport.overnight_AB or (transport.overnight_AB and transport.unload_end_B <= 
                                                                        instance.T_start + 24)):
                                            # Ajouter le départ retour si nécessaire
                                            transport.departure_B = transport.unload_end_B
                                            solution.compute_times_for_transport(transport)
                                            
                                            # Mettre à jour la solution
                                            solution.transports.append(transport)
                                            
                                            # Mettre à jour les demandes restantes
                                            remaining_weight_AB -= weight_to_AB
                                            remaining_volume_AB -= volume_to_AB
                                            
                                            vehicle_found = True
                                            vehicle_assigned = True
                                            break
                        
                        # Si aucun véhicule existant n'a pu être utilisé, chercher un nouveau
                        if not vehicle_found:
                            for veh_idx in range(1, instance.m[vtype] + 1):
                                vehicle_key = (vtype, veh_idx)
                                
                                # Vérifier si ce véhicule n'est pas déjà utilisé cette semaine
                                if week not in solution.vehicles[vehicle_key].weeks_used or vehicle_key not in vehicles_used_this_week:
                                    # Calculer les quantités à transporter
                                    weight_to_AB = min(remaining_weight_AB, capacity_w)
                                    volume_to_AB = min(remaining_volume_AB, capacity_v)
                                    
                                    # Créer le transport
                                    transport = Transport(
                                        week=week,
                                        vehicle_idx=veh_idx,
                                        vehicle_type=vtype,
                                        weight_AB=weight_to_AB,
                                        volume_AB=volume_to_AB,
                                        load_start_A=instance.T_start,  # Commence au début de la journée
                                        seq=1 if vehicle_key not in vehicles_used_this_week else vehicles_used_this_week[vehicle_key] + 1
                                    )
                                    
                                    # Calculer les temps
                                    solution.compute_times_for_transport(transport)
                                    
                                    # Ajouter le départ retour
                                    transport.departure_B = transport.unload_end_B
                                    solution.compute_times_for_transport(transport)
                                    
                                    # Mettre à jour la solution
                                    solution.transports.append(transport)
                                    solution.vehicles[vehicle_key].weeks_used.add(week)
                                    
                                    # Mettre à jour les demandes restantes
                                    remaining_weight_AB -= weight_to_AB
                                    remaining_volume_AB -= volume_to_AB
                                    
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
                    
                    # Créer un transport spécial (qui dépassera les capacités si nécessaire)
                    transport = Transport(
                        week=week,
                        vehicle_idx=veh_idx,
                        vehicle_type=vtype,
                        weight_AB=weight_to_AB,
                        volume_AB=volume_to_AB,
                        load_start_A=instance.T_start,
                        seq=1
                    )
                    
                    # Calculer les temps
                    solution.compute_times_for_transport(transport)
                    
                    solution.transports.append(transport)
                    solution.vehicles[(vtype, veh_idx)].weeks_used.add(week)
                    
                    # Mettre à jour les demandes restantes
                    remaining_weight_AB = 0
                    remaining_volume_AB = 0
        
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
                        load_start_A=transport.load_start_A,
                        load_end_A=transport.load_end_A,
                        departure_A=transport.departure_A,
                        arrival_B=transport.arrival_B,
                        unload_start_B=transport.unload_start_B,
                        unload_end_B=transport.unload_end_B,
                        departure_B=transport.departure_B,
                        arrival_A=transport.arrival_A,
                        breaks_AB=transport.breaks_AB,
                        breaks_BA=transport.breaks_BA,
                        seq=transport.seq
                    )
                    # Ajouter le transport au child
                    child.transports.append(new_transport)
                    # Mettre à jour l'utilisation des véhicules
                    child.vehicles[(transport.vehicle_type, transport.vehicle_idx)].weeks_used.add(week)
        
        # Évaluer le child
        child.evaluate()
        
        # Si le child n'est pas faisable, réparer la solution
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
            
            # Calculer les demandes restantes
            remaining_weight_AB = max(0, instance.dw_AB[week] - transported_weight_AB)
            remaining_volume_AB = max(0, instance.dv_AB[week] - transported_volume_AB)
            
            # S'il reste des demandes à satisfaire
            if remaining_weight_AB > 0 or remaining_volume_AB > 0:
                
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
                    if remaining_weight_AB <= capacity_w and remaining_volume_AB <= capacity_v:
                        
                        # Créer un nouveau transport
                        transport = Transport(
                            week=week,
                            vehicle_idx=idx,
                            vehicle_type=vtype,
                            weight_AB=remaining_weight_AB,
                            volume_AB=remaining_volume_AB,
                            load_start_A=instance.T_start,
                            seq=1  # Par défaut, premier transport de la journée
                        )
                        
                        # Calculer les temps pour le transport
                        solution.compute_times_for_transport(transport)
                        
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
                    
                    while remaining_weight_AB > 0 or remaining_volume_AB > 0:
                        
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
                                    
                                    # Créer le transport
                                    transport = Transport(
                                        week=week,
                                        vehicle_idx=idx,
                                        vehicle_type=vtype,
                                        weight_AB=weight_to_AB,
                                        volume_AB=volume_to_AB,
                                        load_start_A=instance.T_start,
                                        seq=1  # Par défaut, premier transport de la journée
                                    )
                                    
                                    # Calculer les temps pour le transport
                                    solution.compute_times_for_transport(transport)
                                    
                                    # Ajouter le retour
                                    transport.departure_B = transport.unload_end_B
                                    solution.compute_times_for_transport(transport)
                                    
                                    # Ajouter le transport à la solution
                                    solution.transports.append(transport)
                                    solution.vehicles[(vtype, idx)].weeks_used.add(week)
                                    
                                    # Mettre à jour les demandes restantes
                                    remaining_weight_AB -= weight_to_AB
                                    remaining_volume_AB -= volume_to_AB
                                    
                                    # Marquer le véhicule comme utilisé cette semaine
                                    vehicles_used_this_week.add((vtype, idx))
                                    
                                    vehicle_assigned = True
                                    break
                            
                            if vehicle_assigned:
                                break
                        
                        if not vehicle_assigned:
                            # Si nous arrivons ici, c'est qu'aucun véhicule supplémentaire n'est disponible
                            # Utiliser un véhicule déjà assigné pour cette semaine en ajoutant un second transport
                            
                            # Trouver un véhicule déjà utilisé cette semaine
                            used_vehicles = []
                            for t in solution.transports:
                                if t.week == week:
                                    used_vehicles.append((t.vehicle_type, t.vehicle_idx))
                            
                            if used_vehicles:
                                vtype, idx = used_vehicles[0]
                                capacity_w = instance.L[vtype]["Qw"]
                                capacity_v = instance.L[vtype]["Qv"]
                                
                                # Trouver la dernière séquence pour ce véhicule
                                last_seq = max([t.seq for t in solution.transports 
                                            if t.week == week and t.vehicle_type == vtype and t.vehicle_idx == idx])
                                
                                # Trouver le dernier transport de ce véhicule
                                last_transport = None
                                for t in solution.transports:
                                    if (t.week == week and t.vehicle_type == vtype and 
                                        t.vehicle_idx == idx and t.seq == last_seq):
                                        last_transport = t
                                        break
                                
                                if last_transport:
                                    # Calculer l'heure de début du nouveau transport
                                    if last_transport.arrival_A is None:
                                        solution.compute_times_for_transport(last_transport)
                                    
                                    next_start_time = last_transport.arrival_A
                                    
                                    # S'assurer que le prochain transport commence dans la journée de travail
                                    if next_start_time <= instance.T_end - 1:  # Au moins 1h avant la fin
                                        # Calculer les quantités à transporter
                                        weight_to_AB = min(remaining_weight_AB, capacity_w)
                                        volume_to_AB = min(remaining_volume_AB, capacity_v)
                                        
                                        # Créer le transport
                                        transport = Transport(
                                            week=week,
                                            vehicle_idx=idx,
                                            vehicle_type=vtype,
                                            weight_AB=weight_to_AB,
                                            volume_AB=volume_to_AB,
                                            load_start_A=next_start_time,
                                            seq=last_seq + 1
                                        )
                                        
                                        # Calculer les temps
                                        solution.compute_times_for_transport(transport)
                                        
                                        # Ajouter le retour
                                        transport.departure_B = transport.unload_end_B
                                        solution.compute_times_for_transport(transport)
                                        
                                        # Ajouter le transport à la solution
                                        solution.transports.append(transport)
                                        
                                        # Mettre à jour les demandes restantes
                                        remaining_weight_AB -= weight_to_AB
                                        remaining_volume_AB -= volume_to_AB
                                    else:
                                        # Si pas assez de temps, forcer l'utilisation d'un autre véhicule
                                        # ou arrêter (échec de l'opération de réparation)
                                        pass
                            else:
                                # Si on arrive ici, c'est qu'il n'y a pas de solution possible
                                break
        
        # Réévaluer la solution
        solution.evaluate()

def mutate(solution, instance, mutation_rate=0.3):
        """
        Opérateur de mutation qui modifie certains transports
        
        Args:
            solution: Solution à muter
            instance: Instance du problème
            mutation_rate: Probabilité de mutation d'une semaine
            
        Returns:
            Solution: Solution mutée
        """
        mutated = copy.deepcopy(solution)
        
        # Pour chaque semaine
        for week in instance.T:
            # Décider si cette semaine doit être mutée
            if random.random() < mutation_rate:
                # Récupérer tous les transports de cette semaine
                week_transports = [t for t in mutated.transports if t.week == week]
                
                # Si pas de transports cette semaine, passer à la suivante
                if not week_transports:
                    continue
                
                # Choisir une opération de mutation
                operations = ["split", "reassign", "replace_vehicle"]
                op = random.choice(operations)
                
                if op == "split" and len(week_transports) > 0:
                    # Diviser un transport en deux
                    t = random.choice(week_transports)
                    
                    # Vérifier s'il y a quelque chose à diviser
                    if t.weight_AB > 0 or t.volume_AB > 0:
                        
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
                                load_start_A=t.load_start_A,
                                seq=t.seq
                            )
                            
                            t2 = Transport(
                                week=week,
                                vehicle_idx=idx,
                                vehicle_type=vtype,
                                weight_AB=t.weight_AB * split_ratio,
                                volume_AB=t.volume_AB * split_ratio,
                                load_start_A=instance.T_start,
                                seq=1
                            )
                            
                            # Calculer les temps pour les transports
                            mutated.compute_times_for_transport(t1)
                            mutated.compute_times_for_transport(t2)
                            
                            # Ajouter les retours
                            t1.departure_B = t1.unload_end_B
                            t2.departure_B = t2.unload_end_B
                            mutated.compute_times_for_transport(t1)
                            mutated.compute_times_for_transport(t2)
                            
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
                        
                        if t.weight_AB <= capacity_w and t.volume_AB <= capacity_v:
                            
                            # Créer un nouveau transport avec le nouveau véhicule
                            new_t = Transport(
                                week=week,
                                vehicle_idx=idx,
                                vehicle_type=vtype,
                                weight_AB=t.weight_AB,
                                volume_AB=t.volume_AB,
                                load_start_A=t.load_start_A,
                                seq=1
                            )
                            
                            # Calculer les temps
                            mutated.compute_times_for_transport(new_t)
                            
                            # Ajouter le retour
                            new_t.departure_B = new_t.unload_end_B
                            mutated.compute_times_for_transport(new_t)
                            
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
                        if t.weight_AB <= instance.L[vtype]["Qw"] and t.volume_AB <= instance.L[vtype]["Qv"]:
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
                                load_start_A=t.load_start_A,
                                seq=1
                            )
                            
                            # Calculer les temps
                            mutated.compute_times_for_transport(new_t)
                            
                            # Ajouter le retour
                            new_t.departure_B = new_t.unload_end_B
                            mutated.compute_times_for_transport(new_t)
                            
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
        
        for iteration in range(max_iterations):
            # Essayer différentes opérations de voisinage
            # 1. Consolidation de véhicules
            improved = consolidate_vehicles(current, instance)
            if improved and improved.fitness < current.fitness:
                current = improved
                if current.fitness < best_fitness:
                    best = copy.deepcopy(current)
                    best_fitness = best.fitness
                    no_improvement_count = 0
                continue
            
            # 2. Réaffectation de charge
            improved = reassign_load(current, instance)
            if improved and improved.fitness < current.fitness:
                current = improved
                if current.fitness < best_fitness:
                    best = copy.deepcopy(current)
                    best_fitness = best.fitness
                    no_improvement_count = 0
                continue
            
            # 3. Changement de type de véhicule
            improved = change_vehicle_type(current, instance)
            if improved and improved.fitness < current.fitness:
                current = improved
                if current.fitness < best_fitness:
                    best = copy.deepcopy(current)
                    best_fitness = best.fitness
                    no_improvement_count = 0
                continue
            
            # Si aucune amélioration n'a été trouvée, incrémenter le compteur
            no_improvement_count += 1
            
            # Si trop d'itérations sans amélioration, arrêter
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
            
            # Parcourir tous les transports de cette semaine
            for i in range(len(week_transports)):
                if week_transports[i] is None:  # Si le transport a déjà été fusionné
                    continue
                    
                t1 = week_transports[i]
                
                # Chercher un autre transport qui pourrait être fusionné avec celui-ci
                for j in range(i+1, len(week_transports)):
                    if week_transports[j] is None:  # Si le transport a déjà été fusionné
                        continue
                        
                    t2 = week_transports[j]
                    
                    # Vérifier si les deux transports peuvent être fusionnés
                    # (même type de véhicule ou un autre type disponible avec capacité suffisante)
                    can_merge = False
                    merged_vehicle_type = None
                    merged_vehicle_idx = None
                    
                    # Cas 1: même type de véhicule, fusionner dans l'un des deux véhicules
                    if t1.vehicle_type == t2.vehicle_type:
                        capacity_w = instance.L[t1.vehicle_type]["Qw"]
                        capacity_v = instance.L[t1.vehicle_type]["Qv"]
                        
                        if (t1.weight_AB + t2.weight_AB <= capacity_w and
                            t1.volume_AB + t2.volume_AB <= capacity_v):
                            can_merge = True
                            merged_vehicle_type = t1.vehicle_type
                            merged_vehicle_idx = t1.vehicle_idx
                    
                    # Cas 2: différents types de véhicules, chercher un véhicule avec capacité suffisante
                    else:
                        for vtype in instance.L.keys():
                            capacity_w = instance.L[vtype]["Qw"]
                            capacity_v = instance.L[vtype]["Qv"]
                            
                            if (t1.weight_AB + t2.weight_AB <= capacity_w and
                                t1.volume_AB + t2.volume_AB <= capacity_v):
                                
                                # Chercher un véhicule disponible de ce type
                                for idx in range(1, instance.m[vtype] + 1):
                                    if (vtype != t1.vehicle_type or idx != t1.vehicle_idx) and \
                                    (vtype != t2.vehicle_type or idx != t2.vehicle_idx) and \
                                    week not in improved.vehicles[(vtype, idx)].weeks_used:
                                        can_merge = True
                                        merged_vehicle_type = vtype
                                        merged_vehicle_idx = idx
                                        break
                                
                                if can_merge:
                                    break
                    
                    if can_merge:
                        # Fusionner les deux transports
                        merged_transport = Transport(
                            week=week,
                            vehicle_idx=merged_vehicle_idx,
                            vehicle_type=merged_vehicle_type,
                            weight_AB=t1.weight_AB + t2.weight_AB,
                            volume_AB=t1.volume_AB + t2.volume_AB,
                            load_start_A=min(t1.load_start_A, t2.load_start_A) if t2.load_start_A is not None else t1.load_start_A,
                            seq=1
                        )
                        
                        # Calculer les temps pour le nouveau transport
                        improved.compute_times_for_transport(merged_transport)
                        
                        # Ajouter le retour
                        merged_transport.departure_B = merged_transport.unload_end_B
                        improved.compute_times_for_transport(merged_transport)
                        
                        # Supprimer les anciens transports et ajouter le nouveau
                        improved.transports = [t for t in improved.transports if t != t1 and t != t2]
                        improved.transports.append(merged_transport)
                        
                        # Mettre à jour les semaines d'utilisation des véhicules
                        improved.vehicles[(t1.vehicle_type, t1.vehicle_idx)].weeks_used.discard(week)
                        improved.vehicles[(t2.vehicle_type, t2.vehicle_idx)].weeks_used.discard(week)
                        improved.vehicles[(merged_vehicle_type, merged_vehicle_idx)].weeks_used.add(week)
                                
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
                    
                    # Vérifier si une réaffectation est possible
                    # (par exemple, transférer une partie de la charge de t1 à t2)
                    if t1.weight_AB > 0 and t1.volume_AB > 0:
                        # Vérifier si t2 a de la capacité restante
                        capacity_w_t2 = instance.L[t2.vehicle_type]["Qw"] - t2.weight_AB
                        capacity_v_t2 = instance.L[t2.vehicle_type]["Qv"] - t2.volume_AB
                        
                        if capacity_w_t2 > 0 and capacity_v_t2 > 0:
                            # Calculer la quantité à transférer (au plus 50%)
                            transfer_ratio = min(0.5, min(capacity_w_t2 / t1.weight_AB, capacity_v_t2 / t1.volume_AB))
                            
                            if transfer_ratio > 0.1:  # Transférer au moins 10%
                                weight_to_transfer = t1.weight_AB * transfer_ratio
                                volume_to_transfer = t1.volume_AB * transfer_ratio
                                
                                # Mettre à jour les charges
                                t1.weight_AB -= weight_to_transfer
                                t1.volume_AB -= volume_to_transfer
                                t2.weight_AB += weight_to_transfer
                                t2.volume_AB += volume_to_transfer
                                
                                # Recalculer les temps pour les deux transports
                                improved.compute_times_for_transport(t1)
                                improved.compute_times_for_transport(t2)
        
        # Évaluer la solution améliorée
        improved.evaluate()
        
        # Vérifier si la solution est meilleure
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
        
        # Pour chaque semaine
        for week in instance.T:
            # Récupérer tous les transports de cette semaine par véhicule
            transports_by_vehicle = {}
            for t in improved.transports:
                if t.week == week:
                    key = (t.vehicle_type, t.vehicle_idx)
                    if key not in transports_by_vehicle:
                        transports_by_vehicle[key] = []
                    transports_by_vehicle[key].append(t)
            
            # Pour chaque véhicule utilisé cette semaine
            for (vtype, vidx), transports in transports_by_vehicle.items():
                # Calculer la charge totale de ce véhicule
                total_weight = sum(t.weight_AB for t in transports)
                total_volume = sum(t.volume_AB for t in transports)
                
                # Chercher un type de véhicule plus adapté
                for new_type in instance.L.keys():
                    if new_type != vtype:
                        # Vérifier si le nouveau type peut contenir toutes les charges
                        if (total_weight <= instance.L[new_type]["Qw"] and 
                            total_volume <= instance.L[new_type]["Qv"]):
                            
                            # Vérifier s'il y a un véhicule disponible du nouveau type
                            available_vehicles = []
                            for i in range(1, instance.m[new_type] + 1):
                                # Vérifier si ce véhicule est disponible cette semaine
                                if week not in improved.vehicles[(new_type, i)].weeks_used:
                                    available_vehicles.append(i)
                            
                            if available_vehicles:
                                # Sélectionner un véhicule disponible
                                new_idx = min(available_vehicles)
                                
                                # Calculer le coût avant et après changement
                                cost_before = instance.c[vtype]
                                cost_after = instance.c[new_type]
                                
                                # Si le coût diminue ou reste le même, faire le changement
                                if cost_after <= cost_before:
                                    # Mettre à jour tous les transports de ce véhicule
                                    for t in transports:
                                        t.vehicle_type = new_type
                                        t.vehicle_idx = new_idx
                                        
                                        # Recalculer les temps
                                        improved.compute_times_for_transport(t)
                                    
                                    # Mettre à jour l'utilisation des véhicules
                                    improved.vehicles[(vtype, vidx)].weeks_used.discard(week)
                                    improved.vehicles[(new_type, new_idx)].weeks_used.add(week)
        
        # Évaluer la solution améliorée
        improved.evaluate()
        
        # Vérifier si la solution est meilleure
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
        
        # Calculer l'utilisation des véhicules par semaine
        vehicles_by_week = {}
        for week in instance.T:
            vehicles_by_week[week] = set()
            for t in improved.transports:
                if t.week == week:
                    vehicles_by_week[week].add((t.vehicle_type, t.vehicle_idx))
        
        # Identifier les semaines avec peu de véhicules et les semaines chargées
        light_weeks = sorted(instance.T, key=lambda w: len(vehicles_by_week[w]))
        heavy_weeks = sorted(instance.T, key=lambda w: len(vehicles_by_week[w]), reverse=True)
        
        # Essayer de déplacer des charges des semaines chargées vers les semaines légères
        for heavy_week in heavy_weeks[:3]:  # Essayer avec les 3 semaines les plus chargées
            for light_week in light_weeks[:3]:  # Essayer avec les 3 semaines les moins chargées
                if heavy_week == light_week:
                    continue
                    
                # Vérifier si la semaine légère a des véhicules disponibles
                heavy_vehicles = vehicles_by_week[heavy_week]
                light_vehicles = vehicles_by_week[light_week]
                
                # Trouver des véhicules utilisés dans la semaine chargée mais pas dans la légère
                for vtype, vidx in heavy_vehicles:
                    if (vtype, vidx) not in light_vehicles:
                        # Ce véhicule pourrait être utilisé dans la semaine légère
                        # Chercher un transport de la semaine chargée qu'on pourrait déplacer
                        for t in improved.transports:
                            if t.week == heavy_week and t.vehicle_type == vtype and t.vehicle_idx == vidx:
                                # Vérifier si ce transport peut être déplacé vers la semaine légère
                                # (c'est une heuristique simple, on vérifie juste les capacités)
                                can_move = True
                                
                                if can_move:
                                    # Déplacer le transport vers la semaine légère
                                    t.week = light_week
                                    
                                    # Mettre à jour l'utilisation des véhicules
                                    improved.vehicles[(vtype, vidx)].weeks_used.add(light_week)
                                    
                                    # Vérifier si c'était le seul transport de ce véhicule dans la semaine chargée
                                    remaining_transports = [t2 for t2 in improved.transports 
                                                        if t2.week == heavy_week and 
                                                        t2.vehicle_type == vtype and 
                                                        t2.vehicle_idx == vidx]
                                    
                                    if not remaining_transports:
                                        improved.vehicles[(vtype, vidx)].weeks_used.discard(heavy_week)
                                        vehicles_by_week[heavy_week].discard((vtype, vidx))
                                    
                                    # Ajouter à la liste des véhicules de la semaine légère
                                    vehicles_by_week[light_week].add((vtype, vidx))
                                    
                                    # Réévaluer si c'est faisable
                                    improved.evaluate()
                                    if not improved.feasible:
                                        # Si non faisable, réparer la solution
                                        repair_solution(improved, instance)
                                        
                                    # Vérifier si on a réduit le nombre total de véhicules
                                    if improved.fitness < solution.fitness:
                                        return improved
        
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
        # Générer la population initiale
        population = []
        for _ in range(population_size):
            solution = greedy_initial_solution(instance)
            population.append(solution)
        
        # Évaluer la population initiale
        for solution in population:
            solution.evaluate()
        
        # Meilleure solution trouvée
        best_solution = min(population, key=lambda s: s.fitness)
        
        # Boucle principale de l'algorithme
        for gen in range(generations):
            # Afficher la progression
            if gen % 10 == 0:
                print(f"Génération {gen}/{generations}, meilleure fitness: {best_solution.fitness}")
            
            # Appliquer la recherche locale périodiquement
            if gen % local_search_freq == 0:
                # Appliquer la recherche locale sur une partie de la population
                for i in range(min(5, population_size)):
                    # Sélectionner un individu aléatoire
                    index = random.randint(0, population_size - 1)
                    # Appliquer la recherche locale
                    improved = local_search(population[index], instance)
                    # Remplacer si amélioré
                    if improved.fitness < population[index].fitness:
                        population[index] = improved
                        # Mettre à jour la meilleure solution si nécessaire
                        if improved.fitness < best_solution.fitness:
                            best_solution = copy.deepcopy(improved)
            
            # Créer une nouvelle génération
            new_population = []
            
            # Élitisme: garder les 2 meilleures solutions
            sorted_population = sorted(population, key=lambda s: s.fitness)
            new_population.extend(copy.deepcopy(sorted_population[:2]))
            
            # Remplir le reste de la population avec des enfants
            while len(new_population) < population_size:
                # Sélectionner deux parents
                parent1 = tournament_selection(population)
                parent2 = tournament_selection(population)
                
                # Croisement
                child = crossover(parent1, parent2, instance)
                
                # Mutation
                if random.random() < mutation_rate:
                    child = mutate(child, instance)
                
                # Ajouter l'enfant à la nouvelle population
                new_population.append(child)
            
            # Remplacer l'ancienne population
            population = new_population
            
            # Mettre à jour la meilleure solution
            current_best = min(population, key=lambda s: s.fitness)
            if current_best.fitness < best_solution.fitness:
                best_solution = copy.deepcopy(current_best)
        
        # Appliquer une dernière recherche locale à la meilleure solution
        final_solution = local_search(best_solution, instance)
        if final_solution.fitness < best_solution.fitness:
            best_solution = final_solution
        
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

def save_solution(solution, filename):
        """
        Sauvegarde une solution dans un fichier JSON
        
        Args:
            solution: Solution à sauvegarder
            filename: Nom du fichier
        """
        # Convertir la solution en dictionnaire
        solution_dict = {
            "fitness": solution.fitness,
            "feasible": solution.feasible,
            "vehicles_used": sum(1 for v in solution.vehicles.values() if v.is_used()),
            "transports": []
        }
        
        # Ajouter les transports
        for t in solution.transports:
            transport_dict = {
                "week": t.week,
                "vehicle_type": t.vehicle_type,
                "vehicle_idx": t.vehicle_idx,
                "weight_AB": t.weight_AB,
                "volume_AB": t.volume_AB,
                "load_start_A": t.load_start_A,
                "load_end_A": t.load_end_A,
                "departure_A": t.departure_A,
                "arrival_B": t.arrival_B,
                "unload_start_B": t.unload_start_B,
                "unload_end_B": t.unload_end_B,
                "departure_B": t.departure_B,
                "arrival_A": t.arrival_A,
                "breaks_AB": t.breaks_AB,
                "breaks_BA": t.breaks_BA,
                "seq": t.seq
            }
            solution_dict["transports"].append(transport_dict)
        
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
            print("Matplotlib non disponible, visualisation impossible")
            return
        
        # Configurer le graphique
        fig, ax = plt.subplots(figsize=(15, 10))
        
        # Couleurs pour les différents types de véhicules
        colors = {1: 'lightblue', 2: 'lightgreen'}
        
        # Pour chaque semaine
        for week in instance.T:
            # Récupérer les transports de cette semaine
            week_transports = [t for t in solution.transports if t.week == week]
            
            # Trier par véhicule et séquence
            week_transports.sort(key=lambda t: (t.vehicle_type, t.vehicle_idx, t.seq))
            
            # Afficher chaque transport
            y_pos = week
            for i, transport in enumerate(week_transports):
                # Calculer les positions temporelles
                if transport.load_start_A is None or transport.arrival_A is None:
                    solution.compute_times_for_transport(transport)
                
                # Calculer la largeur de chaque bloc
                load_width = transport.load_end_A - transport.load_start_A
                travel_AB_width = transport.arrival_B - transport.departure_A
                unload_width = transport.unload_end_B - transport.unload_start_B
                
                if transport.departure_B is not None:
                    travel_BA_width = transport.arrival_A - transport.departure_B
                else:
                    travel_BA_width = 0
                
                # Dessiner les blocs
                # Chargement
                ax.add_patch(
                    patches.Rectangle(
                        (transport.load_start_A, y_pos - 0.3),
                        load_width,
                        0.6,
                        facecolor=colors[transport.vehicle_type],
                        alpha=0.7,
                        edgecolor='black'
                    )
                )
                ax.text(transport.load_start_A + load_width/2, y_pos, 
                    f"Load\n{transport.weight_AB:.1f}kg/{transport.volume_AB:.1f}m³", 
                    ha='center', va='center', fontsize=8)
                
                # Trajet A→B
                ax.add_patch(
                    patches.Rectangle(
                        (transport.departure_A, y_pos - 0.3),
                        travel_AB_width,
                        0.6,
                        facecolor='lightcoral',
                        alpha=0.7,
                        edgecolor='black'
                    )
                )
                ax.text(transport.departure_A + travel_AB_width/2, y_pos, 
                    f"A→B\n{transport.breaks_AB} pauses", 
                    ha='center', va='center', fontsize=8)
                
                # Déchargement
                ax.add_patch(
                    patches.Rectangle(
                        (transport.unload_start_B, y_pos - 0.3),
                        unload_width,
                        0.6,
                        facecolor=colors[transport.vehicle_type],
                        alpha=0.7,
                        edgecolor='black'
                    )
                )
                ax.text(transport.unload_start_B + unload_width/2, y_pos, 
                    "Unload", 
                    ha='center', va='center', fontsize=8)
                
                # Trajet B→A (si retour)
                if transport.departure_B is not None:
                    ax.add_patch(
                        patches.Rectangle(
                            (transport.departure_B, y_pos - 0.3),
                            travel_BA_width,
                            0.6,
                            facecolor='lightsalmon',
                            alpha=0.7,
                            edgecolor='black'
                        )
                    )
                    ax.text(transport.departure_B + travel_BA_width/2, y_pos, 
                        f"B→A\n{transport.breaks_BA} pauses", 
                        ha='center', va='center', fontsize=8)
                
                # Étiquette pour le véhicule
                ax.text(instance.T_start - 1, y_pos, 
                    f"V{transport.vehicle_type}-{transport.vehicle_idx} #{transport.seq}", 
                    ha='right', va='center', fontsize=10)
        
        # Configurer les axes
        ax.set_xlim(instance.T_start - 2, instance.T_end + 2)
        ax.set_ylim(0, len(instance.T) + 1)
        ax.set_yticks(range(1, len(instance.T) + 1))
        ax.set_yticklabels([f"Semaine {w}" for w in instance.T])
        ax.set_xlabel('Heure de la journée')
        ax.set_ylabel('Semaine')
        ax.set_title(f'Planning des transports (Véhicules utilisés: {solution.fitness})')
        
        # Ajouter une grille
        ax.grid(True, linestyle='--', alpha=0.6)
        
        # Ajouter une légende
        legend_elements = [
            patches.Patch(facecolor='lightblue', alpha=0.7, edgecolor='black', label='Véhicule Type 1'),
            patches.Patch(facecolor='lightgreen', alpha=0.7, edgecolor='black', label='Véhicule Type 2'),
            patches.Patch(facecolor='lightcoral', alpha=0.7 , edgecolor='black', label='Trajet A→B'),
            patches.Patch(facecolor='lightsalmon', alpha=0.7, edgecolor='black', label='Trajet B→A')
        ]


def repair_solution(solution, instance):
        """
        Répare une solution non faisable en ajoutant des transports manquants
        
        Args:
            solution: Solution à réparer
            instance: Instance du problème
        """
        # Pour chaque semaine, vérifier si toutes les demandes sont satisfaites
        for week in instance.T:
            # Calculer les quantités déjà transportées cette semaine
            transported_weight_AB = sum(t.weight_AB for t in solution.transports if t.week == week)
            transported_volume_AB = sum(t.volume_AB for t in solution.transports if t.week == week)
            
            # Calculer les demandes restantes
            remaining_weight_AB = max(0, instance.dw_AB[week] - transported_weight_AB)
            remaining_volume_AB = max(0, instance.dv_AB[week] - transported_volume_AB)
            
            # S'il reste des demandes à satisfaire
            if remaining_weight_AB > 0 or remaining_volume_AB > 0:
                
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
                    if remaining_weight_AB <= capacity_w and remaining_volume_AB <= capacity_v:
                        
                        # Créer un nouveau transport
                        transport = Transport(
                            week=week,
                            vehicle_idx=idx,
                            vehicle_type=vtype,
                            weight_AB=remaining_weight_AB,
                            volume_AB=remaining_volume_AB,
                            load_start_A=instance.T_start,
                            seq=1  # Par défaut, premier transport de la journée
                        )
                        
                        # Calculer les temps pour le transport
                        solution.compute_times_for_transport(transport)
                        
                        # Ajouter le retour
                        transport.departure_B = transport.unload_end_B
                        solution.compute_times_for_transport(transport)
                        
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
                    
                    while remaining_weight_AB > 0 or remaining_volume_AB > 0:
                        
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
                                    
                                    # Créer le transport
                                    transport = Transport(
                                        week=week,
                                        vehicle_idx=idx,
                                        vehicle_type=vtype,
                                        weight_AB=weight_to_AB,
                                        volume_AB=volume_to_AB,
                                        load_start_A=instance.T_start,
                                        seq=1  # Par défaut, premier transport de la journée
                                    )
                                    
                                    # Calculer les temps pour le transport
                                    solution.compute_times_for_transport(transport)
                                    
                                    # Ajouter le retour
                                    transport.departure_B = transport.unload_end_B
                                    solution.compute_times_for_transport(transport)
                                    
                                    # Ajouter le transport à la solution
                                    solution.transports.append(transport)
                                    solution.vehicles[(vtype, idx)].weeks_used.add(week)
                                    
                                    # Mettre à jour les demandes restantes
                                    remaining_weight_AB -= weight_to_AB
                                    remaining_volume_AB -= volume_to_AB
                                    
                                    # Marquer le véhicule comme utilisé cette semaine
                                    vehicles_used_this_week.add((vtype, idx))
                                    
                                    vehicle_assigned = True
                                    break
                            
                            if vehicle_assigned:
                                break
                        
                        # Si aucun véhicule additionnel n'est disponible, essayer de réutiliser un véhicule
                        if not vehicle_assigned:
                            # Chercher un véhicule déjà utilisé cette semaine avec un temps disponible
                            used_vehicles = sorted(vehicles_used_this_week)
                            
                            for vtype, idx in used_vehicles:
                                # Trouver le dernier transport pour ce véhicule
                                last_seq = max([t.seq for t in solution.transports 
                                            if t.week == week and t.vehicle_type == vtype and t.vehicle_idx == idx], 
                                            default=0)
                                
                                last_transport = None
                                for t in solution.transports:
                                    if (t.week == week and t.vehicle_type == vtype and 
                                        t.vehicle_idx == idx and t.seq == last_seq):
                                        last_transport = t
                                        break
                                
                                if last_transport:
                                    # S'assurer que les temps sont calculés
                                    if last_transport.arrival_A is None and last_transport.departure_B is not None:
                                        solution.compute_times_for_transport(last_transport)
                                    
                                    # Vérifier s'il reste du temps dans la journée
                                    next_start = last_transport.arrival_A if last_transport.arrival_A is not None else instance.T_end
                                    
                                    if next_start <= instance.T_end - 2:  # Au moins 2h avant la fin
                                        capacity_w = instance.L[vtype]["Qw"]
                                        capacity_v = instance.L[vtype]["Qv"]
                                        
                                        weight_to_AB = min(remaining_weight_AB, capacity_w)
                                        volume_to_AB = min(remaining_volume_AB, capacity_v)
                                        
                                        # Créer un nouveau transport
                                        transport = Transport(
                                            week=week,
                                            vehicle_idx=idx,
                                            vehicle_type=vtype,
                                            weight_AB=weight_to_AB,
                                            volume_AB=volume_to_AB,
                                            load_start_A=next_start,
                                            seq=last_seq + 1
                                        )
                                        
                                        # Calculer les temps
                                        solution.compute_times_for_transport(transport)
                                        
                                        # Ajouter le retour
                                        transport.departure_B = transport.unload_end_B
                                        solution.compute_times_for_transport(transport)
                                        
                                        # Ajouter le transport à la solution
                                        solution.transports.append(transport)
                                        
                                        # Mettre à jour les demandes restantes
                                        remaining_weight_AB -= weight_to_AB
                                        remaining_volume_AB -= volume_to_AB
                                        
                                        vehicle_assigned = True
                                        break
                            
                            # Si on ne peut pas réutiliser un véhicule, c'est qu'on a un problème
                            if not vehicle_assigned:
                                # En dernier recours, forcer l'utilisation d'un véhicule du plus grand type
                                vtype = max(instance.L.keys(), key=lambda t: instance.L[t]["Qw"] + instance.L[t]["Qv"])
                                idx = 1  # Prendre le premier véhicule par défaut
                                
                                # Forcer la création d'un transport (qui pourrait être infaisable)
                                transport = Transport(
                                    week=week,
                                    vehicle_idx=idx,
                                    vehicle_type=vtype,
                                    weight_AB=remaining_weight_AB,
                                    volume_AB=remaining_volume_AB,
                                    load_start_A=instance.T_start,
                                    seq=1
                                )
                                
                                solution.compute_times_for_transport(transport)
                                
                                # Ajouter le transport sans se soucier des contraintes temporelles
                                solution.transports.append(transport)
                                solution.vehicles[(vtype, idx)].weeks_used.add(week)
                                
                                # Considérer les demandes comme satisfaites (même si ce n'est pas réaliste)
                                remaining_weight_AB = 0
                                remaining_volume_AB = 0
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
        
        # Pour chaque semaine, calculer le nombre minimum de véhicules théoriques nécessaires
        for week in instance.T:
            # Demandes totales pour cette semaine
            week_weight = instance.dw_AB[week]
            week_volume = instance.dv_AB[week]
            
            # Calculer combien de véhicules de chaque type seraient nécessaires pour cette semaine
            vehicles_needed_by_type = {}
            for vtype in instance.L.keys():
                # Nombre de véhicules basé sur le poids
                veh_by_weight = math.ceil(week_weight / instance.L[vtype]["Qw"])
                # Nombre de véhicules basé sur le volume
                veh_by_volume = math.ceil(week_volume / instance.L[vtype]["Qv"])
                # Prendre le maximum des deux
                vehicles_needed_by_type[vtype] = max(veh_by_weight, veh_by_volume)
            
            # Considérer la stratégie optimale: utiliser d'abord les véhicules les plus grands
            vehicles_sorted = sorted(instance.L.keys(), 
                                key=lambda vt: instance.L[vt]["Qw"] + instance.L[vt]["Qv"], 
                                reverse=True)
            
            # Calculer le nombre minimal de véhicules nécessaires en utilisant cette stratégie
            remaining_weight = week_weight
            remaining_volume = week_volume
            vehicles_count = 0
            
            for vtype in vehicles_sorted:
                veh_capacity_w = instance.L[vtype]["Qw"]
                veh_capacity_v = instance.L[vtype]["Qv"]
                veh_available = instance.m[vtype]
                
                for _ in range(veh_available):
                    if remaining_weight <= 0 and remaining_volume <= 0:
                        break
                        
                    # Ce véhicule peut transporter tout ou partie de ce qui reste
                    weight_transported = min(remaining_weight, veh_capacity_w)
                    volume_transported = min(remaining_volume, veh_capacity_v)
                    
                    if weight_transported > 0 or volume_transported > 0:
                        remaining_weight -= weight_transported
                        remaining_volume -= volume_transported
                        vehicles_count += 1
                    else:
                        break
            
            # Si après avoir utilisé tous les véhicules disponibles, il reste des demandes
            # c'est que la solution est infaisable
            if remaining_weight > 0 or remaining_volume > 0:
                print(f"Semaine {week}: Demandes trop élevées pour la flotte disponible!")
                return False
            
            # Mettre à jour le minimum de véhicules nécessaires sur toutes les semaines
            min_vehicles_needed = min(min_vehicles_needed, vehicles_count)
        
        # Compter le nombre de véhicules distincts utilisés dans la solution
        vehicles_used = sum(1 for vehicle in solution.vehicles.values() if vehicle.is_used())
        
        print(f"\nBorne inférieure théorique: {min_vehicles_needed} véhicule(s)")
        print(f"Véhicules distincts utilisés: {vehicles_used}")
        
        # La solution est optimale si elle utilise exactement le nombre minimum de véhicules
        return vehicles_used <= min_vehicles_needed
def main():
    """
    Fonction principale pour exécuter l'algorithme de transport.
    """
    # Créer une instance du problème
    instance = Instance()
    
    # Afficher les informations de l'instance
    print("Instance créée avec succès :")
    print(f"Nombre de semaines : {len(instance.T)}")
    print(f"Types de véhicules disponibles : {instance.L}")
    print(f"Nombre de véhicules par type : {instance.m}")
    print("\nDemandes hebdomadaires :")
    for week in instance.T:
        print(f"Semaine {week}: A→B: {instance.dw_AB[week]} kg, {instance.dv_AB[week]} m³")
    
    # Résoudre le problème avec l'algorithme mémétique
    print("\nExécution de l'algorithme mémétique...")
    start_time = time.time()
    best_solution = memetic_algorithm(instance)
    end_time = time.time()
    
    # Afficher les résultats
    print("\nMeilleure solution trouvée :")
    print(best_solution.detailed_str())
    
    # Sauvegarder la solution dans un fichier
    save_solution(best_solution, "best_solution.json")
    
    # Visualiser la solution
    visualize_solution(best_solution, instance)
    
    # Vérifier si la solution est optimale
    optimal = is_optimal(best_solution, instance)
    print(f"\nLa solution est-elle optimale ? {'Oui' if optimal else 'Non'}")
    
    print(f"\nTemps d'exécution : {end_time - start_time:.2f} secondes")
    return best_solution
if __name__ == "__main__":
    import math  # Ajout de l'import math nécessaire pour la fonction is_optimal
    
    # Exécuter la fonction principale
    best_solution = main()