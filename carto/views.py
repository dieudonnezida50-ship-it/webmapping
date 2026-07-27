import json
import csv
from io import StringIO, TextIOWrapper
from django.contrib.auth.models import Group, User
from django.contrib.gis.geos import GEOSGeometry, Point, Polygon
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.http import JsonResponse
from django.core.serializers import serialize
from django.contrib import messages
from django import forms

from .models import (
    JournalAudit, Equipement, Commune, Secteur, StatutFonctionnement, TypeEquipement,
    EtatPhysique, DetailsEcole, DetailsSante, DetailsForage, DetailsMarche,
    DetailsAdministration, DetailsAssainissement, DetailsSport, DetailsEclairage
)

from .forms import (
    EquipementForm, CommuneForm, SecteurForm, EtatPhysiqueForm, StatutFonctionnementForm,
    DetailsEcoleForm, DetailsSanteForm, DetailsForageForm, DetailsMarcheForm,
    DetailsAdministrationForm, DetailsAssainissementForm, DetailsSportForm, DetailsEclairageForm,
    UtilisateurCreationForm, UtilisateurModificationForm
)

from django.forms.models import model_to_dict

# Assure-toi que les autres imports comme User, redirect, render, get_object_or_400 sont présents
def obtenir_ip_client(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

# ==========================================
# FONCTION UTILITAIRE : TRAITER LES IMPORTS DE FICHIERS
# ==========================================
def traiter_import_fichier(fichier_obj):
    """
    Traite un fichier CSV ou GeoJSON pour extraire les données géographiques.
    
    Retourne un dictionnaire avec :
    - 'geometrie' : GEOSGeometry object (Polygon)
    - 'latitude' : float (centre du centroïde)
    - 'longitude' : float (centre du centroïde)
    """
    if not fichier_obj:
        return None
    
    try:
        # Lire le contenu du fichier
        if isinstance(fichier_obj, str):
            contenu = fichier_obj
        else:
            contenu = fichier_obj.read().decode('utf-8')
        
        # Essayer d'abord comme GeoJSON
        if contenu.strip().startswith('{'):
            try:
                data = json.loads(contenu)
                
                # Extraire la géométrie du GeoJSON
                if 'geometry' in data:
                    geometry_data = data['geometry']
                elif 'features' in data and len(data['features']) > 0:
                    geometry_data = data['features'][0]['geometry']
                else:
                    geometry_data = data
                
                geom_geojson = json.dumps(geometry_data)
                geometrie = GEOSGeometry(geom_geojson, srid=4326)
                
                # Calculer le centre (centroïde)
                centroid = geometrie.centroid
                return {
                    'geometrie': geometrie,
                    'latitude': centroid.y,
                    'longitude': centroid.x
                }
            except Exception as e:
                raise ValueError(f"Erreur lors du traitement GeoJSON : {e}")
        
        # Sinon, traiter comme CSV
        else:
            f = StringIO(contenu)
            reader = csv.DictReader(f)
            rows = list(reader)
            
            if not rows:
                raise ValueError("Le fichier CSV est vide")
            
            # Chercher les colonnes latitude/longitude
            first_row = rows[0]
            lat_col = None
            lon_col = None
            
            # Essayer différents noms de colonnes
            for col in first_row.keys():
                col_lower = col.lower().strip()
                if col_lower in ['latitude', 'lat', 'y']:
                    lat_col = col
                elif col_lower in ['longitude', 'lon', 'x']:
                    lon_col = col
            
            if not lat_col or not lon_col:
                raise ValueError("Le CSV doit contenir des colonnes 'latitude' et 'longitude'")
            
            # Extraire les données
            lat = float(first_row[lat_col].strip())
            lon = float(first_row[lon_col].strip())
            
            # Créer un point
            point = Point(lon, lat, srid=4326)
            
            return {
                'geometrie': None,  # CSV fournit juste un point, pas un polygone
                'latitude': lat,
                'longitude': lon,
                'point': point
            }
    
    except Exception as e:
        return {'erreur': str(e)}

# ==========================================
# 1. SERVICES CARTOGRAPHIQUES ET API (PUBLIC)
# ==========================================

# Point d'entrée de l'application cartographique (visualisation principale)
def carte_index(request):
    """Vue pour afficher la page HTML principale de votre carte SIG"""
    return render(request, 'carto/index.html')

# Sérialisation GeoJSON : Extraction des infrastructures (Points géospatiaux)
def equipements_geojson(request):
    equipements = Equipement.objects.select_related('type_equipement', 'etat', 'statut', 'secteur__commune').all()
    
    features = []
    for eq in equipements:
        if eq.localisation:
            libelle_etat = eq.etat.libelle if eq.etat else "N/A"
            libelle_statut = eq.statut.libelle if eq.statut else "N/A"
            
            if "neuf" in libelle_etat.lower():
                etat_css = "badge bg-success-subtle text-success border border-success-subtle"
                etat_color = "#2ec4b6"
            elif "bon" in libelle_etat.lower():
                etat_css = "badge bg-info-subtle text-info border border-info-subtle"
                etat_color = "#00b4d8"
            else:
                etat_css = "badge bg-warning-subtle text-warning border border-warning-subtle"
                etat_color = "#e67e22"

            if "opérationnel" in libelle_statut.lower():
                statut_css = "badge bg-success text-white"
            elif "maintenance" in libelle_statut.lower():
                statut_css = "badge bg-warning text-dark"
            else:
                statut_css = "badge bg-danger text-white"

            props = {
                "nom": eq.nom,
                "code_identification": eq.code_identification,
                "type_equipement": eq.type_equipement.libelle if eq.type_equipement else "N/A",
                "icone": eq.type_equipement.icone if (eq.type_equipement and eq.type_equipement.icone) else "fa-location-dot",
                "etat": libelle_etat,
                "statut": libelle_statut,
                "etat_css_class": etat_css,
                "statut_css_class": statut_css,
                "marker_color": etat_color,
                "secteur": eq.secteur.nom if eq.secteur else "Non spécifié",
                "commune": eq.secteur.commune.nom if (eq.secteur and eq.secteur.commune) else "Non spécifiée",
                "annee_realisation": eq.annee_realisation if eq.annee_realisation else "Non renseignée"
            }

            # Rattacher les détails métiers (s'il en existe) pour enrichir le popup
            for rel in ['details_ecole','details_sante','details_forage','details_marche','details_administration','details_assainissement','details_sport','details_eclairage']:
                if hasattr(eq, rel):
                    deta = getattr(eq, rel)
                    if deta:
                        try:
                            props['details'] = model_to_dict(deta, exclude=['id', 'equipement'])
                        except Exception:
                            props['details'] = {}
                    break

            features.append({
                "type": "Feature",
                "geometry": json.loads(eq.localisation.geojson),
                "properties": props
            })
    
    geojson_data = {
        "type": "FeatureCollection",
        "features": features
    }
    return JsonResponse(geojson_data, safe=False)

# Sérialisation GeoJSON : Extraction des limites de secteurs (Polygones géospatiaux)
def secteurs_geojson(request):
    secteurs = Secteur.objects.all()
    features = []
    for sec in secteurs:
        if sec.geom:
            features.append({
                "type": "Feature",
                "geometry": json.loads(sec.geom.geojson),
                "properties": {
                    "nom": sec.nom,
                    "superficie": sec.superficie if sec.superficie else 0,
                    "commune": sec.commune.nom
                }
            })
        
    geojson_data = {
        "type": "FeatureCollection",
        "features": features
    }
    return JsonResponse(geojson_data, safe=False)

# Sérialisation GeoJSON : Extraction des limites de la commune (MultiPolygone)
def commune_geojson(request):
    communes = Commune.objects.all()
    features = []
    for com in communes:
        if com.geom:
            features.append({
                "type": "Feature",
                "geometry": json.loads(com.geom.geojson),
                "properties": {
                    "nom": com.nom,
                    "population": com.population or "N/A",
                    "superficie": com.superficie or "N/A"
                }
            })
    geojson_data = {
        "type": "FeatureCollection",
        "features": features
    }
    return JsonResponse(geojson_data, safe=False)


# ==========================================
# 2. ESPACE ADMINISTRATEUR ET TABLEAU DE BORD
# ==========================================

@login_required(login_url='connexion')
def dashboard_admin(request):
    """Tableau de bord de gestion : Statistiques décisionnelles et flux d'activité"""
    # On laisse passer le Superadmin OU l'Agent. Si ce n'est aucun des deux, on l'expulse.
    if not (request.user.is_superuser or request.user.groups.filter(name__iexact="Agent").exists()):
        return redirect('carte_index') # Sécurité : un agent simple ne va pas sur le dashboard admin

    total_equipements = Equipement.objects.count()
    operationnels = Equipement.objects.filter(statut__libelle="Opérationnel").count()
    en_maintenance = Equipement.objects.filter(statut__libelle="En maintenance").count()
    en_panne = Equipement.objects.filter(statut__libelle="En panne").count()
    
    etat_neuf = Equipement.objects.filter(etat__libelle__icontains="Neuf").count()
    etat_bon = Equipement.objects.filter(etat__libelle__icontains="Bon").count()
    etat_degrade = Equipement.objects.filter(etat__libelle__icontains="Dégradé").count()
    
    derniers_equipements = Equipement.objects.select_related(
        'type_equipement', 
        'secteur', 
        'statut'
    ).order_by('-id')[:6]
    
    # --- ÉTAPE 3 : RÉCUPÉRATION DES LOGS DU JOURNAL D'AUDIT ---
    # On récupère les 10 actions les plus récentes avec les données de l'utilisateur lié
    logs_audit = JournalAudit.objects.select_related('utilisateur').order_by('-date_action')[:10]
    
    context = {
        'total': total_equipements,
        'operationnels': operationnels,
        'en_maintenance': en_maintenance,
        'en_panne': en_panne,
        'equipements': derniers_equipements,
        'etat_neuf': etat_neuf,
        'etat_bon': etat_bon,
        'etat_degrade': etat_degrade,
        'is_agent': request.user.groups.filter(name__iexact="Agent").exists(),
        'logs_audit': logs_audit, # <-- ON ENVOIE LES LOGS AU TEMPLATE HTML
    }
    return render(request, 'admin/admin_dashboard.html', context)

@login_required(login_url='connexion')
def liste_equipements_view(request):
    """Console d'administration globale et filtrage des infrastructures"""
    equipements = Equipement.objects.all().select_related('type_equipement', 'secteur__commune', 'statut').order_by('-id')
    tous_les_statuts = StatutFonctionnement.objects.all()
    tous_les_types = TypeEquipement.objects.all()

    context = {
        'equipements': equipements,
        'tous_les_statuts': tous_les_statuts,
        'tous_les_types': tous_les_types,
        'total': equipements.count(),
    }
    return render(request, 'admin/liste_equipements.html', context)


# ==========================================
# 3. GESTION DES TERRITOIRES (COMMUNES CRUD)
# ==========================================

@login_required(login_url='connexion')
def liste_communes(request):
    """Registre global des communes enregistrées dans le SIG"""
    communes = Commune.objects.all().order_by('nom')
    return render(request, 'admin/liste_communes.html', {
        'communes': communes,
        'total': communes.count()
    })


def api_toutes_communes_geojson(request):
    """Renvoie l'ensemble des communes enregistrées au format GeoJSON"""
    communes = Commune.objects.all()
    geojson_data = serialize('geojson', communes, geometry_field='geom', fields=('nom', 'code_insee'))
    return JsonResponse(json.loads(geojson_data), safe=False)


@login_required(login_url='connexion')
def gestion_commune(request, pk=None):
    """Contrôleur hybride CRUD : Assure l'Ajout ou la Modification automatique d'une commune."""
    if pk:
        commune = get_object_or_404(Commune, pk=pk)
        title = f"Modifier la commune : {commune.nom}"
        geom_wkt = commune.geom.wkt if commune.geom else ""
    else:
        commune = None
        title = "Ajouter une nouvelle Commune"
        geom_wkt = ""

    if request.method == 'POST':
        form = CommuneForm(request.POST, request.FILES, instance=commune)
        if form.is_valid():
            try:
                commune_obj = form.save(commit=False)
                
                # Récupérer la latitude et longitude du formulaire
                lat = form.cleaned_data.get('latitude')
                lon = form.cleaned_data.get('longitude')
                
                # Récupérer le fichier d'import s'il existe
                fichier_import = request.FILES.get('fichier_import')
                
                # Traiter l'import de fichier en priorité
                if fichier_import:
                    resultat_import = traiter_import_fichier(fichier_import)
                    if 'erreur' in resultat_import:
                        messages.error(request, f"Erreur lors de l'import du fichier : {resultat_import['erreur']}")
                    else:
                        if resultat_import.get('latitude'):
                            commune_obj.latitude = resultat_import['latitude']
                        if resultat_import.get('longitude'):
                            commune_obj.longitude = resultat_import['longitude']
                        if resultat_import.get('geometrie'):
                            commune_obj.geom = resultat_import['geometrie']
                
                # Sinon, utiliser la saisie manuelle de lat/lon
                elif lat is not None and lon is not None:
                    commune_obj.latitude = lat
                    commune_obj.longitude = lon
                
                # Traiter la géométrie du tracé sur la carte
                wkt_data = request.POST.get('geom')
                
                if wkt_data:
                    spatial_geom = GEOSGeometry(wkt_data, srid=4326)
                    commune_obj.geom = spatial_geom
                    
                    # Calcul de la superficie réelle en Hectares via projection métrique (EPSG:3857)
                    geom_proj = spatial_geom.transform(3857, clone=True)
                    commune_obj.superficie = round(geom_proj.area / 10000, 2)
                    
                    # Si on n'a pas lat/lon, calculer depuis le centroïde du polygone
                    if not commune_obj.latitude or not commune_obj.longitude:
                        centroid = spatial_geom.centroid
                        commune_obj.latitude = centroid.y
                        commune_obj.longitude = centroid.x
                
                commune_obj.save()
                messages.success(request, f"La commune '{commune_obj.nom}' a été enregistrée et cartographiée avec succès.")
                return redirect('liste_communes')
                
            except Exception as e:
                messages.error(request, f"Erreur de traitement géospatiale : {e}")
        else:
            messages.error(request, "Veuillez vérifier les informations saisies.")
    else:
        form = CommuneForm(instance=commune)
        
    return render(request, 'admin/ajouter_commune.html', {
        'form': form,
        'title': title,
        'geom_wkt': geom_wkt,
        'is_edit': pk is not None
    })


@login_required(login_url='connexion')
def supprimer_commune(request, pk):
    """Suppression définitive d'un polygone communal dans la base de données"""
    commune = get_object_or_404(Commune, pk=pk)
    nom_commune = commune.nom
    commune.delete()
    messages.success(request, f"La commune '{nom_commune}' a été supprimée de l'inventaire territorial.")
    return redirect('liste_communes')

# ==========================================
# 4. CONTRÔLEURS ÉQUIPEMENTS (CRUD & SPATIAL)
# ==========================================
# Les contrôleurs d'équipement principaux sont définis plus bas dans le fichier,
# après les vues de groupe et d'utilisateur. Cette section conserve la structure
# du fichier tout en évitant les définitions dupliquées.

@login_required(login_url='connexion')
def supprimer_equipement_view(request, pk):
    """Suppression définitive d'une entité au sein de l'extension PostGIS avec traçabilité"""
    equipement = get_object_or_404(Equipement, pk=pk)

    # Permission: seul le créateur ou un superuser peut supprimer
    if not (request.user == equipement.cree_par or request.user.is_superuser):
        messages.error(request, "Vous n'êtes pas autorisé à supprimer cet équipement.")
        return redirect('liste_equipements')

    nom_equipement = equipement.nom
    code_ident = equipement.code_identification
    
    # --- JOURNAL D'AUDIT : ENREGISTREMENT AVANT SUPPRESSION ---
    JournalAudit.objects.create(
        utilisateur=request.user,
        action_type='SUPPRESSION',
        module='EQUIPEMENT',
        description=f"Suppression définitive de l'infrastructure : {nom_equipement} (Code ID: {code_ident} | ID BDD: {pk})",
        adresse_ip=obtenir_ip_client(request)
    )
    
    # Destruction physique de la donnée (Django et PostGIS nettoient la liaison OneToOne)
    equipement.delete()
    
    messages.success(request, f"L'équipement '{nom_equipement}' a été supprimé de la base de données spatiale.")
    return redirect('liste_equipements')

def api_un_secteur_geojson(request, secteur_id):
    """API Rest : Renvoie les primitives géométriques d'un secteur pour l'analyse spatiale"""
    secteur = get_object_or_404(Secteur, pk=secteur_id)
    geojson_data = {
        "type": "Feature",
        "geometry": json.loads(secteur.geom.geojson) if secteur.geom else None,
        "properties": {
            "nom": secteur.nom,
            "commune": secteur.commune.nom
        }
    }
    return JsonResponse(geojson_data)


def api_limites_commune_geojson(request, commune_id):
    """API Rest : Extrait et renvoie la géométrie d'une commune spécifique pour Leaflet"""
    commune = get_object_or_404(Commune, pk=commune_id)
    
    geojson_data = {
        "type": "Feature",
        "geometry": json.loads(commune.geom.geojson) if commune.geom else None,
        "properties": {
            "nom": commune.nom,
            "population": commune.population or "N/A",
            "superficie": commune.superficie or "N/A"
        }
    }
    return JsonResponse(geojson_data)


# ==========================================
# 5. GESTION DES SECTEURS / QUARTIERS (CRUD & SPATIAL)
# ==========================================

@login_required(login_url='connexion')
def liste_secteurs(request):
    """Registre global des secteurs/quartiers enregistrés dans le SIG"""
    secteurs = Secteur.objects.all().select_related('commune').order_by('nom')
    return render(request, 'admin/liste_secteurs.html', {
        'secteurs': secteurs,
        'total': secteurs.count()
    })


def api_secteurs_par_commune(request, commune_id):
    """Renvoie tous les secteurs rattachés à une commune spécifique au format GeoJSON"""
    secteurs = Secteur.objects.filter(commune_id=commune_id)
    geojson_data = serialize('geojson', secteurs, geometry_field='geom', fields=('nom',))
    return JsonResponse(json.loads(geojson_data), safe=False)


@login_required(login_url='connexion')
def gestion_secteur(request, pk=None):
    """Contrôleur hybride CRUD prenant en charge le WKT, GeoJSON brut et lat/lon pour le tracé"""
    if pk:
        secteur = get_object_or_404(Secteur, pk=pk)
        title = "Modifier le Secteur"
        geom_wkt = secteur.geom.wkt if secteur.geom else ""
    else:
        secteur = None
        title = "Ajouter un Secteur"
        geom_wkt = ""

    if request.method == 'POST':
        form = SecteurForm(request.POST, request.FILES, instance=secteur)
        raw_geom_data = request.POST.get('geom')
        
        if form.is_valid():
            try:
                obj_secteur = form.save(commit=False)
                
                # Récupérer la latitude et longitude du formulaire
                lat = form.cleaned_data.get('latitude')
                lon = form.cleaned_data.get('longitude')
                
                # Récupérer le fichier d'import s'il existe
                fichier_import = request.FILES.get('fichier_import')
                
                # Traiter l'import de fichier en priorité
                if fichier_import:
                    resultat_import = traiter_import_fichier(fichier_import)
                    if 'erreur' in resultat_import:
                        messages.error(request, f"Erreur lors de l'import du fichier : {resultat_import['erreur']}")
                    else:
                        if resultat_import.get('latitude'):
                            obj_secteur.latitude = resultat_import['latitude']
                        if resultat_import.get('longitude'):
                            obj_secteur.longitude = resultat_import['longitude']
                        if resultat_import.get('geometrie'):
                            obj_secteur.geom = resultat_import['geometrie']
                
                # Sinon, utiliser la saisie manuelle de lat/lon
                elif lat is not None and lon is not None:
                    obj_secteur.latitude = lat
                    obj_secteur.longitude = lon
                
                # Traiter la géométrie du tracé sur la carte
                if raw_geom_data:
                    if raw_geom_data.strip().startswith('{'):
                        try:
                            geojson_obj = json.loads(raw_geom_data)
                            if "geometry" in geojson_obj:
                                raw_geom_data = json.dumps(geojson_obj["geometry"])
                        except Exception:
                            pass
                        obj_secteur.geom = GEOSGeometry(raw_geom_data, srid=4326)
                    else:
                        obj_secteur.geom = GEOSGeometry(raw_geom_data, srid=4326)
                    
                    # Calcul de la superficie réelle en Hectares via projection métrique (EPSG:3857)
                    geom_proj = obj_secteur.geom.transform(3857, clone=True)
                    obj_secteur.superficie = round(geom_proj.area / 10000, 2)
                    
                    # Si on n'a pas lat/lon, calculer depuis le centroïde du polygone
                    if not obj_secteur.latitude or not obj_secteur.longitude:
                        centroid = obj_secteur.geom.centroid
                        obj_secteur.latitude = centroid.y
                        obj_secteur.longitude = centroid.x
                
                obj_secteur.save()
                messages.success(request, f"Le secteur '{obj_secteur.nom}' a été enregistré avec succès.")
                return redirect('liste_secteurs')
                
            except Exception as e:
                messages.error(request, f"Erreur de conversion spatiale : {e}")
        else:
            messages.error(request, "Veuillez vérifier les informations du secteur.")
    else:
        form = SecteurForm(instance=secteur)
        
    return render(request, 'admin/ajouter_secteur.html', {
        'form': form, 
        'title': title, 
        'geom_wkt': geom_wkt
    })


@login_required(login_url='connexion')
def supprimer_secteur(request, pk):
    """Suppression définitive d'un polygone de secteur dans PostGIS"""
    secteur = get_object_or_404(Secteur, pk=pk)
    nom_secteur = secteur.nom
    secteur.delete()
    messages.success(request, f"Le secteur '{nom_secteur}' a été supprimé de l'inventaire territorial.")
    return redirect('liste_secteurs')


def api_equipements_par_secteur(request):
    """API simple pour récupérer les équipements d'un secteur donné"""
    secteur_id = request.GET.get('secteur')
    if not secteur_id:
        return JsonResponse([], safe=False)
    
    equipements = Equipement.objects.filter(secteur_id=secteur_id)
    data = []
    for e in equipements:
        if e.localisation:
            data.append({
                "id": e.id,
                "nom": e.nom,
                "lat": e.localisation.y,
                "lng": e.localisation.x,
                "type_equipement": e.type_equipement.libelle if e.type_equipement else "N/A"
            })
            
    return JsonResponse(data, safe=False)


# ==========================================
# 6. NOMENCLATURES ET CATÉGORIES (ADMIN)
# ==========================================

@login_required(login_url='connexion')
def liste_types_equipements(request):
    """Console d'administration globale des nomenclatures et types d'infrastructures"""
    types_equipements = TypeEquipement.objects.all().order_by('libelle')
    return render(request, 'admin/liste_types_equipements.html', {
        'types_equipements': types_equipements
    })


@login_required(login_url='connexion')
def ajouter_type_equipement(request):
    """Formulaire d'ajout d'une nouvelle catégorie"""
    if request.method == "POST":
        libelle = request.POST.get('libelle')
        icone = request.POST.get('icone')

        if libelle:
            TypeEquipement.objects.create(libelle=libelle, icone=icone)
            messages.success(request, f"La catégorie '{libelle}' a été ajoutée avec succès.")
            return redirect('liste_types_equipements')
        else:
            messages.error(request, "Veuillez remplir tous les champs obligatoires.")

    return render(request, 'admin/ajouter_type_equipement.html')


@login_required(login_url='connexion')
def modifier_type_equipement(request, pk):
    """Formulaire de modification d'une catégorie existante"""
    type_equipement = get_object_or_404(TypeEquipement, pk=pk)
    
    if request.method == "POST":
        libelle = request.POST.get('libelle')
        icone = request.POST.get('icone')

        if libelle:
            type_equipement.libelle = libelle
            type_equipement.icone = icone
            type_equipement.save()
            messages.success(request, f"La catégorie '{libelle}' a été modifiée avec succès.")
            return redirect('liste_types_equipements')
        else:
            messages.error(request, "Veuillez remplir tous les champs obligatoires.")

    return render(request, 'admin/ajouter_type_equipement.html', {
        'type_equipement': type_equipement,
        'type_id': pk
    })


@login_required(login_url='connexion')
def supprimer_type_equipement(request, pk):
    type_obj = get_object_or_404(TypeEquipement, pk=pk)
    nom_type = type_obj.libelle
    type_obj.delete()
    messages.success(request, f"Le type d'équipement '{nom_type}' a été supprimé avec succès.")
    return redirect('liste_types_equipements')


@login_required(login_url='connexion')
def liste_etats_physiques(request):
    """Console d'administration globale des états physiques des infrastructures"""
    etats = EtatPhysique.objects.all().order_by('libelle')
    return render(request, 'admin/liste_etats_physiques.html', {
        'etats_physiques': etats
    })


@login_required(login_url='connexion')
def ajouter_etat_physique(request):
    """Formulaire d'ajout d'une nouvelle nomenclature d'état physique"""
    title = "Ajouter un nouvel État Physique"
    if request.method == "POST":
        form = EtatPhysiqueForm(request.POST)
        if form.is_valid():
            etat_obj = form.save()
            messages.success(request, f"L'état physique '{etat_obj.libelle}' a été ajouté avec succès.")
            return redirect('liste_etats_physiques')
        else:
            messages.error(request, "Échec de l'enregistrement. Veuillez vérifier les données saisies.")
    else:
        form = EtatPhysiqueForm()

    return render(request, 'admin/form_etat_physique.html', {
        'form': form,
        'title': title
    })


@login_required(login_url='connexion')
def modifier_etat_physique(request, pk):
    """Formulaire de modification d'un état physique existant"""
    etat = get_object_or_404(EtatPhysique, pk=pk)
    title = f"Modifier l'état : {etat.libelle}"
    
    if request.method == "POST":
        form = EtatPhysiqueForm(request.POST, instance=etat)
        if form.is_valid():
            form.save()
            messages.success(request, f"L'état physique '{etat.libelle}' a été modifié avec succès.")
            return redirect('liste_etats_physiques')
        else:
            messages.error(request, "Veuillez corriger les erreurs du formulaire.")
    else:
        form = EtatPhysiqueForm(instance=etat)

    return render(request, 'admin/form_etat_physique.html', {
        'form': form,
        'title': title,
        'is_edit': True
    })


@login_required(login_url='connexion')
def supprimer_etat_physique(request, pk):
    """Suppression définitive d'un état physique"""
    etat = get_object_or_404(EtatPhysique, pk=pk)
    nom_etat = etat.libelle
    try:
        etat.delete()
        messages.success(request, f"L'état physique '{nom_etat}' a été supprimé avec succès.")
    except Exception:
        messages.error(request, f"Impossible de supprimer '{nom_etat}' car il est actuellement lié à des infrastructures.")
    return redirect('liste_etats_physiques')


@login_required(login_url='connexion')
def liste_statuts_fonctionnels(request):
    """Console d'administration globale des statuts fonctionnels des infrastructures"""
    statuts = StatutFonctionnement.objects.all().order_by('libelle')
    return render(request, 'admin/liste_statuts_fonctionnels.html', {
        'statuts_fonctionnels': statuts
    })


@login_required(login_url='connexion')
def ajouter_statut_fonctionnel(request):
    """Formulaire d'ajout d'une nouvelle nomenclature de statut fonctionnel"""
    title = "Ajouter un nouveau Statut Fonctionnel"
    if request.method == "POST":
        form = StatutFonctionnementForm(request.POST)
        if form.is_valid():
            statut_obj = form.save()
            messages.success(request, f"Le statut fonctionnel '{statut_obj.libelle}' a été ajouté avec succès.")
            return redirect('liste_statuts_fonctionnels')
        else:
            messages.error(request, "Échec de l'enregistrement. Veuillez vérifier les données saisies.")
    else:
        form = StatutFonctionnementForm()

    return render(request, 'admin/form_statut_fonctionnel.html', {
        'form': form,
        'title': title
    })


@login_required(login_url='connexion')
def modifier_statut_fonctionnel(request, pk):
    """Formulaire de modification d'un statut fonctionnel existant"""
    statut = get_object_or_404(StatutFonctionnement, pk=pk)
    title = f"Modifier le statut : {statut.libelle}"
    
    if request.method == "POST":
        form = StatutFonctionnementForm(request.POST, instance=statut)
        if form.is_valid():
            form.save()
            messages.success(request, f"Le statut fonctionnel '{statut.libelle}' a été modifié avec succès.")
            return redirect('liste_statuts_fonctionnels')
        else:
            messages.error(request, "Veuillez corriger les erreurs du formulaire.")
    else:
        form = StatutFonctionnementForm(instance=statut)

    return render(request, 'admin/form_statut_fonctionnel.html', {
        'form': form,
        'title': title,
        'is_edit': True
    })


@login_required(login_url='connexion')
def supprimer_statut_fonctionnel(request, pk):
    """Suppression définitive d'un statut fonctionnel"""
    statut = get_object_or_404(StatutFonctionnement, pk=pk)
    nom_statut = statut.libelle
    try:
        statut.delete()
        messages.success(request, f"Le statut fonctionnel '{nom_statut}' a été supprimé avec succès.")
    except Exception:
        messages.error(request, f"Impossible de supprimer '{nom_statut}' car il est actuellement lié à des infrastructures.")
    return redirect('liste_statuts_fonctionnels')


# ==========================================
# 7. AUTHENTIFICATION (ACCÈS SÉCURISÉ)
# ==========================================

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages

def connexion_view(request):
    if request.user.is_authenticated:
        # Si déjà connecté et fait partie des gestionnaires, direction le dashboard
        if request.user.is_superuser or request.user.groups.filter(name__iexact="Agent").exists():
            return redirect('admin_dashboard')
        return redirect('carte_index')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                
                if user.is_superuser:
                    messages.success(request, f"Bienvenue, Administrateur {user.username} !")
                    return redirect('admin_dashboard')
                
                elif user.groups.filter(name__iexact="Agent").exists():
                    messages.success(request, f"Espace Agent : Bienvenue, {user.username} !")
                    return redirect('admin_dashboard')
                
                else:
                    messages.info(request, f"Connexion réussie. Bienvenue {user.username}.")
                    return redirect('carte_index')
            else:
                messages.error(request, "Identifiants invalides.")
        else:
            messages.error(request, "Formulaire de connexion invalide.")
    else:
        form = AuthenticationForm()
        
    # CORRECTION ICI : Utilisation de ton template dans templates/admin/connexion_premuim.html
    return render(request, 'admin/connexion_premium.html', {'form': form})

def deconnexion_view(request):
    """Vue pour fermer la session de l'utilisateur"""
    logout(request)
    messages.info(request, "Vous avez été déconnecté avec succès.")
    return redirect('connexion')

@login_required(login_url='connexion')
def journal_audit_view(request):
    """Module de sécurité : réservé uniquement au Superadmin"""
    # Si un agent essaie de tricher en tapant l'URL directement, on le bloque
    if request.user.groups.filter(name__iexact="Agent").exists() or not request.user.is_superuser:
        messages.error(request, "Accès refusé : privilèges insuffisants.")
        return redirect('admin_dashboard')
        
    # On récupère tous les logs triés du plus récent au plus ancien
    logs_audit = JournalAudit.objects.select_related('utilisateur').order_by('-date_action')
    
    context = {
        'logs_audit': logs_audit,
        'total_logs': logs_audit.count(),
        # AJOUT CRUCIAL : On passe l'information pour que le template sache qu'il s'agit de l'Admin (is_agent = False)
        'is_agent': request.user.groups.filter(name__iexact="Agent").exists(), 
    }
    return render(request, 'admin/journal_audit.html', context)

# Remplacer "from .forms import UtilisateurForm" par :
from .forms import UtilisateurCreationForm, UtilisateurModificationForm

# =================================================================
# MODULE GESTION DES AGENTS / UTILISATEURS (ADMINISTRATION PREMIUM)
# =================================================================
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from .models import JournalAudit
from .forms import UtilisateurCreationForm, UtilisateurModificationForm

@login_required(login_url='connexion')
def liste_utilisateurs(request):
    """
    Vue pour lister tous les agents/utilisateurs du système.
    Sécurité : Réservé uniquement au Superadmin.
    """
    if request.user.groups.filter(name__iexact="Agent").exists() or not request.user.is_superuser:
        messages.error(request, "Accès refusé : privilèges insuffisants pour gérer les comptes.")
        return redirect('admin_dashboard')

    utilisateurs = User.objects.filter(is_superuser=False).order_by('-date_joined')
    
    context = {
        'utilisateurs': utilisateurs,
        'total_agents': utilisateurs.count(),
        'is_agent': False  
    }
    return render(request, 'admin/liste_utilisateurs.html', context)


@login_required(login_url='connexion')
def ajouter_utilisateur(request):
    """
    Vue pour créer un nouveau compte Agent avec attribution de rôle et audit.
    """
    if request.user.groups.filter(name__iexact="Agent").exists() or not request.user.is_superuser:
        messages.error(request, "Accès refusé : privilèges insuffisants.")
        return redirect('admin_dashboard')

    if request.method == 'POST':
        # Utilisation du formulaire de CREATION
        form = UtilisateurCreationForm(request.POST)
        if form.is_valid():
            nouvel_agent = form.save()
            
            JournalAudit.objects.create(
                utilisateur=request.user,
                action_type='AJOUT',
                module='CONFIGURATION',
                description=f"Création du compte agent : {nouvel_agent.username} ({nouvel_agent.get_full_name()})",
                adresse_ip=obtenir_ip_client(request),
                date_action=timezone.now()
            )
            
            messages.success(request, f"Le compte de l'agent '{nouvel_agent.username}' a été créé avec succès.")
            return redirect('liste_utilisateurs')
        else:
            messages.error(request, "Erreur lors de la création. Veuillez corriger les champs invalides.")
    else:
        form = UtilisateurCreationForm()

    return render(request, 'admin/form_utilisateur.html', {
        'form': form,
        'titre': "Créer un nouveau compte Agent",
        'is_agent': False
    })


@login_required(login_url='connexion')
def modifier_utilisateur(request, pk):
    """
    Vue pour modifier un compte agent existant (Profil, rôle, statut ou mot de passe).
    """
    if request.user.groups.filter(name__iexact="Agent").exists() or not request.user.is_superuser:
        messages.error(request, "Accès refusé : privilèges insuffisants.")
        return redirect('admin_dashboard')

    agent = get_object_or_404(User, pk=pk, is_superuser=False)

    if request.method == 'POST':
        # Utilisation du formulaire de MODIFICATION
        form = UtilisateurModificationForm(request.POST, instance=agent)
        if form.is_valid():
            form.save()
            
            JournalAudit.objects.create(
                utilisateur=request.user,
                action_type='MODIFICATION',
                module='CONFIGURATION',
                description=f"Modification des informations de l'agent : {agent.username}",
                adresse_ip=obtenir_ip_client(request),
                date_action=timezone.now()
            )
            
            messages.success(request, f"Le compte de l'agent '{agent.username}' a été mis à jour.")
            return redirect('liste_utilisateurs')
        else:
            messages.error(request, "Erreur lors de la modification. Veuillez vérifier les données saisies.")
    else:
        form = UtilisateurModificationForm(instance=agent)

    return render(request, 'admin/form_utilisateur.html', {
        'form': form,
        'titre': f"Modifier le compte Agent : {agent.username}",
        'is_agent': False
    })


@login_required(login_url='connexion')
def supprimer_utilisateur(request, pk):
    """
    Vue pour supprimer définitivement un compte agent.
    """
    if request.user.groups.filter(name__iexact="Agent").exists() or not request.user.is_superuser:
        messages.error(request, "Accès refusé : privilèges insuffisants.")
        return redirect('admin_dashboard')

    agent = get_object_or_404(User, pk=pk, is_superuser=False)
    nom_utilisateur = agent.username

    JournalAudit.objects.create(
        utilisateur=request.user,
        action_type='SUPPRESSION',
        module='CONFIGURATION',
        description=f"Suppression définitive du compte agent : {nom_utilisateur}",
        adresse_ip=obtenir_ip_client(request),
        date_action=timezone.now()
    )

    agent.delete()
    messages.success(request, f"Le compte de l'agent '{nom_utilisateur}' a été supprimé définitivement du SIG.")
    return redirect('liste_utilisateurs')

from django.contrib.auth.models import Group
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django import forms

# --- FORMULAIRE DJANGO POUR LES GROUPES ---
class GroupeForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['name', 'permissions']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Agent Communal'}),
            'permissions': forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        }

