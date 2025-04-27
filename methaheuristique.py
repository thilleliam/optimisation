import numpy as np
import random
import copy
import time
from collections import defaultdict

class Instance:
    def __init__(self):
        # Instance adaptée pour des navettes entre sites sur 10 semaines
        self.V = [f"site{i}" for i in range(6)]  # Sites 0 à 5
        self.depot = "site0"  # Le dépôt central
        
        # Arêtes avec leurs coûts et classes d'accès
        self.E = {
            ("site0", "site1"): {"cost": 10, "classes": {1, 2}},
            ("site0", "site2"): {"cost": 15, "classes": {1, 2}},
            ("site0", "site3"): {"cost": 20, "classes": {1, 2}},
            ("site0", "site4"): {"cost": 18, "classes": {1, 2}},
            ("site0", "site5"): {"cost": 22, "classes": {1, 2}},
            ("site1", "site2"): {"cost": 7, "classes": {1, 2}},
            ("site1", "site3"): {"cost": 12, "classes": {1, 2}},
            ("site1", "site4"): {"cost": 14, "classes": {1, 2}},
            ("site1", "site5"): {"cost": 16, "classes": {1, 2}},
            ("site2", "site3"): {"cost": 9, "classes": {1, 2}},
            ("site2", "site4"): {"cost": 8, "classes": {1, 2}},
            ("site2", "site5"): {"cost": 11, "classes": {1, 2}},
            ("site3", "site4"): {"cost": 5, "classes": {1, 2}},
            ("site3", "site5"): {"cost": 9, "classes": {1, 2}},
            ("site4", "site5"): {"cost": 6, "classes": {1, 2}}
        }
        edges_copy = copy.deepcopy(self.E)
        for (u, v), data in edges_copy.items():
            if (v, u) not in self.E:
                self.E[(v, u)] = data
        for u in self.V:
            for v in self.V:
                if u != v and (u, v) not in self.E:
                    self.E[(u, v)] = {"cost": float('inf'), "classes": set()}
        
        # Rendre les arêtes non orientées
        edges_copy = copy.deepcopy(self.E)
        for (u, v), data in edges_copy.items():
            self.E[(v, u)] = data
        
        # Sites à desservir
        self.VR = ["site1", "site2", "site3", "site4", "site5"]
        self.c = {}
        for (u, v), data in self.E.items():
            for vehicle_class in [1, 2]:  # Classes de véhicules disponibles
                if vehicle_class in data["classes"]:
                    self.c[(u, v, vehicle_class)] = data["cost"]
        
        # Périodes (10 semaines)
        self.P = list(range(1, 11))
        self.np = 10
        
        # Types de véhicules
        self.L = {
            1: {"Qw": 150, "Qv": 70},  # Véhicule de capacité moyenne
            2: {"Qw": 300, "Qv": 120}  # Véhicule de grande capacité
        }
        
        # Véhicules disponibles par classe et type
        self.m = {
            (1, 1): 6,  # 3 véhicules de classe 1, type 1
            (1, 2): 8,  # 2 véhicules de classe 1, type 2
            (2, 1): 4,  # 3 véhicules de classe 2, type 1
            (2, 2): 3   # 2 véhicules de classe 2, type 2
        }
        
        # Initialiser les demandes pour 10 semaines
        self.dw = {}
        self.dv = {}
        
        # Génération de demandes avec variation hebdomadaire
        base_demands_w = {
            "site1": 20,
            "site2": 25,
            "site3": 30,
            "site4": 40,
            "site5": 25
    }
    
        base_demands_v = {
            "site1": 8,
            "site2": 12,
            "site3": 15,
            "site4": 20,
            "site5": 10
    }
        
        # Définir les demandes avec fluctuations par semaine
        # Définir les demandes avec fluctuations réduites par semaine
        for site in self.VR:
            self.dw[site] = {}
            self.dv[site] = {}
            for p in self.P:
                # Variation hebdomadaire entre 90% et 110% de la demande de base
                week_factor = 0.9 + 0.2 * random.random()
                self.dw[site][p] = int(base_demands_w[site] * week_factor)
                self.dv[site][p] = int(base_demands_v[site] * week_factor)
            
        # Fréquences de visite hebdomadaire pour chaque site
        # Fréquences de visite hebdomadaire réduites
        self.eta = {
            "site1": 2,  # Réduit de 4 à 3
            "site2": 2,  # Réduit de 5 à 4
            "site3": 3,  # Réduit de 7 à 5
            "site4": 2,  # Réduit de 6 à 4
            "site5": 1   # Réduit de 3 à 2
        }
        # Définition des périodes admissibles simplifiée
        self.APC = {}
        for site in self.VR:
            self.APC[site] = []
            # Toutes les périodes sont admissibles
            for p in self.P:
                self.APC[site].append({p})
        
        # Réduire les dessertes obligatoires
        self.Treq = {
            ("site3", 2), ("site3", 8),  # Site 3 doit être desservi aux semaines 2 et 8
            ("site4", 1),                # Site 4 doit être desservi à la semaine 1
            ("site1", 3), ("site5", 7)   # Autres dessertes obligatoires
        }
        
        # Calculer les demandes accumulées
        self.adw = {}
        self.adv = {}
        for t in self.VR:
            self.adw[t] = {}
            self.adv[t] = {}
            for p in self.P:
                self.adw[t][p] = self.dw[t][p]
                self.adv[t][p] = self.dv[t][p]
        
        # Définir les navettes récurrentes (nombre réduit)
        self.shuttles = [
            # (site_départ, site_arrivée, semaine_début, fréquence)
            ("site1", "site3", 1, 2),  # Navette entre site1 et site3 commençant semaine 1, toutes les 2 semaines
            ("site2", "site4", 2, 3)   # Navette entre site2 et site4 commençant semaine 2, toutes les 3 semaines
        ]
            
       
    def nodes(self):
        """Retourne l'ensemble des nœuds du graphe."""
        return self.V

class Shuttle:
    def __init__(self, origin, destination, vehicle_class, vehicle_type, period):
        self.origin = origin
        self.destination = destination
        self.vehicle_class = vehicle_class
        self.vehicle_type = vehicle_type
        self.period = period
        self.load_weight = 0
        self.load_volume = 0
        self.cost = 0
    
    def can_transport(self, weight, volume, capacity_w, capacity_v):
        return (self.load_weight + weight <= capacity_w and
                self.load_volume + volume <= capacity_v)
    
    def add_cargo(self, weight, volume):
        self.load_weight += weight
        self.load_volume += volume
    
    def __str__(self):
        return (f"Navette({self.origin}->{self.destination}, "
                f"période={self.period}, classe={self.vehicle_class}, "
                f"type={self.vehicle_type}, charge={self.load_weight}/{self.load_volume})")

def build_adjacency_list(instance):
    """Construire la liste d'adjacence du graphe"""
    adj_list = defaultdict(list)
    for (u, v), data in instance.E.items():
        adj_list[u].append((v, data["cost"], data["classes"]))
    return adj_list

def calculate_shortest_paths(instance, adj_list):
    """Calculer les plus courts chemins entre toutes les paires de nœuds"""
    nodes = instance.V
    n = len(nodes)
    dist = {(u, v): float('inf') for u in nodes for v in nodes}
    next_node = {(u, v): None for u in nodes for v in nodes}
    path_classes = {(u, v): set() for u in nodes for v in nodes}
    
    # Initialiser les distances
    for u in nodes:
        dist[(u, u)] = 0
        path_classes[(u, u)] = {1, 2}  # Toutes les classes peuvent rester sur place
    
    for u in nodes:
        for v, cost, classes in adj_list[u]:
            dist[(u, v)] = cost
            next_node[(u, v)] = v
            path_classes[(u, v)] = classes
    
    # Algorithme de Floyd-Warshall
    for k in nodes:
        for i in nodes:
            for j in nodes:
                if dist[(i, k)] + dist[(k, j)] < dist[(i, j)]:
                    dist[(i, j)] = dist[(i, k)] + dist[(k, j)]
                    next_node[(i, j)] = next_node[(i, k)]
                    # Les classes d'accès pour un chemin sont l'intersection des classes des sous-chemins
                    path_classes[(i, j)] = path_classes[(i, k)].intersection(path_classes[(k, j)])
    
    # Reconstruire les chemins
    paths = {}
    for u in nodes:
        for v in nodes:
            if u != v and next_node[(u, v)] is not None:
                path = [u]
                current = u
                while current != v:
                    current = next_node[(current, v)]
                    path.append(current)
                paths[(u, v)] = path
            elif u == v:
                paths[(u, v)] = [u]
            else:
                paths[(u, v)] = []
    
    return dist, paths, path_classes

