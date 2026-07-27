from django.contrib.gis.db import models  # IMPORTANT : Module GIS pour PostGIS
from django.contrib.auth.models import User  # Modèle d'utilisateur Django
from django.utils import timezone

# ==========================================
# 1. MODÈLE COMMUNE
# ==========================================
class Commune(models.Model):
    nom = models.CharField(max_length=100)
    code_insee = models.CharField(max_length=20, blank=True, null=True) # Utile pour l'administration
    population = models.IntegerField(blank=True, null=True)
    superficie = models.FloatField(blank=True, null=True)
    geom = models.PolygonField(srid=4326)  # Stocke les frontières de la commune (Zone/Polygone)
    
    # Champs pour point central (latitude/longitude)
    latitude = models.FloatField(blank=True, null=True, verbose_name="Latitude du centre")
    longitude = models.FloatField(blank=True, null=True, verbose_name="Longitude du centre")

    def __str__(self):
        return self.nom

# ==========================================
# 2. MODÈLE SECTEUR
# ==========================================
class Secteur(models.Model):
    nom = models.CharField(max_length=100)
    superficie = models.FloatField(blank=True, null=True)
    geom = models.PolygonField(srid=4326)  # Stocke les limites du quartier/secteur (Zone/Polygone)
    commune = models.ForeignKey(Commune, on_delete=models.CASCADE, related_name='secteurs')
    
    # Champs pour point central (latitude/longitude)
    latitude = models.FloatField(blank=True, null=True, verbose_name="Latitude du centre")
    longitude = models.FloatField(blank=True, null=True, verbose_name="Longitude du centre")

    def __str__(self):
        return f"{self.nom} - {self.commune.nom}"

# ==========================================
# 3. MODÈLE TYPE D'ÉQUIPEMENT
# ==========================================
class TypeEquipement(models.Model):
    libelle = models.CharField(max_length=100)  # Exemple : Écoles, Forages, Marchés...
    icone = models.CharField(max_length=50, blank=True, null=True)  # Nom du marqueur pour Leaflet

    def __str__(self):
        return self.libelle

# ==========================================
# 4. MODÈLE ÉTAT PHYSIQUE
# ==========================================
class EtatPhysique(models.Model):
    libelle = models.CharField(max_length=100)  # Exemple : Neuf, Bon état, Dégradé...

    def __str__(self):
        return self.libelle

# ==========================================
# 5. MODÈLE STATUT DE FONCTIONNEMENT
# ==========================================
class StatutFonctionnement(models.Model):
    libelle = models.CharField(max_length=100)  # Exemple : Opérationnel, En panne, En maintenance

    def __str__(self):
        return self.libelle

# ==========================================
# 6. MODÈLE CENTRAL : ÉQUIPEMENT
# ==========================================
class Equipement(models.Model):
    nom = models.CharField(max_length=150)
    code_identification = models.CharField(max_length=50, unique=True)  # Exemple : FOR-001
    annee_realisation = models.IntegerField(blank=True, null=True)
    accessibilite = models.CharField(max_length=100, blank=True, null=True)  # Exemple : Libre, Payant
    
    # La localisation géospatiale précise (POINT X/Y)
    localisation = models.PointField(srid=4326) 

    # Les Clés Étrangères (Relations vers les autres tables)
    secteur = models.ForeignKey(Secteur, on_delete=models.PROTECT, related_name='equipements')
    type_equipement = models.ForeignKey(TypeEquipement, on_delete=models.PROTECT, related_name='equipements')
    etat = models.ForeignKey(EtatPhysique, on_delete=models.PROTECT, related_name='equipements')
    statut = models.ForeignKey(StatutFonctionnement, on_delete=models.PROTECT, related_name='equipements')

    # Nouveaux champs de sécurité
    cree_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Agent créateur")
    date_creation = models.DateTimeField(default=timezone.now, verbose_name="Date de création")

    def __str__(self):
        return f"{self.nom} ({self.code_identification})"

    def get_details_dict(self):
        """
        Méthode d'aide pour renvoyer dynamiquement les attributs de la sous-table 
        métier active sous forme de dictionnaire (Utilisé pour l'API GeoJSON et les Popups).
        """
        relations_metiers = [
            'details_ecole', 'details_sante', 'details_forage', 'details_marche',
            'details_administration', 'details_assainissement', 'details_sport', 'details_eclairage'
        ]
        
        for rel in relations_metiers:
            if hasattr(self, rel):
                try:
                    obj_metier = getattr(self, rel)
                    if obj_metier:
                        fields = obj_metier._meta.get_fields()
                        return {
                            f.verbose_name: getattr(obj_metier, f.name)
                            for f in fields if f.name not in ['id', 'equipement'] and getattr(obj_metier, f.name) is not None
                        }
                except models.ObjectDoesNotExist:
                    continue
        return {}