# --- 1. VUE : LISTER LES GROUPES ---
@login_required
@user_passes_test(lambda u: u.is_superuser)
def liste_groupes(request):
    groupes = Group.objects.all()
    return render(request, 'admin/liste_groupes.html', {'groupes': groupes})

# =====================================================================
# 2. GESTION DU REGISTRE DES ÉQUIPEMENTS / INFRASTRUCTURES (CRUD DYNAMIQUE)
# =====================================================================

from django.contrib.gis.geos import Point

# Dictionnaire de correspondance : associe chaque type d'infrastructure à son Formulaire Django 
# et au nom de sa relation inverse (related_name) définie dans vos modèles.
FORM_MAPPING = {
    'ecole': (DetailsEcoleForm, 'details_ecole'),
    'sante': (DetailsSanteForm, 'details_sante'),
    'forage': (DetailsForageForm, 'details_forage'),
    'marche': (DetailsMarcheForm, 'details_marche'),
    'administration': (DetailsAdministrationForm, 'details_administration'),
    'assainissement': (DetailsAssainissementForm, 'details_assainissement'),
    'sport': (DetailsSportForm, 'details_sport'),
    'eclairage': (DetailsEclairageForm, 'details_eclairage'),
}

def get_type_key(type_obj):
    """
    Fonction utilitaire pour normaliser le libellé du type d'équipement
    et trouver la bonne clé dans notre dictionnaire FORM_MAPPING.
    """
    if not type_obj:
        return None

    libelle = getattr(type_obj, 'libelle', None) or getattr(type_obj, 'nom', None) or str(type_obj)
    if not libelle:
        return None

    nom_clean = libelle.lower()
    if 'ecole' in nom_clean or 'école' in nom_clean or 'scolaire' in nom_clean or 'education' in nom_clean:
        return 'ecole'
    elif 'sante' in nom_clean or 'santé' in nom_clean or 'medical' in nom_clean or 'hopital' in nom_clean:
        return 'sante'
    elif 'forage' in nom_clean or 'eau' in nom_clean or 'puits' in nom_clean:
        return 'forage'
    elif 'marche' in nom_clean or 'marché' in nom_clean:
        return 'marche'
    elif 'admin' in nom_clean or 'mairie' in nom_clean:
        return 'administration'
    elif 'assainis' in nom_clean or 'latrine' in nom_clean:
        return 'assainissement'
    elif 'sport' in nom_clean or 'stade' in nom_clean:
        return 'sport'
    elif 'eclairage' in nom_clean or 'éclairage' in nom_clean or 'solaire' in nom_clean:
        return 'eclairage'
    return None