class Route:
    def __init__(self, period, vehicle_class, vehicle_type):
        self.period = period
        self.vehicle_class = vehicle_class
        self.vehicle_type = vehicle_type
        self.nodes = []  # Liste des nœuds visités
        self.deliveries = {}  # Quantités livrées à chaque nœud
        self.load_weight = 0
        self.load_volume = 0
        self.cost = 0
        self.is_shuttle = False  # Indique si c'est une navette fixe
        self.shuttle_origin = None
        self.shuttle_destination = None
    # Nouvelle méthode pour calculer l'utilisation du poids
    def weight_utilization(self, instance):
        max_weight = instance.L[self.vehicle_type]["Qw"]
        return self.load_weight / max_weight if max_weight > 0 else 0

    # Méthode pour calculer l'utilisation du volume
    def volume_utilization(self, instance):
        max_volume = instance.L[self.vehicle_type]["Qv"]
        return self.load_volume / max_volume if max_volume > 0 else 0
    def add_node(self, node, delivery_weight, delivery_volume, distance):
        self.nodes.append(node)
        self.deliveries[node] = (delivery_weight, delivery_volume)
        self.load_weight += delivery_weight
        self.load_volume += delivery_volume
        self.cost += distance
    
    def can_add_node(self, node, delivery_weight, delivery_volume, instance):
        # Vérifier si les capacités sont respectées
        if (self.load_weight + delivery_weight > instance.L[self.vehicle_type]["Qw"] or
            self.load_volume + delivery_volume > instance.L[self.vehicle_type]["Qv"]):
            return False
        return True
    
    def set_as_shuttle(self, origin, destination):
        self.is_shuttle = True
        self.shuttle_origin = origin
        self.shuttle_destination = destination
        # Vider la liste des nœuds et recréer pour la navette
        self.nodes = [origin, destination]
    
    def __str__(self):
        if self.is_shuttle:
            return (f"Navette(période={self.period}, classe={self.vehicle_class}, "
                    f"type={self.vehicle_type}, {self.shuttle_origin}->{self.shuttle_destination}, "
                    f"coût={self.cost:.2f})")
        else:
            return (f"Route(période={self.period}, classe={self.vehicle_class}, "
                    f"type={self.vehicle_type}, nœuds={self.nodes}, coût={self.cost:.2f})")

class Solution:
    def __init__(self, instance):
        self.instance = instance
        self.routes = []
        self.shuttles = []  # Liste des navettes fixes
        self.node_visits = {node: set() for node in instance.VR}  # Périodes où chaque nœud est visité
        self.fitness = float('inf')
        self.feasible = False
    
    def evaluate(self):
        """
        Évalue la solution en calculant son coût et en vérifiant sa faisabilité
        """
        total_cost = 0
        feasible = True
        
        # Création d'une structure pour suivre les visites par noeud et période
        self.node_visits = defaultdict(set)
        
        # Évaluer chaque route
        for route in self.routes:
            # Calculer le coût de la route
            route_cost = 0
            
            # Ajouter les coûts des trajets entre dépôt et premier noeud et entre dernier noeud et dépôt
            if route.nodes:
                if (self.instance.depot, route.nodes[0], route.vehicle_class) in self.instance.c:
                    route_cost += self.instance.c[(self.instance.depot, route.nodes[0], route.vehicle_class)]
                else:
                    print(f"Clé manquante dans self.c : {(self.instance.depot, route.nodes[0], route.vehicle_class)}")
                    route_cost += float('inf')  # Ou une valeur par défaut
            
                
                # Coût entre les noeuds de la route
                for i in range(len(route.nodes) - 1):
                    if route.nodes[i] == route.nodes[i + 1]:
                        print(f"Nœuds dupliqués détectés dans la route : {route.nodes[i]} -> {route.nodes[i + 1]}. Ignoré.")
                        continue
                    route_cost += self.instance.c[(route.nodes[i], route.nodes[i + 1], route.vehicle_class)]
            else:
                print("Route sans nœuds détectée. Ignorée dans l'évaluation.")
                continue
            for i in range(len(route.nodes) - 1):
                key = (route.nodes[i], route.nodes[i + 1], route.vehicle_class)
                if key in self.instance.c:
                    route_cost += self.instance.c[key]
                else:
                    print(f"Clé manquante dans self.c : {key}. Ignoré.")
                    route_cost += float('inf')  # Ou une valeur par défaut
            if (self.instance.depot, route.nodes[0], route.vehicle_class) in self.instance.c:
                route_cost += self.instance.c[(self.instance.depot, route.nodes[0], route.vehicle_class)]
            else:
                print(f"Clé manquante dans self.c : {(self.instance.depot, route.nodes[0], route.vehicle_class)}")
                route_cost += float('inf')  # Ou une valeur par défaut
            # Vérifier si c'est une navette
            if hasattr(route, 'is_shuttle') and route.is_shuttle:
                # Pour les navettes, vérifier l'existence des attributs origin et destination
                if hasattr(route, 'shuttle_origin') and hasattr(route, 'shuttle_destination'):
                    # Calculer le coût de la navette
                    route_cost = self.instance.c[(self.instance.depot, route.shuttle_origin, route.vehicle_class)]
                    route_cost += self.instance.c[(route.shuttle_origin, route.shuttle_destination, route.vehicle_class)]
                    route_cost += self.instance.c[(route.shuttle_destination, self.instance.depot, route.vehicle_class)]
                    
                    # Marquer les visites pour les deux noeuds de la navette
                    self.node_visits[route.shuttle_origin].add(route.period)
                    self.node_visits[route.shuttle_destination].add(route.period)
                else:
                    # Si la navette n'a pas les attributs nécessaires, c'est une erreur
                    feasible = False
                    route_cost = float('inf')
            else:
                # Marquer les visites pour tous les noeuds de la route standard
                for node in route.nodes:
                    self.node_visits[node].add(route.period)
            
            # Mettre à jour le coût de la route
            route.cost = route_cost
            total_cost += route_cost
        
        # Évaluer chaque navette fixe
        for shuttle in self.shuttles:
            # Calculer le coût de la navette
            shuttle_cost = self.instance.c[(self.instance.depot, shuttle.shuttle_origin, shuttle.vehicle_class)]
            shuttle_cost += self.instance.c[(shuttle.shuttle_origin, shuttle.shuttle_destination, shuttle.vehicle_class)]
            shuttle_cost += self.instance.c[(shuttle.shuttle_destination, self.instance.depot, shuttle.vehicle_class)]
            
            # Marquer les visites pour les deux noeuds de la navette
            self.node_visits[shuttle.shuttle_origin].add(shuttle.period)
            self.node_visits[shuttle.shuttle_destination].add(shuttle.period)
            
            # Mettre à jour le coût de la navette
            shuttle.cost = shuttle_cost
            total_cost += shuttle_cost
        
        # Vérifier les contraintes de fréquence de visite
        for node in self.instance.V:
            if node != self.instance.depot:
                # Vérifier que chaque site est visité suffisamment
                if len(self.node_visits[node]) < self.instance.eta[node]:
                    feasible = False
        
        # Vérifier les contraintes de desserte obligatoire
        for node, period in self.instance.Treq:
            if period not in self.node_visits[node]:
                feasible = False
        
        # Vérifier les contraintes de périodes admissibles pour chaque site
        for node, periods in self.node_visits.items():
            # Vérifier si les périodes de visite sont admissibles pour ce site
            if periods and not any(periods.issubset(set(period_set)) for period_set in self.instance.APC[node]):
                feasible = False
        
        # Calculer la fitness
        self.fitness = total_cost
        self.feasible = feasible
        return self.fitness
        
    def __str__(self):
        return f"Solution(routes={len(self.routes)}, navettes={len(self.shuttles)}, fitness={self.fitness:.2f}, feasible={self.feasible})"
    
    def detailed_str(self):
        result = [f"Solution avec {len(self.routes)} routes, {len(self.shuttles)} navettes, coût={self.fitness:.2f}, faisable={self.feasible}"]
        for i, route in enumerate(self.routes):
            result.append(f"  Route {i+1}: {route}")
        for i, shuttle in enumerate(self.shuttles):
            result.append(f"  Navette {i+1}: {shuttle}")
        return "\n".join(result)

