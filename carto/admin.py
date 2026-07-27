from django.contrib.gis import admin  # IMPORTANT : On utilise l'admin GIS pour avoir les cartes
from .models import Commune, Secteur, TypeEquipement, EtatPhysique, StatutFonctionnement, Equipement

# Configuration de la carte par défaut pour l'administration
class CustomGeoAdmin(admin.GISModelAdmin):
    # Utilise OpenStreetMap en fond de carte à la place du fond de carte par défaut un peu sombre
    gis_widget_kwargs = {
        'attrs': {
            'default_zoom': 12,
            'default_lon': -1.52,  # Positionnement par défaut (Modifiable selon votre commune)
            'default_lat': 12.36,  
        }
    }

# Enregistrement des modèles simples (Nomenclatures)
admin.site.register(TypeEquipement)
admin.site.register(EtatPhysique)
admin.site.register(StatutFonctionnement)

# Enregistrement des modèles géographiques avec la carte interactive
@admin.register(Commune)
class CommuneAdmin(CustomGeoAdmin):
    list_display = ('nom', 'code_insee', 'population', 'superficie')
    search_fields = ('nom', 'code_insee')

@admin.register(Secteur)
class SecteurAdmin(CustomGeoAdmin):
    list_display = ('nom', 'commune', 'superficie')
    list_filter = ('commune',)
    search_fields = ('nom',)

@admin.register(Equipement)
class EquipementAdmin(CustomGeoAdmin):
    list_display = ('nom', 'code_identification', 'type_equipement', 'secteur', 'etat', 'statut')
    list_filter = ('type_equipement', 'etat', 'statut', 'secteur__commune')
    search_fields = ('nom', 'code_identification')