@login_required
def liste_equipements(request):
    """Vue pour lister l'ensemble des équipements inscrits"""
    equipements = Equipement.objects.all().order_by('-id')
    return render(request, 'admin/liste_equipements.html', {'equipements': equipements})


@login_required
def ajouter_equipement(request):
    """Vue pour traiter la création d'un équipement (Formulaire Général + Détails métiers dynamiques + Audit)"""
    
    # 1. Sécurité et UX : Initialisation par défaut pour éviter l'UnboundLocalError
    form_details = None
    type_key = None
    
    # Récupération de la clé du type si elle est passée par le JavaScript dans l'URL (?type_id=...) ou via POST (AJAX)
    type_id_intermediaire = request.POST.get('type_id') or request.GET.get('type_id')

    # --- Gestion du cas où l'utilisateur change le type via une navigation GET (ou AJAX GET)
    if request.method == 'GET' and type_id_intermediaire:
        try:
            type_obj = TypeEquipement.objects.get(id=type_id_intermediaire)
            type_key = get_type_key(type_obj)
            form_details_class, _ = FORM_MAPPING.get(type_key, (None, None))
            form_details = form_details_class() if form_details_class else None
        except (TypeEquipement.DoesNotExist, ValueError):
            form_details = None

        # Si AJAX, renvoyer uniquement le fragment HTML des détails métiers
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            html = render_to_string('admin/partials/details_metiers.html', {
                'sous_form': form_details,
                'type_nom': getattr(type_obj, 'libelle', '') if 'type_obj' in locals() else ''
            }, request=request)
            return JsonResponse({'html': html})

        # sinon rendu complet pour GET classique
        form = EquipementForm()
        return render(request, 'admin/form_equipement.html', {
            'form': form,
            'form_details': form_details,
            'sous_form': form_details,
            'title': "Saisir un Nouvel Équipement",
            'type_key': type_key,
            'type_nom': getattr(type_obj, 'libelle', '') if 'type_obj' in locals() else '',
            'all_details_forms': {
                'ecole': DetailsEcoleForm(), 'sante': DetailsSanteForm(),
                'forage': DetailsForageForm(), 'marche': DetailsMarcheForm(),
                'administration': DetailsAdministrationForm(), 'assainissement': DetailsAssainissementForm(),
                'sport': DetailsSportForm(), 'eclairage': DetailsEclairageForm(),
            }
        })

    if request.method == 'POST':
        form = EquipementForm(request.POST)
        
        # 2. CAS INTERMÉDIAIRE : L'utilisateur change le type d'équipement dans la liste déroulante
        # On détecte que c'est une soumission provoquée par le JavaScript (grâce au paramètre dans l'URL)
        if type_id_intermediaire:
            try:
                # On récupère l'objet TypeEquipement sélectionné
                type_obj = TypeEquipement.objects.get(id=type_id_intermediaire)
                type_key = get_type_key(type_obj)
                
                # On récupère le bon sous-formulaire dans le dictionnaire FORM_MAPPING
                form_details_class, _ = FORM_MAPPING.get(type_key, (None, None))
                if form_details_class:
                    # On l'instancie à vide pour qu'il s'affiche proprement à l'écran
                        form_details = form_details_class()
            except (TypeEquipement.DoesNotExist, ValueError):
                pass
                
            # On réaffiche le formulaire immédiatement avec les données saisies préservées,
            # sans bloquer sur les champs obligatoires non encore saisis.
                # If the request was initiated via AJAX, return only the fragment HTML
                context_fragment = {
                    'sous_form': form_details,
                    'type_nom': getattr(type_obj, 'libelle', '') if 'type_obj' in locals() else ''
                }
                if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
                    html = render_to_string('admin/partials/details_metiers.html', context_fragment, request=request)
                    return JsonResponse({'html': html})

                return render(request, 'admin/form_equipement.html', {
                    'form': form,
                    'form_details': form_details,
                    'sous_form': form_details,  # Harmonisation avec le template HTML
                    'title': "Saisir un Nouvel Équipement",
                    'type_key': type_key,
                    'type_nom': getattr(type_obj, 'libelle', '') if 'type_obj' in locals() else '',
                    'all_details_forms': {
                        'ecole': DetailsEcoleForm(), 'sante': DetailsSanteForm(),
                        'forage': DetailsForageForm(), 'marche': DetailsMarcheForm(),
                        'administration': DetailsAdministrationForm(), 'assainissement': DetailsAssainissementForm(),
                        'sport': DetailsSportForm(), 'eclairage': DetailsEclairageForm(),
                    }
                })

        # 3. CAS FINAL : L'utilisateur clique sur le bouton "Enregistrer l'Infrastructure"
        if form.is_valid():
            type_equipement = form.cleaned_data.get('type_equipement')
            type_key = get_type_key(type_equipement)
            form_details_class, _ = FORM_MAPPING.get(type_key, (None, None))
            
            if form_details_class:
                form_details = form_details_class(request.POST)
                # Si le sous-formulaire métier est invalide, on bloque et on lève les erreurs
                if not form_details.is_valid():
                    return render(request, 'admin/form_equipement.html', {
                        'form': form,
                        'form_details': form_details,
                        'sous_form': form_details,
                        'title': "Saisir un Nouvel Équipement",
                        'type_key': type_key,
                        'type_nom': getattr(type_equipement, 'libelle', '') if type_equipement else '',
                        'all_details_forms': {
                            'ecole': DetailsEcoleForm(), 'sante': DetailsSanteForm(),
                            'forage': DetailsForageForm(), 'marche': DetailsMarcheForm(),
                            'administration': DetailsAdministrationForm(), 'assainissement': DetailsAssainissementForm(),
                            'sport': DetailsSportForm(), 'eclairage': DetailsEclairageForm(),
                        }
                    })
            
            # Enregistrement du tronc commun en mémoire
            equipement = form.save(commit=False)
            
            # Traitement Spatial PostGIS (Latitude/Longitude)
            lat = form.cleaned_data.get('latitude')
            lon = form.cleaned_data.get('longitude')
            if lat is not None and lon is not None:
                equipement.localisation = Point(lon, lat, srid=4326)
            
            # Sauvegarde en Base de Données
            equipement.cree_par = request.user
            equipement.save()
            
            # Enregistrement des détails métiers correspondants
            if form_details:
                details = form_details.save(commit=False)
                details.equipement = equipement
                details.save()
            
            # Alimentation automatique du Journal d'Audit (Trame de Soutenance)
            JournalAudit.objects.create(
                utilisateur=request.user,
                action_type='AJOUT',
                module='EQUIPEMENT',
                description=f"Création de l'infrastructure : {equipement.nom} (Code: {equipement.code_identification})",
                adresse_ip=obtenir_ip_client(request)
            )
            
            messages.success(request, f"L'équipement '{equipement.nom}' a été créé avec succès.")
            return redirect('liste_equipements')

    else:
        # CAS D'OUVERTURE DE PAGE (GET Classique)
        form = EquipementForm()
        form_details = None

    # Rendu global de secours en cas d'erreur ou d'affichage initial
    return render(request, 'admin/form_equipement.html', {
        'form': form,
        'form_details': form_details,
        'sous_form': form_details,  # Assure la compatibilité double variable
        'title': "Saisir un Nouvel Équipement",
        'type_key': type_key,
        'type_nom': getattr(type_equipement, 'libelle', '') if request.method == 'POST' and 'type_equipement' in locals() else '',
        'all_details_forms': {
            'ecole': DetailsEcoleForm(),
            'sante': DetailsSanteForm(),
            'forage': DetailsForageForm(),
            'marche': DetailsMarcheForm(),
            'administration': DetailsAdministrationForm(),
            'assainissement': DetailsAssainissementForm(),
            'sport': DetailsSportForm(),
            'eclairage': DetailsEclairageForm(),
        }
    })