def create_shuttles(instance, dist, paths=None, path_classes=None):
    """Créer les navettes fixes entre sites selon les spécifications de l'instance"""
    shuttles = []
    
    for origin, destination, start_week, frequency in instance.shuttles:
        # Déterminer toutes les périodes pour cette navette
        periods = list(range(start_week, instance.np + 1, frequency))
        
        for p in periods:
            # Trouver une classe de véhicule qui peut accéder aux deux sites
            valid_classes = []
            for c in [1, 2]:
                if (c in path_classes.get((instance.depot, origin), set()) and
                    c in path_classes.get((origin, destination), set()) and
                    c in path_classes.get((destination, instance.depot), set())):
                    valid_classes.append(c)
            
            if not valid_classes:
                continue  # Aucune classe valide pour cette navette
            
            # Choisir un type de véhicule adapté aux demandes
            vehicle_class = valid_classes[0]
            vehicle_type = None
            total_weight = instance.adw[origin][p] + instance.adw[destination][p]
            total_volume = instance.adv[origin][p] + instance.adv[destination][p]
            
            for l in sorted(instance.L.keys()):
                if (total_weight <= instance.L[l]["Qw"] and
                    total_volume <= instance.L[l]["Qv"]):
                    vehicle_type = l
                    break
            
            if vehicle_type is None:
                vehicle_type = max(instance.L.keys())  # Prendre le plus grand type si nécessaire
            
            # Créer la navette
            shuttle = Route(p, vehicle_class, vehicle_type)
            shuttle.set_as_shuttle(origin, destination)
            
            # Calculer le coût
            depot_to_origin = dist.get((instance.depot, origin), 0)
            origin_to_dest = dist.get((origin, destination), 0)
            dest_to_depot = dist.get((destination, instance.depot), 0)
            
            shuttle.cost = depot_to_origin + origin_to_dest + dest_to_depot
            
            # Ajouter les livraisons
            shuttle.deliveries[origin] = (instance.adw[origin][p], instance.adv[origin][p])
            shuttle.deliveries[destination] = (instance.adw[destination][p], instance.adv[destination][p])
            shuttle.load_weight = instance.adw[origin][p] + instance.adw[destination][p]
            shuttle.load_volume = instance.adv[origin][p] + instance.adv[destination][p]
            
            shuttles.append(shuttle)
    
    return shuttles

def greedy_initial_solution(instance, dist, paths, path_classes):
    # Initialisation - utiliser dist au lieu de shortest_paths[0]
    distance = {}
    for n in instance.nodes():
        distance[n] = {}
        
        # Utiliser dist directement
        for k in instance.nodes():
            distance[n][k] = dist.get((n, k), float('inf'))
    
    solution = Solution(instance)
    
    # Créer les navettes fixes - passer dist, paths, path_classes comme arguments séparés
    solution.shuttles = create_shuttles(instance, dist, paths, path_classes)
    
    # Marquer les demandes servies par les navettes comme satisfaites
    remaining_demand_w = copy.deepcopy(instance.adw)
    remaining_demand_v = copy.deepcopy(instance.adv)
    
    for shuttle in solution.shuttles:
        p = shuttle.period
        for node, (w, v) in shuttle.deliveries.items():
            remaining_demand_w[node][p] = max(0, remaining_demand_w[node][p] - w)
            remaining_demand_v[node][p] = max(0, remaining_demand_v[node][p] - v)
    
    # Pour chaque période
    for p in instance.P:
        # Pour chaque classe de véhicule
        for c in [1, 2]:
            # Pour chaque type de véhicule
            for l in instance.L.keys():
                # Compter combien de ce type de véhicule est déjà utilisé par des navettes
                used_in_shuttles = 0
                for shuttle in solution.shuttles:
                    if (shuttle.period == p and 
                        shuttle.vehicle_class == c and 
                        shuttle.vehicle_type == l):
                        used_in_shuttles += 1
                
                # Vérifier la disponibilité restante
                vehicles_available = instance.m.get((c, l), 0) - used_in_shuttles
                if vehicles_available <= 0:
                    continue
                
                for _ in range(vehicles_available):
                    route = Route(p, c, l)
                    current_node = instance.depot
                    route_modified = True
                    
                    # Continuer tant qu'on peut ajouter des nœuds à la route
                    while route_modified:
                        route_modified = False
                        best_node = None
                        best_saving = -float('inf')
                        best_delivery_w = 0
                        best_delivery_v = 0
                        
                        # Parcourir tous les nœuds avec demande restante
                        for node in instance.VR:
                            if remaining_demand_w[node][p] > 0 or remaining_demand_v[node][p] > 0:
                                # Vérifier l'accessibilité
                                if not path_classes.get((current_node, node), set()) or c not in path_classes[(current_node, node)]:
                                    continue
                                
                                # Calculer la livraison maximale possible
                                delivery_w = remaining_demand_w[node][p]
                                delivery_v = remaining_demand_v[node][p]
                                
                                # Vérifier si le véhicule peut livrer cette quantité
                                if not route.can_add_node(node, delivery_w, delivery_v, instance):
                                    continue
                                
                                # Calculer l'économie (distance à parcourir vs quantité livrée)
                                distance_to_node = dist.get((current_node, node), float('inf'))
                                saving = (delivery_w + delivery_v) / (distance_to_node + 1)  # +1 pour éviter division par zéro
                                
                                if saving > best_saving:
                                    best_saving = saving
                                    best_node = node
                                    best_delivery_w = delivery_w
                                    best_delivery_v = delivery_v
                        
                        # Si on a trouvé un nœud à ajouter
                        if best_node:
                            distance_to_best = dist.get((current_node, best_node), 0)
                            route.add_node(best_node, best_delivery_w, best_delivery_v, distance_to_best)
                            remaining_demand_w[best_node][p] = 0
                            remaining_demand_v[best_node][p] = 0
                            current_node = best_node
                            route_modified = True
                    
                    # Si la route contient des livraisons, l'ajouter à la solution
                    if len(route.nodes) > 0:
                        # Ajouter le coût de retour au dépôt
                        return_distance = dist.get((current_node, instance.depot), 0)
                        route.cost += return_distance
                        solution.routes.append(route)
    
    solution.evaluate()
    return solution