# =====================================================================
# 7. LES 8 TABLES MÉTIERS DÉDIÉES (STRUCTURE NORMALISÉE - OPTION B)
# =====================================================================

# 1. ÉCOLES
class DetailsEcole(models.Model):
    equipement = models.OneToOneField(Equipement, on_delete=models.CASCADE, related_name='details_ecole', verbose_name="Infrastructure")
    nombre_classes = models.IntegerField(blank=True, null=True, verbose_name="Nombre de classes")
    nombre_eleves = models.IntegerField(blank=True, null=True, verbose_name="Nombre d'élèves")
    nombre_enseignants = models.IntegerField(blank=True, null=True, verbose_name="Nombre d'enseignants")
    cycle_enseignement = models.CharField(max_length=50, blank=True, null=True, verbose_name="Cycle d'enseignement")
    presence_cantine = models.BooleanField(default=False, verbose_name="Présence d'une cantine")
    nom_directeur = models.CharField(max_length=100, blank=True, null=True, verbose_name="Nom du Directeur")

    class Meta:
        verbose_name = "Détails École"
        verbose_name_plural = "Détails Écoles"

    def __str__(self):
        return f"Éducation - {self.equipement.nom}"

# 2. CENTRES DE SANTÉ
class DetailsSante(models.Model):
    equipement = models.OneToOneField(Equipement, on_delete=models.CASCADE, related_name='details_sante', verbose_name="Infrastructure")
    type_centre = models.CharField(max_length=100, blank=True, null=True, verbose_name="Type de centre de santé")
    capacite_lits = models.IntegerField(blank=True, null=True, verbose_name="Capacité en lits")
    presence_maternite = models.BooleanField(default=False, verbose_name="Présence d'une maternité")
    ambulance_fonctionnelle = models.BooleanField(default=False, verbose_name="Ambulance fonctionnelle")
    personnel_medical_count = models.IntegerField(blank=True, null=True, verbose_name="Nombre de personnels soignants")

    class Meta:
        verbose_name = "Détails Centre de Santé"
        verbose_name_plural = "Détails Centres de Santé"

    def __str__(self):
        return f"Santé - {self.equipement.nom}"

# 3. FORAGES ET POINTS D'EAU
class DetailsForage(models.Model):
    equipement = models.OneToOneField(Equipement, on_delete=models.CASCADE, related_name='details_forage', verbose_name="Infrastructure")
    type_pompe = models.CharField(max_length=100, blank=True, null=True, verbose_name="Type de pompe")
    profondeur = models.FloatField(blank=True, null=True, verbose_name="Profondeur (m)")
    debit = models.FloatField(blank=True, null=True, verbose_name="Débit (m³/h)")
    population_desservie = models.IntegerField(blank=True, null=True, verbose_name="Population desservie")
    mode_gestion = models.CharField(max_length=100, blank=True, null=True, verbose_name="Mode de gestion")

    class Meta:
        verbose_name = "Détails Point d'Eau / Forage"
        verbose_name_plural = "Détails Points d'Eau / Forages"

    def __str__(self):
        return f"Hydraulique - {self.equipement.nom}"

# 4. MARCHÉS
class DetailsMarche(models.Model):
    equipement = models.OneToOneField(Equipement, on_delete=models.CASCADE, related_name='details_marche', verbose_name="Infrastructure")
    nombre_boutiques = models.IntegerField(blank=True, null=True, verbose_name="Nombre de boutiques/hangars")
    superficie = models.FloatField(blank=True, null=True, verbose_name="Superficie (m²)")
    frequence_marche = models.CharField(max_length=50, blank=True, null=True, verbose_name="Fréquence du marché")
    cloture = models.BooleanField(default=False, verbose_name="Marché clôturé")

    class Meta:
        verbose_name = "Détails Marché"
        verbose_name_plural = "Détails Marchés"

    def __str__(self):
        return f"Commerce - {self.equipement.nom}"

# 5. BÂTIMENTS ADMINISTRATIFS
class DetailsAdministration(models.Model):
    equipement = models.OneToOneField(Equipement, on_delete=models.CASCADE, related_name='details_administration', verbose_name="Infrastructure")
    type_administration = models.CharField(max_length=100, blank=True, null=True, verbose_name="Type d'administration")
    nombre_bureaux = models.IntegerField(blank=True, null=True, verbose_name="Nombre de bureaux")
    salle_reunion = models.BooleanField(default=False, verbose_name="Présence d'une salle de réunion")
    accessible_public = models.BooleanField(default=True, verbose_name="Accessible au public (PMR)")

    class Meta:
        verbose_name = "Détails Bâtiment Administratif"
        verbose_name_plural = "Détails Bâtiments Administratifs"

    def __str__(self):
        return f"Administration - {self.equipement.nom}"