@login_required
def modifier_equipement(request, pk):
    """Vue pour modifier un équipement existant et mettre à jour ses détails métiers spécifiques"""
    equipement = get_object_or_404(Equipement, pk=pk)

    # Permission: seul le créateur ou un superuser peut modifier
    if not (request.user == equipement.cree_par or request.user.is_superuser):
        messages.error(request, "Vous n'êtes pas autorisé à modifier cet équipement.")
        return redirect('liste_equipements')
    
    # Détecter le type actuel pour récupérer la bonne instance de détails existante en BDD
    type_key_actuel = get_type_key(equipement.type_equipement)
    _, rel_name_actuel = FORM_MAPPING.get(type_key_actuel, (None, None))
    
    details_instance = None
    if rel_name_actuel and hasattr(equipement, rel_name_actuel):
        details_instance = getattr(equipement, rel_name_actuel)

    type_id_intermediaire = request.POST.get('type_id') or request.GET.get('type_id')
    if type_id_intermediaire:
        try:
            type_obj = TypeEquipement.objects.get(id=type_id_intermediaire)
            type_key_ajax = get_type_key(type_obj)
            form_details_class, _ = FORM_MAPPING.get(type_key_ajax, (None, None))
            form_details_ajax = form_details_class(request.POST) if (request.method == 'POST' and form_details_class) else (form_details_class() if form_details_class else None)
        except (TypeEquipement.DoesNotExist, ValueError):
            form_details_ajax = None

        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            html = render_to_string('admin/partials/details_metiers.html', {
                'sous_form': form_details_ajax,
                'type_nom': getattr(type_obj, 'libelle', '') if 'type_obj' in locals() else ''
            }, request=request)
            return JsonResponse({'html': html})

    if request.method == 'POST':
        form = EquipementForm(request.POST, instance=equipement)
        
        if form.is_valid():
            # On vérifie le type soumis (au cas où il a été modifié dans le formulaire)
            type_equipement_post = form.cleaned_data.get('type_equipement')
            type_key_post = get_type_key(type_equipement_post)
            form_details_class, rel_name_post = FORM_MAPPING.get(type_key_post, (None, None))
            
            # Déterminer la bonne instance à lier
            if type_key_post == type_key_actuel:
                instance_a_modifier = details_instance
            else:
                if rel_name_post and hasattr(equipement, rel_name_post):
                    instance_a_modifier = getattr(equipement, rel_name_post)
                else:
                    instance_a_modifier = None
            
            form_details = None
            if form_details_class:
                form_details = form_details_class(request.POST, instance=instance_a_modifier)
                if not form_details.is_valid():
                    return render(request, 'admin/form_equipement.html', {
                        'form': form,
                        'form_details': form_details,
                        'sous_form': form_details,
                        'equipement': equipement,
                        'title': f"Modifier l'Équipement : {equipement.nom}",
                        'type_key': type_key_post,
                        'type_nom': getattr(type_equipement_post, 'libelle', '') if type_equipement_post else ''
                    })

            # Mise à jour de l'équipement général
            equipement = form.save(commit=False)
            lat = form.cleaned_data.get('latitude')
            lon = form.cleaned_data.get('longitude')
            if lat is not None and lon is not None:
                equipement.localisation = Point(lon, lat, srid=4326)
                
            equipement.save()
            
            # Mise à jour des caractéristiques techniques spécifiques
            if form_details:
                details = form_details.save(commit=False)
                details.equipement = equipement
                details.save()
            
            # Journalisation de la modification
            JournalAudit.objects.create(
                utilisateur=request.user,
                action_type='MODIFICATION',
                module='EQUIPEMENT',
                description=f"Modification de l'infrastructure : {equipement.nom} (ID: {equipement.id})",
                adresse_ip=obtenir_ip_client(request)
            )
            
            messages.success(request, f"L'équipement '{equipement.nom}' a été mis à jour avec succès.")
            return redirect('liste_equipements')
    else:
        # Pré-remplir les coordonnées géographiques à l'affichage
        initial_coords = {}
        if equipement.localisation:
            initial_coords['longitude'] = equipement.localisation.x
            initial_coords['latitude'] = equipement.localisation.y
            
        form = EquipementForm(instance=equipement, initial=initial_coords)
        
        # Instanciation initiale du formulaire technique spécifique
        form_details_class, _ = FORM_MAPPING.get(type_key_actuel, (None, None))
        if form_details_class:
            form_details = form_details_class(instance=details_instance)
        else:
            form_details = None
        
    return render(request, 'admin/form_equipement.html', {
        'form': form,
        'form_details': form_details,
        'sous_form': form_details,
        'equipement': equipement,
        'title': f"Modifier l'Équipement : {equipement.nom}",
        'type_key': type_key_actuel,
        'type_nom': getattr(equipement.type_equipement, 'libelle', '') if equipement.type_equipement else ''
    })