def crossover(parent1, parent2, instance, dist, paths=None, path_classes=None):
    """Opérateur de croisement qui combine des routes et navettes de deux parents"""
    child = Solution(instance)
    
    # Sélectionner aléatoirement des routes de chaque parent
    p1_routes = random.sample(parent1.routes, k=len(parent1.routes) // 2 if parent1.routes else 0)
    p2_routes = random.sample(parent2.routes, k=len(parent2.routes) // 2 if parent2.routes else 0)
    
    # Sélectionner des navettes
    p1_shuttles = random.sample(parent1.shuttles, k=len(parent1.shuttles) // 2 if parent1.shuttles else 0)
    p2_shuttles = random.sample(parent2.shuttles, k=len(parent2.shuttles) // 2 if parent2.shuttles else 0)
    
    # Combiner les routes et navettes
    child.routes = p1_routes + p2_routes
    for route in child.routes:
        route.nodes = [node for i, node in enumerate(route.nodes) if i == 0 or node != route.nodes[i - 1]]
    child.shuttles = p1_shuttles + p2_shuttles
    
    # Évaluer la solution enfant
    child.evaluate()
    
    return child

def mutate(solution, instance, dist, paths=None, path_classes=None, mutation_rate=0.3):
    """Opérateur de mutation qui modifie certaines routes et navettes"""
    # Muter les routes standard
    for i in range(len(solution.routes)):
        if random.random() < mutation_rate:
            # Appliquer un des opérateurs de mutation
            op = random.choice(["swap", "insert", "remove", "replace"])
            
            if op == "swap" and len(solution.routes[i].nodes) >= 2:
                idx = random.randint(0, len(solution.routes[i].nodes) - 2)
                if solution.routes[i].nodes[idx] != solution.routes[i].nodes[idx + 1]:
                    solution.routes[i].nodes[idx], solution.routes[i].nodes[idx + 1] = solution.routes[i].nodes[idx + 1], solution.routes[i].nodes[idx]
                # Échanger deux nœuds consécutifs
                idx = random.randint(0, len(solution.routes[i].nodes) - 2)
                solution.routes[i].nodes[idx], solution.routes[i].nodes[idx + 1] = solution.routes[i].nodes[idx + 1], solution.routes[i].nodes[idx]
            
            elif op == "insert" and solution.routes[i].nodes:
                # Insérer un nœud aléatoire
                available_nodes = list(set(instance.VR) - set(solution.routes[i].nodes))
                if available_nodes:
                    node_to_insert = random.choice(available_nodes)
                    pos = random.randint(0, len(solution.routes[i].nodes))
                    solution.routes[i].nodes.insert(pos, node_to_insert)
                    
                    # Mise à jour des livraisons (simplifié)
                    w_demand = min(instance.adw[node_to_insert][solution.routes[i].period], 
                                 instance.L[solution.routes[i].vehicle_type]["Qw"] - solution.routes[i].load_weight)
                    v_demand = min(instance.adv[node_to_insert][solution.routes[i].period],
                                 instance.L[solution.routes[i].vehicle_type]["Qv"] - solution.routes[i].load_volume)
                    
                    solution.routes[i].deliveries[node_to_insert] = (w_demand, v_demand)
                    solution.routes[i].load_weight += w_demand
                    solution.routes[i].load_volume += v_demand
            
            elif op == "remove" and solution.routes[i].nodes:
                # Supprimer un nœud aléatoire
                idx = random.randint(0, len(solution.routes[i].nodes) - 1)
                node_to_remove = solution.routes[i].nodes[idx]
                w_delivered, v_delivered = solution.routes[i].deliveries.get(node_to_remove, (0, 0))
                
                solution.routes[i].nodes.pop(idx)
                if node_to_remove in solution.routes[i].deliveries:
                    del solution.routes[i].deliveries[node_to_remove]
                
                solution.routes[i].load_weight -= w_delivered
                solution.routes[i].load_volume -= v_delivered
            
            elif op == "replace" and solution.routes[i].nodes:
                # Remplacer un nœud par un autre
                available_nodes = list(set(instance.VR) - set(solution.routes[i].nodes))
                if available_nodes:
                    idx = random.randint(0, len(solution.routes[i].nodes) - 1)
                    node_to_replace = solution.routes[i].nodes[idx]
                    new_node = random.choice(available_nodes)
                    
                    # Retirer l'ancien nœud
                    w_old, v_old = solution.routes[i].deliveries.get(node_to_replace, (0, 0))
                    solution.routes[i].load_weight -= w_old
                    solution.routes[i].load_volume -= v_old
                    
                    # Ajouter le nouveau
                    solution.routes[i].nodes[idx] = new_node
                    w_demand = min(instance.adw[new_node][solution.routes[i].period], 
                                 instance.L[solution.routes[i].vehicle_type]["Qw"] - solution.routes[i].load_weight)
                    v_demand = min(instance.adv[new_node][solution.routes[i].period],
                                 instance.L[solution.routes[i].vehicle_type]["Qv"] - solution.routes[i].load_volume)
                    
                    solution.routes[i].deliveries[new_node] = (w_demand, v_demand)
                    solution.routes[i].load_weight += w_demand
                    solution.routes[i].load_volume += v_demand
            
            # Recalculer le coût de la route
            route = solution.routes[i]
            route.cost = 0
            prev_node = instance.depot
            
            for node in route.nodes:
                route.cost += dist.get((prev_node, node), 0)
                prev_node = node
            
            # Ajouter le coût de retour au dépôt
            route.cost += dist.get((prev_node, instance.depot), 0)
    
    # Muter les navettes (avec une probabilité plus faible car elles sont fixes)
    for i in range(len(solution.shuttles)):
        if random.random() < mutation_rate * 0.5:
            # Pour les navettes, on peut juste modifier le type de véhicule si possible
            current_shuttle = solution.shuttles[i]
            
            # Essayer de changer de type de véhicule
            current_type = current_shuttle.vehicle_type
            
            # Liste des types de véhicules disponibles de la même classe
            available_types = []
            for l in instance.L.keys():
                if l != current_type and instance.m.get((current_shuttle.vehicle_class, l), 0) > 0:
                    # Vérifier si ce type peut transporter la charge
                    if (current_shuttle.load_weight <= instance.L[l]["Qw"] and
                        current_shuttle.load_volume <= instance.L[l]["Qv"]):
                        available_types.append(l)
            
            if available_types:
                # Changer le type de véhicule
                new_type = random.choice(available_types)
                current_shuttle.vehicle_type = new_type
                
                # Pas besoin de recalculer le coût car il dépend du trajet, pas du type de véhicule
    
    # Évaluer la solution après les mutations
    solution.evaluate()
    solution = consolidate_routes(solution, instance)
    return solution
def consolidate_routes(solution, instance):
    # Trier les routes par période
    routes_by_period = {}
    for route in solution.routes:
        if route.period not in routes_by_period:
            routes_by_period[route.period] = []
        routes_by_period[route.period].append(route)
    
    # Pour chaque période, essayer de consolider les routes
    for period, routes in routes_by_period.items():
        # Trier les routes par utilisation
        routes.sort(key=lambda r: r.weight_utilization(instance) + r.volume_utilization(instance))
        
        # Tant qu'il y a plus d'une route et que la première route est sous-utilisée
        i = 0
        while i < len(routes) - 1:
            current_route = routes[i]
            if current_route.weight_utilization(instance) >= 0.7 or current_route.volume_utilization(instance) >= 0.7:
                i += 1
                continue
            
            # Chercher une route compatible pour fusionner
            for j in range(i + 1, len(routes)):
                next_route = routes[j]
                if (current_route.vehicle_class == next_route.vehicle_class and 
                    current_route.vehicle_type == next_route.vehicle_type):
                    # Vérifier si la fusion est possible (capacité)
                    if (current_route.load_weight + next_route.load_weight <= instance.L[current_route.vehicle_type]["Qw"] and
                        current_route.load_volume + next_route.load_volume <= instance.L[current_route.vehicle_type]["Qv"]):
                        # Fusion des routes
                        current_route.nodes.extend(next_route.nodes)
                        current_route.load_weight += next_route.load_weight
                        current_route.load_volume += next_route.load_volume
                        routes.pop(j)
                        # Ne pas incrémenter i pour essayer de fusionner avec d'autres routes
                        break
            else:
                # Aucune fusion possible, passer à la route suivante
                i += 1
    
    # Reconstruire la liste complète des routes
    solution.routes = []
    for period_routes in routes_by_period.values():
        solution.routes.extend(period_routes)
    
    return solution
def local_search(solution, instance, dist, paths=None, path_classes=None, max_iterations=100):
    """Recherche locale pour améliorer une solution"""
    best_solution = copy.deepcopy(solution)
    best_fitness = solution.fitness
    
    for _ in range(max_iterations):
        # Créer une copie de la solution actuelle
        current = copy.deepcopy(best_solution)
        
        # Appliquer une perturbation
        improved = False
        
        # Choisir un opérateur de recherche locale
        op = random.choice(["2-opt", "relocate", "exchange", "swap-vehicle"])
        
        if op == "2-opt" and current.routes:
            # Choisir une route aléatoire (pas une navette)
            if not current.routes:
                continue
                
            route_idx = random.randint(0, len(current.routes) - 1)
            route = current.routes[route_idx]
            
            # Inverser un segment de la route si possible
            if len(route.nodes) >= 4:
                i = random.randint(0, len(route.nodes) - 4)
                j = random.randint(i + 2, len(route.nodes) - 1)
                
                # Inverser le segment
                route.nodes[i:j+1] = reversed(route.nodes[i:j+1])
                
                # Recalculer le coût
                route.cost = 0
                prev_node = instance.depot
                for node in route.nodes:
                    route.cost += dist.get((prev_node, node), 0)
                    prev_node = node
                route.cost += dist.get((prev_node, instance.depot), 0)
                
                improved = True
        
        elif op == "relocate" and len(current.routes) >= 2:
            # Déplacer un nœud d'une route à une autre (pas pour les navettes)
            if len(current.routes) < 2:
                continue
                
            route_idx1 = random.randint(0, len(current.routes) - 1)
            route_idx2 = random.randint(0, len(current.routes) - 1)
            
            # Ignorer si c'est une navette fixe
            if current.routes[route_idx1].is_shuttle or current.routes[route_idx2].is_shuttle:
                continue
            
            if route_idx1 != route_idx2 and current.routes[route_idx1].nodes:
                # Choisir un nœud à déplacer
                node_idx = random.randint(0, len(current.routes[route_idx1].nodes) - 1)
                node = current.routes[route_idx1].nodes[node_idx]
                
                # Vérifier la compatibilité
                if (current.routes[route_idx1].period == current.routes[route_idx2].period and
                    current.routes[route_idx2].vehicle_class in path_classes.get((instance.depot, node), set())):
                    # Récupérer les quantités livrées
                    w_delivered, v_delivered = current.routes[route_idx1].deliveries.get(node, (0, 0))
                    
                    # Vérifier la capacité
                    if (current.routes[route_idx2].load_weight + w_delivered <= instance.L[current.routes[route_idx2].vehicle_type]["Qw"] and
                        current.routes[route_idx2].load_volume + v_delivered <= instance.L[current.routes[route_idx2].vehicle_type]["Qv"]):
                        
                        # Supprimer de la première route
                        current.routes[route_idx1].nodes.remove(node)
                        if node in current.routes[route_idx1].deliveries:
                            w_delivered, v_delivered = current.routes[route_idx1].deliveries[node]
                            current.routes[route_idx1].load_weight -= w_delivered
                            current.routes[route_idx1].load_volume -= v_delivered
                            del current.routes[route_idx1].deliveries[node]
                        
                        # Ajouter à la seconde route
                        insert_pos = random.randint(0, len(current.routes[route_idx2].nodes))
                        current.routes[route_idx2].nodes.insert(insert_pos, node)
                        current.routes[route_idx2].deliveries[node] = (w_delivered, v_delivered)
                        current.routes[route_idx2].load_weight += w_delivered
                        current.routes[route_idx2].load_volume += v_delivered
                        
                        # Recalculer les coûts
                        for idx in [route_idx1, route_idx2]:
                            route = current.routes[idx]
                            route.cost = 0
                            prev_node = instance.depot
                            for n in route.nodes:
                                route.cost += dist.get((prev_node, n), 0)
                                prev_node = n
                            route.cost += dist.get((prev_node, instance.depot), 0)
                        
                        improved = True
        
        elif op == "exchange" and len(current.routes) >= 2:
            # Échanger deux nœuds entre deux routes (pas pour les navettes)
            if len(current.routes) < 2:
                continue
            
            route_idx1 = random.randint(0, len(current.routes) - 1)
            route_idx2 = random.randint(0, len(current.routes) - 1)
            
            # Ignorer si c'est une navette fixe
            if current.routes[route_idx1].is_shuttle or current.routes[route_idx2].is_shuttle:
                continue
            
            if (route_idx1 != route_idx2 and 
                current.routes[route_idx1].nodes and 
                current.routes[route_idx2].nodes and
                current.routes[route_idx1].period == current.routes[route_idx2].period):
                
                # Choisir les nœuds à échanger
                node_idx1 = random.randint(0, len(current.routes[route_idx1].nodes) - 1)
                node_idx2 = random.randint(0, len(current.routes[route_idx2].nodes) - 1)
                
                node1 = current.routes[route_idx1].nodes[node_idx1]
                node2 = current.routes[route_idx2].nodes[node_idx2]
                
                # Vérifier l'accessibilité
                if (current.routes[route_idx1].vehicle_class in path_classes.get((instance.depot, node2), set()) and
                    current.routes[route_idx2].vehicle_class in path_classes.get((instance.depot, node1), set())):
                    
                    # Récupérer les quantités livrées
                    w1, v1 = current.routes[route_idx1].deliveries.get(node1, (0, 0))
                    w2, v2 = current.routes[route_idx2].deliveries.get(node2, (0, 0))
                    
                    # Vérifier les capacités après échange
                    if (current.routes[route_idx1].load_weight - w1 + w2 <= instance.L[current.routes[route_idx1].vehicle_type]["Qw"] and
                        current.routes[route_idx1].load_volume - v1 + v2 <= instance.L[current.routes[route_idx1].vehicle_type]["Qv"] and
                        current.routes[route_idx2].load_weight - w2 + w1 <= instance.L[current.routes[route_idx2].vehicle_type]["Qw"] and
                        current.routes[route_idx2].load_volume - v2 + v1 <= instance.L[current.routes[route_idx2].vehicle_type]["Qv"]):
                        
                        # Échanger les nœuds
                        current.routes[route_idx1].nodes[node_idx1] = node2
                        current.routes[route_idx2].nodes[node_idx2] = node1
                        
                        # Mettre à jour les livraisons
                        current.routes[route_idx1].deliveries[node2] = (w2, v2)
                        current.routes[route_idx2].deliveries[node1] = (w1, v1)
                        
                        if node1 in current.routes[route_idx1].deliveries:
                            del current.routes[route_idx1].deliveries[node1]
                        if node2 in current.routes[route_idx2].deliveries:
                            del current.routes[route_idx2].deliveries[node2]
                        
                        # Mettre à jour les charges
                        current.routes[route_idx1].load_weight = current.routes[route_idx1].load_weight - w1 + w2
                        current.routes[route_idx1].load_volume = current.routes[route_idx1].load_volume - v1 + v2
                        current.routes[route_idx2].load_weight = current.routes[route_idx2].load_weight - w2 + w1
                        current.routes[route_idx2].load_volume = current.routes[route_idx2].load_volume - v2 + v1
                        
                        # Recalculer les coûts
                        for idx in [route_idx1, route_idx2]:
                            route = current.routes[idx]
                            route.cost = 0
                            prev_node = instance.depot
                            for n in route.nodes:
                                route.cost += dist.get((prev_node, n), 0)
                                prev_node = n
                            route.cost += dist.get((prev_node, instance.depot), 0)
                        
                        improved = True
def repair_solution(solution, instance, dist, paths=None, path_classes=None):
    """Essaie de réparer une solution non réalisable"""
    # Créer une copie de la solution
    repaired = copy.deepcopy(solution)
    
    # Vérifier et réparer les contraintes de fréquence
    for node, visits in repaired.node_visits.items():
        # Si le nœud n'est pas visité suffisamment
        if len(visits) < instance.eta[node]:
            # Périodes où le nœud n'est pas visité
            missing_periods = set(instance.P) - visits
            
            # Périodes admissibles non encore utilisées
            valid_periods = []
            for period_set in instance.APC[node]:
                if not visits.issubset(period_set):
                    # Trouver les périodes manquantes qui sont dans ce period_set
                    potential_periods = set(period_set) - visits
                    valid_periods.extend(list(potential_periods.intersection(missing_periods)))
            
            # Si aucune période valide, essayer toutes les périodes manquantes
            if not valid_periods:
                valid_periods = list(missing_periods)
            
            # Essayer d'ajouter le nœud à des routes existantes ou créer de nouvelles routes
            for p in valid_periods:
                # Demandes pour cette période
                demand_w = instance.adw[node][p]
                demand_v = instance.adv[node][p]
                
                # Chercher une route existante pouvant accueillir ce nœud
                added = False
                for route in repaired.routes:
                    # Ignorer les navettes fixes
                    if route.is_shuttle:
                        continue
                        
                    if route.period == p and route.can_add_node(node, demand_w, demand_v, instance):
                        # Vérifier l'accessibilité
                        if route.nodes:
                            last_node = route.nodes[-1]
                            if (route.vehicle_class not in path_classes.get((last_node, node), set()) or
                                route.vehicle_class not in path_classes.get((node, instance.depot), set())):
                                continue
                        
                        # Ajouter le nœud à la route
                        prev_node = route.nodes[-1] if route.nodes else instance.depot
                        distance_to_node = dist.get((prev_node, node), 0)
                        route.add_node(node, demand_w, demand_v, distance_to_node)
                        
                        # Recalculer le coût de retour au dépôt
                        route.cost += dist.get((node, instance.depot), 0) - dist.get((prev_node, instance.depot), 0)
                        
                        added = True
                        break
                
                # Si nécessaire, créer une nouvelle route
                if not added:
                    # Trouver un véhicule disponible capable de desservir ce nœud
                    for c in [1, 2]:
                        if c not in path_classes.get((instance.depot, node), set()):
                            continue
                        
                        for l in instance.L.keys():
                            if (demand_w <= instance.L[l]["Qw"] and 
                                demand_v <= instance.L[l]["Qv"] and
                                instance.m.get((c, l), 0) > 0):
                                
                                # Créer une nouvelle route
                                route = Route(p, c, l)
                                distance_to_node = dist.get((instance.depot, node), 0)
                                route.add_node(node, demand_w, demand_v, distance_to_node)
                                
                                # Ajouter le coût de retour au dépôt
                                route.cost += dist.get((node, instance.depot), 0)
                                
                                repaired.routes.append(route)
                                added = True
                                break
                        
                        if added:
                            break
    
    # Vérifier et réparer les contraintes de desserte obligatoire
    for (node, period) in instance.Treq:
        if period not in repaired.node_visits.get(node, set()):
            # Le nœud doit être desservi à cette période mais ne l'est pas
            demand_w = instance.adw[node][period]
            demand_v = instance.adv[node][period]
            
            # Chercher une route existante
            added = False
            for route in repaired.routes:
                # Ignorer les navettes fixes
                if route.is_shuttle:
                    continue
                    
                if route.period == period and route.can_add_node(node, demand_w, demand_v, instance):
                    # Vérifier l'accessibilité
                    if route.nodes:
                        last_node = route.nodes[-1]
                        if (route.vehicle_class not in path_classes.get((last_node, node), set()) or
                            route.vehicle_class not in path_classes.get((node, instance.depot), set())):
                            continue
                    
                    # Ajouter le nœud à la route
                    prev_node = route.nodes[-1] if route.nodes else instance.depot
                    distance_to_node = dist.get((prev_node, node), 0)
                    route.add_node(node, demand_w, demand_v, distance_to_node)
                    
                    # Recalculer le coût de retour au dépôt
                    route.cost += dist.get((node, instance.depot), 0) - dist.get((prev_node, instance.depot), 0)
                    
                    added = True
                    break
            
            # Si nécessaire, créer une nouvelle route
            if not added:
                for c in [1, 2]:
                    if c not in path_classes.get((instance.depot, node), set()):
                        continue
                    
                    for l in instance.L.keys():
                        if (demand_w <= instance.L[l]["Qw"] and 
                            demand_v <= instance.L[l]["Qv"] and
                            instance.m.get((c, l), 0) > 0):
                            
                            # Créer une nouvelle route
                            route = Route(period, c, l)
                            distance_to_node = dist.get((instance.depot, node), 0)
                            route.add_node(node, demand_w, demand_v, distance_to_node)
                            
                            # Ajouter le coût de retour au dépôt
                            route.cost += dist.get((node, instance.depot), 0)
                            
                            repaired.routes.append(route)
                            added = True
                            break
                    
                    if added:
                        break
    
    # Réévaluer la solution réparée
    repaired.evaluate()
    solution = consolidate_routes(solution, instance)
    return repaired

def select_parents(population, tournament_size=3):
    """
    Sélectionne deux parents dans la population par tournoi.

    Args:
        population: Liste des solutions (individus) de la population
        tournament_size: Taille du tournoi pour la sélection (défaut: 3)

    Returns:
        tuple: Deux solutions parents sélectionnées
    """
    if len(population) < 2:
        raise ValueError("La population doit contenir au moins deux individus")

    if tournament_size < 1 or tournament_size > len(population):
        tournament_size = min(3, len(population))

    # Sélectionner le premier parent
    tournament1 = random.sample(population, tournament_size)
    parent1 = min(tournament1, key=lambda x: x.fitness)

    # Sélectionner le second parent
    tournament2 = random.sample(population, tournament_size)
    parent2 = min(tournament2, key=lambda x: x.fitness)

    return parent1, parent2
def initialize_population(instance, population_size, dist, paths, path_classes):
    """
    Initialise une population de solutions pour l'algorithme mémétique.
    
    Args:
        instance: Instance du problème
        population_size: Taille de la population souhaitée
        dist: Distances des plus courts chemins
        paths: Chemins les plus courts
        path_classes: Classes d'accès des plus courts chemins
    
    Returns:
        list: Liste de solutions initiales
    """
    population = []
    for _ in range(population_size):
        # Créer une solution initiale glouton avec un peu d'aléatoire
        solution = greedy_initial_solution(instance, dist, paths, path_classes)
        solution = mutate(solution, instance, dist, paths, path_classes, mutation_rate=0.5)
        solution = consolidate_routes(solution, instance)
        population.append(solution)
    
    # Trier la population initiale
    population.sort(key=lambda x: x.fitness)
    return population
def memetic_algorithm(instance, population_size=30, generations=50, crossover_rate=0.8, mutation_rate=0.3):
    """
    Algorithme mémétique pour résoudre le problème de tournées de véhicules avec navettes fixes.
    """
    # Construction des structures de données nécessaires
    adj_list = build_adjacency_list(instance)
    dist, paths, path_classes = calculate_shortest_paths(instance, adj_list)
    
    # Initialisation de la population
    population = initialize_population(instance, population_size, dist, paths, path_classes)
    
    for gen in range(generations):
        offspring = []
        while len(offspring) < population_size:
            # Sélection des parents
            parent1, parent2 = select_parents(population)
            
            if random.random() < crossover_rate:
                # Appliquer le croisement
                child = crossover(parent1, parent2, instance, dist, paths, path_classes)
                # Appliquer la mutation
                child = mutate(child, instance, dist, paths, path_classes, mutation_rate)
                offspring.append(child)
            else:
                # Ajouter les parents directement
                offspring.extend([parent1, parent2])
        
        # Mettre à jour la population
        population = offspring
        population.sort(key=lambda x: x.fitness)
    
    # Retourner la meilleure solution
    best_solution = copy.deepcopy(population[0])
    best_solution = consolidate_routes(best_solution, instance)
    return best_solution
def main():
    # Forcer l'encodage UTF-8 pour la sortie
    import sys
    sys.stdout.reconfigure(encoding='utf-8')

    # Créer l'instance du problème
    instance = Instance()
    
    print("Résolution du problème de tournées de véhicules avec algorithme mémétique")
    print(f"Graphe: {len(instance.V)} nœuds, {len(instance.E)//2} arêtes")
    print(f"Périodes: {instance.P}")
    print(f"Types de véhicules: {list(instance.L.keys())}")
    print(f"Navettes fixes: {len(instance.shuttles)}")
    
    # Exécuter l'algorithme mémétique
    start_time = time.time()
    best_solution = memetic_algorithm(instance, population_size=30, generations=50, crossover_rate=0.8, mutation_rate=0.3)
    end_time = time.time()
    execution_time = end_time - start_time
    
    # Afficher les résultats
    print(f"\nExécution terminée en {execution_time:.2f} secondes")
    print(f"Meilleure solution trouvée (coût: {best_solution.fitness:.2f}, faisable: {best_solution.feasible})")
    
    # Vérifier si tous les sites sont desservis avec la fréquence requise
    print("\nFréquences de visite par site:")
    for node, visits in best_solution.node_visits.items():
        status = "✓" if len(visits) >= instance.eta[node] else "✗"
        print(f"  {node}: {len(visits)}/{instance.eta[node]} visites {status}")
    
    # Exécuter l'algorithme mémétique
    start_time = time.time()
    best_solution = memetic_algorithm(instance, population_size=30, generations=50, crossover_rate=0.8, mutation_rate=0.3)
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    # Afficher les résultats
    print(f"\nExécution terminée en {execution_time:.2f} secondes")
    print(f"Meilleure solution trouvée (coût: {best_solution.fitness:.2f}, faisable: {best_solution.feasible})")
    
    # Si vous avez besoin de réparer la solution, assurez-vous d'utiliser les mêmes structures
    if not best_solution.feasible:
        print("\nTentative de réparation de la solution...")
        adj_list = build_adjacency_list(instance)
        dist, paths, path_classes = calculate_shortest_paths(instance, adj_list)
        repaired_solution = repair_solution(best_solution, instance, dist, paths, path_classes)
        
        if repaired_solution.feasible:
            print(f"Solution réparée avec succès! Nouveau coût: {repaired_solution.fitness:.2f}")
            best_solution = repaired_solution
        else:
            print(f"La réparation n'a pas abouti à une solution complètement réalisable.")
            print(f"Meilleur coût après réparation: {repaired_solution.fitness:.2f}")
    # Afficher les détails de la meilleure solution
    print("\nDétails de la meilleure solution:")
    print(f"Nombre total de routes: {len(best_solution.routes)}")
    print(f"Nombre total de navettes fixes: {len(best_solution.shuttles)}")
    
    # Répartition des véhicules par période
    vehicles_per_period = defaultdict(int)
    for route in best_solution.routes + best_solution.shuttles:
        vehicles_per_period[route.period] += 1
    
    print("\nUtilisation des véhicules par période:")
    for period in sorted(vehicles_per_period.keys()):
        print(f"  Période {period}: {vehicles_per_period[period]} véhicules")
    
    # Détails des routes
    print("\nRoutes standards:")
    for i, route in enumerate(best_solution.routes):
        if not route.is_shuttle:
            print(f"  Route {i+1}: Période {route.period}, Classe {route.vehicle_class}, Type {route.vehicle_type}")
            print(f"    Parcours: {' -> '.join([instance.depot] + route.nodes + [instance.depot])}")
            print(f"    Coût: {route.cost:.2f}")
            print(f"    Charge (poids/volume): {route.load_weight}/{route.load_volume}")
    
    # Détails des navettes
    print("\nNavettes fixes:")
    for i, shuttle in enumerate(best_solution.shuttles):
        print(f"  Navette {i+1}: Période {shuttle.period}, Classe {shuttle.vehicle_class}, Type {shuttle.vehicle_type}")
        print(f"    Trajet: {shuttle.shuttle_origin} -> {shuttle.shuttle_destination}")
        print(f"    Coût: {shuttle.cost:.2f}")
        print(f"    Charge (poids/volume): {shuttle.load_weight}/{shuttle.load_volume}")
    
    # Vérifier si tous les sites sont desservis avec la fréquence requise
    print("\nFréquences de visite par site:")
    for node, visits in best_solution.node_visits.items():
        status = "✓" if len(visits) >= instance.eta[node] else "✗"
        print(f"  {node}: {len(visits)}/{instance.eta[node]} visites {status}")
        print(f"    Périodes: {sorted(visits)}")

def analyze_solution_quality(solution, instance):
    """Analyser la qualité de la solution et suggérer des améliorations possibles"""
    print("\nAnalyse de la qualité de la solution:")
    
    # Analyser l'utilisation des véhicules
    vehicle_usage = defaultdict(lambda: defaultdict(int))
    max_vehicles = defaultdict(int)
    
    for route in solution.routes + solution.shuttles:
        vehicle_usage[(route.vehicle_class, route.vehicle_type)][route.period] += 1
        max_vehicles[(route.vehicle_class, route.vehicle_type)] = max(
            max_vehicles[(route.vehicle_class, route.vehicle_type)],
            vehicle_usage[(route.vehicle_class, route.vehicle_type)][route.period]
        )
    
    print("\nUtilisation maximale des véhicules:")
    for (c, l), count in sorted(max_vehicles.items()):
        available = instance.m.get((c, l), 0)
        utilization = count / available if available > 0 else float('inf')
        status = "OK" if count <= available else "Dépassement"
        print(f"  Classe {c}, Type {l}: {count}/{available} ({utilization:.2%}) {status}")
    
    # Analyser le taux de remplissage des véhicules
    total_weight_capacity = 0
    total_volume_capacity = 0
    total_weight_used = 0
    total_volume_used = 0
    
    for route in solution.routes + solution.shuttles:
        weight_capacity = instance.L[route.vehicle_type]["Qw"]
        volume_capacity = instance.L[route.vehicle_type]["Qv"]
        
        total_weight_capacity += weight_capacity
        total_volume_capacity += volume_capacity
        total_weight_used += route.load_weight
        total_volume_used += route.load_volume
    
    weight_utilization = total_weight_used / total_weight_capacity if total_weight_capacity > 0 else 0
    volume_utilization = total_volume_used / total_volume_capacity if total_volume_capacity > 0 else 0
    
    print(f"\nTaux d'utilisation global des véhicules:")
    print(f"  Poids: {total_weight_used}/{total_weight_capacity} ({weight_utilization:.2%})")
    print(f"  Volume: {total_volume_used}/{total_volume_capacity} ({volume_utilization:.2%})")
    
    # Identifier les véhicules sous-utilisés
    print("\nVéhicules sous-utilisés (< 50% de capacité):")
    under_utilized = 0
    for i, route in enumerate(solution.routes + solution.shuttles):
        weight_capacity = instance.L[route.vehicle_type]["Qw"]
        volume_capacity = instance.L[route.vehicle_type]["Qv"]
        
        weight_util = route.load_weight / weight_capacity
        volume_util = route.load_volume / volume_capacity
        
        if weight_util < 0.5 or volume_util < 0.5:
            route_type = "Navette" if hasattr(route, 'is_shuttle') and route.is_shuttle else "Route"
            print(f"  {route_type} {i+1}: Période {route.period}, Classe {route.vehicle_class}, Type {route.vehicle_type}")
            print(f"    Utilisation: Poids {weight_util:.2%}, Volume {volume_util:.2%}")
            under_utilized += 1
    
    if under_utilized == 0:
        print("  Aucun véhicule sous-utilisé.")
    
    # Suggestions d'amélioration
    print("\nSuggestions d'amélioration:")
    
    if weight_utilization < 0.7 or volume_utilization < 0.7:
        print("  - Considérer la consolidation des routes pour réduire le nombre de véhicules")
    
    if under_utilized > len(solution.routes + solution.shuttles) * 0.2:
        print("  - Envisager d'utiliser des véhicules plus petits pour certaines routes")
    
    # Vérifier s'il y a des périodes surchargées
    period_load = defaultdict(int)
    for route in solution.routes + solution.shuttles:
        period_load[route.period] += 1
    
    max_load = max(period_load.values()) if period_load else 0
    min_load = min(period_load.values()) if period_load else 0
    
    if max_load > min_load * 1.5:
        print("  - La charge de travail est déséquilibrée entre les périodes")
        print("  - Essayer de redistribuer les visites pour équilibrer la charge")
    
    # Vérifier si des sites sont visités plus que nécessaire
    for node, visits in solution.node_visits.items():
        if len(visits) > instance.eta[node] * 1.5:
            print(f"  - Le site {node} est visité plus fréquemment que nécessaire")
            print(f"    ({len(visits)} visites pour un minimum requis de {instance.eta[node]})")

def export_solution(solution, instance, filename="solution.txt"):
    """Exporter la solution dans un fichier texte"""
    with open(filename, "w") as f:
        f.write(f"Solution pour le problème de tournées de véhicules avec navettes\n")
        f.write(f"Coût total: {solution.fitness:.2f}\n")
        f.write(f"Solution réalisable: {solution.feasible}\n\n")
        
        f.write(f"Nombre de routes: {len(solution.routes)}\n")
        f.write(f"Nombre de navettes fixes: {len(solution.shuttles)}\n\n")
        
        f.write("Routes standards:\n")
        for i, route in enumerate(solution.routes):
            if not route.is_shuttle:
                f.write(f"  Route {i+1}: Période {route.period}, Classe {route.vehicle_class}, Type {route.vehicle_type}\n")
                f.write(f"    Parcours: {' -> '.join([instance.depot] + route.nodes + [instance.depot])}\n")
                f.write(f"    Coût: {route.cost:.2f}\n")
                f.write(f"    Charge (poids/volume): {route.load_weight}/{route.load_volume}\n")
                
                # Détails des livraisons
                f.write("    Livraisons:\n")
                for node, (w, v) in route.deliveries.items():
                    f.write(f"      {node}: {w} unités de poids, {v} unités de volume\n")
                f.write("\n")
        
        f.write("Navettes fixes:\n")
        for i, shuttle in enumerate(solution.shuttles):
            f.write(f"  Navette {i+1}: Période {shuttle.period}, Classe {shuttle.vehicle_class}, Type {shuttle.vehicle_type}\n")
            f.write(f"    Trajet: {shuttle.shuttle_origin} -> {shuttle.shuttle_destination}\n")
            f.write(f"    Coût: {shuttle.cost:.2f}\n")
            f.write(f"    Charge (poids/volume): {shuttle.load_weight}/{shuttle.load_volume}\n")
            
            # Détails des livraisons
            f.write("    Livraisons:\n")
            for node, (w, v) in shuttle.deliveries.items():
                f.write(f"      {node}: {w} unités de poids, {v} unités de volume\n")
            f.write("\n")
        
        f.write("Fréquences de visite par site:\n")
        for node, visits in solution.node_visits.items():
            status = "OK" if len(visits) >= instance.eta[node] else "Insuffisant"
            f.write(f"  {node}: {len(visits)}/{instance.eta[node]} visites ({status})\n")
            f.write(f"    Périodes: {sorted(visits)}\n")
        
        f.write("\nRécapitulatif d'utilisation des véhicules par période:\n")
        vehicles_per_period = defaultdict(int)
        for route in solution.routes + solution.shuttles:
            vehicles_per_period[route.period] += 1
        
        for period in sorted(vehicles_per_period.keys()):
            f.write(f"  Période {period}: {vehicles_per_period[period]} véhicules\n")
    
    print(f"Solution exportée dans le fichier '{filename}'")

def visualize_routes_per_period(solution, instance, output_file="routes_visualization.txt"):
    """Créer une visualisation ASCII des routes pour chaque période"""
    with open(output_file, "w") as f:
        f.write("Visualisation des routes par période\n\n")
        
        for period in instance.P:
            f.write(f"=== Période {period} ===\n\n")
            
            # Collecter les routes et navettes pour cette période
            period_routes = [r for r in solution.routes if r.period == period and not r.is_shuttle]
            period_shuttles = [s for s in solution.shuttles if s.period == period]
            period_shuttles.extend([r for r in solution.routes if r.period == period and r.is_shuttle])
            
            if not period_routes and not period_shuttles:
                f.write("  Aucune route dans cette période\n\n")
                continue
            
            # Visualiser les routes standard
            if period_routes:
                f.write("Routes standard:\n")
                for i, route in enumerate(period_routes):
                    nodes = [instance.depot] + route.nodes + [instance.depot]
                    route_str = ""
                    
                    for j in range(len(nodes) - 1):
                        u, v = nodes[j], nodes[j+1]
                        route_str += f"{u} --({route.vehicle_class},{route.vehicle_type})--> {v}\n"
                        if j < len(nodes) - 2:
                            route_str += "  |\n  v\n"
                    
                    f.write(f"  Route {i+1}: (Classe {route.vehicle_class}, Type {route.vehicle_type})\n")
                    f.write(f"{route_str}\n")
            
            # Visualiser les navettes
            if period_shuttles:
                f.write("Navettes:\n")
                for i, shuttle in enumerate(period_shuttles):
                    f.write(f"  Navette {i+1}: (Classe {shuttle.vehicle_class}, Type {shuttle.vehicle_type})\n")
                    f.write(f"  {instance.depot} --> {shuttle.shuttle_origin} --> {shuttle.shuttle_destination} --> {instance.depot}\n\n")
            
            f.write("\n")
    
    print(f"Visualisation des routes exportée dans le fichier '{output_file}'")

def create_experiment_log(solution, instance, execution_time, params, filename="experiment_log.txt"):
    """Créer un fichier de log pour l'expérience"""
    with open(filename, "w") as f:
        f.write("=== Expérience d'optimisation de tournées de véhicules ===\n\n")
        
        # Paramètres du problème
        f.write("Paramètres du problème:\n")
        f.write(f"  Nombre de sites: {len(instance.V)}\n")
        f.write(f"  Nombre de périodes: {instance.np}\n")
        f.write(f"  Nombre de types de véhicules: {len(instance.L)}\n")
        f.write(f"  Nombre de classes d'accès: 2\n\n")
        
        # Paramètres de l'algorithme
        f.write("Paramètres de l'algorithme:\n")
        f.write(f"  Taille de la population: {params['population_size']}\n")
        f.write(f"  Nombre de générations: {params['generations']}\n")
        f.write(f"  Taux de croisement: {params['crossover_rate']}\n")
        f.write(f"  Taux de mutation: {params['mutation_rate']}\n\n")
        
        # Résultats
        f.write("Résultats:\n")
        f.write(f"  Temps d'exécution: {execution_time:.2f} secondes\n")
        f.write(f"  Coût de la solution: {solution.fitness:.2f}\n")
        f.write(f"  Solution réalisable: {solution.feasible}\n")
        f.write(f"  Nombre total de routes: {len(solution.routes)}\n")
        f.write(f"  Nombre total de navettes: {len(solution.shuttles)}\n\n")
        
        # Statistiques sur les véhicules utilisés
        vehicle_usage = defaultdict(int)
        for route in solution.routes + solution.shuttles:
            vehicle_usage[(route.vehicle_class, route.vehicle_type)] += 1
        
        f.write("Utilisation des véhicules:\n")
        for (c, l), count in sorted(vehicle_usage.items()):
            f.write(f"  Classe {c}, Type {l}: {count} véhicules utilisés\n")
        
        # Fréquences de visite
        f.write("\nFréquences de visite:\n")
        for node, visits in solution.node_visits.items():
            f.write(f"  {node}: {len(visits)}/{instance.eta[node]} visites\n")
    
    print(f"Log d'expérience créé dans le fichier '{filename}'")

if __name__ == "__main__":
    # Exécuter le programme principal
    main()
    
    # Définir les paramètres de l'algorithme
    algorithm_params = {
        "population_size": 30,
        "generations": 50,
        "crossover_rate": 0.8,
        "mutation_rate": 0.3
    }
    
    # Analyser la solution obtenue
    instance = Instance()
    start_time = time.time()
    best_solution = memetic_algorithm(instance, **algorithm_params)
    end_time = time.time()
    execution_time = end_time - start_time
    
    # Analyser la qualité de la solution
    analyze_solution_quality(best_solution, instance)
    
    # Exporter la solution
    export_solution(best_solution, instance)
    
    # Visualiser les routes
    visualize_routes_per_period(best_solution, instance)
    
    # Créer un log d'expérience
    create_experiment_log(best_solution, instance, execution_time, algorithm_params)