# 6. OUVRAGES D’ASSAINISSEMENT
class DetailsAssainissement(models.Model):
    equipement = models.OneToOneField(Equipement, on_delete=models.CASCADE, related_name='details_assainissement', verbose_name="Infrastructure")
    type_ouvrage = models.CharField(max_length=100, blank=True, null=True, verbose_name="Type d'ouvrage d'assainissement")
    longueur_reseau = models.FloatField(blank=True, null=True, verbose_name="Longueur du réseau (m)")
    dimension_capacite = models.FloatField(blank=True, null=True, verbose_name="Dimension / Capacité (m³)")
    nature_reseau = models.CharField(max_length=100, blank=True, null=True, verbose_name="Nature de l'ouvrage")

    class Meta:
        verbose_name = "Détails Ouvrage d'Assainissement"
        verbose_name_plural = "Détails Ouvrages d'Assainissement"

    def __str__(self):
        return f"Assainissement - {self.equipement.nom}"

# 7. ÉQUIPEMENTS SPORTIFS
class DetailsSport(models.Model):
    equipement = models.OneToOneField(Equipement, on_delete=models.CASCADE, related_name='details_sport', verbose_name="Infrastructure")
    nature_sport = models.CharField(max_length=100, blank=True, null=True, verbose_name="Nature de l'infrastructure sportive")
    nature_revetement = models.CharField(max_length=100, blank=True, null=True, verbose_name="Nature du revêtement")
    presence_eclairage = models.BooleanField(default=False, verbose_name="Présence d'un éclairage nocturne")
    capacite_places = models.IntegerField(blank=True, null=True, verbose_name="Capacité de places (Gradins)")

    class Meta:
        verbose_name = "Détails Infrastructure Sportive"
        verbose_name_plural = "Détails Infrastructures Sportives"

    def __str__(self):
        return f"Sport - {self.equipement.nom}"

# 8. ÉCLAIRAGE PUBLIC
class DetailsEclairage(models.Model):
    equipement = models.OneToOneField(Equipement, on_delete=models.CASCADE, related_name='details_eclairage', verbose_name="Infrastructure")
    type_technologie = models.CharField(max_length=100, blank=True, null=True, verbose_name="Type de technologie (Solaire/LED)")
    nombre_foyers = models.IntegerField(blank=True, null=True, verbose_name="Nombre de foyers/lampes")
    puissance_lampe = models.IntegerField(blank=True, null=True, verbose_name="Puissance de la lampe (Watts)")
    hauteur_poteau = models.FloatField(blank=True, null=True, verbose_name="Hauteur du poteau (m)")

    class Meta:
        verbose_name = "Détails Éclairage Public"
        verbose_name_plural = "Détails Éclairages Publics"

    def __str__(self):
        return f"Éclairage - {self.equipement.nom}"


# ==========================================
# 8. JOURNAUX ET AUDIT
# ==========================================
class JournalActivite(models.Model):
    utilisateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Agent / Admin")
    action = models.CharField(verbose_name="Action", max_length=50)
    details = models.TextField(verbose_name="Détails de l'action")
    date_action = models.DateTimeField(auto_now_add=True, verbose_name="Date et Heure")

    class Meta:
        verbose_name = "Journal d'activité"
        verbose_name_plural = "Journal des activités"
        ordering = ['-date_action']

    def __str__(self):
        nom_user = self.utilisateur.username if self.utilisateur else "Système/Inconnu"
        return f"{nom_user} - {self.action} - {self.date_action.strftime('%d/%m/%Y %H:%M')}"
    
class JournalAudit(models.Model):
    ACTIONS_CHOICES = [
        ('AJOUT', 'Ajout / Création'),
        ('MODIFICATION', 'Modification'),
        ('SUPPRESSION', 'Suppression définitive'),
    ]
    
    MODULE_CHOICES = [
        ('EQUIPEMENT', 'Infrastructure / Équipement'),
        ('COMMUNE', 'Territoire communal'),
        ('SECTEUR', 'Secteur / Quartier'),
        ('CONFIGURATION', 'Nomenclatures (Types/États/Statuts)'),
    ]

    utilisateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Opérateur")
    action_type = models.CharField(max_length=20, choices=ACTIONS_CHOICES, verbose_name="Type d'action")
    module = models.CharField(max_length=25, choices=MODULE_CHOICES, verbose_name="Module impacté")
    description = models.TextField(verbose_name="Détails de l'opération")
    date_action = models.DateTimeField(default=timezone.now, verbose_name="Horodatage")
    adresse_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name="Adresse IP")

    class Meta:
        verbose_name = "Journal d'Audit"
        verbose_name_plural = "Journaux d'Audit"
        ordering = ['-date_action']

    def __str__(self):
        user_str = self.utilisateur.username if self.utilisateur else "Système/Inconnu"
        return f"[{self.date_action.strftime('%d/%m/%Y %H:%M')}] {user_str} - {self.action_type} ({self.module})"