@login_required
def supprimer_equipement(request, pk):
    """Vue pour supprimer définitivement un équipement du registre"""
    equipement = get_object_or_404(Equipement, pk=pk)
    nom_equipement = equipement.nom
    
    if request.method == 'POST':
        equipement.delete()
        
        # Enregistrement de l'action destructrice dans l'audit
        JournalAudit.objects.create(
            utilisateur=request.user,
            action_type='SUPPRESSION',
            module='EQUIPEMENT',
            description=f"Suppression définitive de l'infrastructure : {nom_equipement} (ID: {pk})",
            adresse_ip=obtenir_ip_client(request)
        )
        
        messages.success(request, f"L'équipement '{nom_equipement}' a été définitivement supprimé.")
        return redirect('liste_equipements')
        
    return render(request, 'admin/confirmer_suppression.html', {
        'objet': equipement, 
        'type': "l'équipement / infrastructure"
    })

# --- 2. VUE : AJOUTER UN GROUPE ---
@login_required
@user_passes_test(lambda u: u.is_superuser)
def ajouter_groupe(request):
    if request.method == 'POST':
        form = GroupeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Le groupe/profil a été créé avec succès.")
            return redirect('liste_groupes')
    else:
        form = GroupeForm()
    return render(request, 'admin/form_groupe.html', {'form': form, 'title': "Créer un nouveau Profil"})


# --- 3. VUE : MODIFIER UN GROUPE ---
@login_required
@user_passes_test(lambda u: u.is_superuser)
def modifier_groupe(request, pk):
    groupe = get_object_or_404(Group, pk=pk)
    if request.method == 'POST':
        form = GroupeForm(request.POST, instance=groupe)
        if form.is_valid():
            form.save()
            messages.success(request, f"Le groupe '{groupe.name}' a été mis à jour.")
            return redirect('liste_groupes')
    else:
        form = GroupeForm(instance=groupe)
    return render(request, 'admin/form_groupe.html', {'form': form, 'groupe': groupe, 'title': f"Modifier le Profil : {groupe.name}"})

# --- 4. VUE : SUPPRIMER UN GROUPE ---
@login_required
@user_passes_test(lambda u: u.is_superuser)
def supprimer_groupe(request, pk):
    groupe = get_object_or_404(Group, pk=pk)
    nom_groupe = groupe.name
    groupe.delete()
    messages.success(request, f"Le groupe '{nom_groupe}' a été supprimé avec succès.")
    return redirect('liste_groupes')
    return redirect('liste_groupes')