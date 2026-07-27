from django.urls import path
from . import views

urlpatterns = [
    # --- ESPACE PUBLIC ---
    path('', views.carte_index, name='carte_index'),  # Accueil globale du SIG (Carte principale)
    
    # --- FLUX DE DONNÉES GÉOSPATIALES (API GeoJSON) ---
    path('api/equipements/', views.equipements_geojson, name='api_equipements'),  # Flux de points (infrastructures)
    path('api/secteurs/', views.secteurs_geojson, name='api_secteurs'),  # Flux de polygones (toutes les communes)
    path('api/secteurs/<int:secteur_id>/', views.api_un_secteur_geojson, name='api_un_secteur'), # Un seul secteur/commune
    
    # --- TABLEAU DE BORD PRINCIPAL (ADMIN) ---
    path('admin-dashboard/', views.dashboard_admin, name='admin_dashboard'),  
    
    # --- GESTION DES ÉQUIPEMENTS / INFRASTRUCTURES ---
    path('admin-space/equipements/', views.liste_equipements_view, name='liste_equipements'),
    path('admin-dashboard/equipement/add/', views.ajouter_equipement, name='ajouter_equipement'),
    path('admin-dashboard/equipement/<int:pk>/edit/', views.modifier_equipement, name='modifier_equipement'),
    path('admin-space/equipements/<int:pk>/delete/', views.supprimer_equipement_view, name='supprimer_equipement'),
    
    # --- GESTION DES TYPES D'ÉQUIPEMENTS (NOUVEAU MODULE UNIFORME) ---
    path('admin-space/types-equipements/', views.liste_types_equipements, name='liste_types_equipements'),
    path('admin-dashboard/types-equipements/add/', views.ajouter_type_equipement, name='ajouter_type_equipement'),
    path('admin-dashboard/types-equipements/<int:pk>/edit/', views.modifier_type_equipement, name='modifier_type_equipement'),
    path('admin-space/types-equipements/<int:pk>/delete/', views.supprimer_type_equipement, name='supprimer_type_equipement'),
    
    # --- GESTION DES COMMUNES (Nouveau système PostGIS optimisé) ---
    path('admin-space/communes/', views.liste_communes, name='liste_communes'),  # Tableau de bord des communes
    path('admin-dashboard/commune/add/', views.gestion_commune, name='ajouter_commune'),  # Ajout (sans PK)
    path('admin-dashboard/commune/<int:pk>/edit/', views.gestion_commune, name='modifier_commune'),  # Modification (avec PK)
    path('admin-space/commune/<int:pk>/delete/', views.supprimer_commune, name='supprimer_commune'),  # Suppression
    path('api/communes/<int:commune_id>/', views.api_limites_commune_geojson, name='api_limites_commune'),
    # --- GESTION DES SECTEURS / QUARTIERS ---
    path('admin-space/secteurs/', views.liste_secteurs, name='liste_secteurs'),  # Tableau de bord des secteurs
    path('admin-dashboard/secteur/add/', views.gestion_secteur, name='ajouter_secteur'),  # Ajout
    path('admin-dashboard/secteur/<int:pk>/edit/', views.gestion_secteur, name='modifier_secteur'),  # Modification
    path('admin-space/secteur/<int:pk>/delete/', views.supprimer_secteur, name='supprimer_secteur'),  # Suppression
    # Mettre ceci dans urlpatterns de urls.py :
    path('api/communes/<int:commune_id>/secteurs/', views.api_secteurs_par_commune, name='api_secteurs_par_commune'),
    # Dans urlpatterns de urls.py
    path('api/communes/all/', views.api_toutes_communes_geojson, name='api_toutes_communes'),
    path('api/equipements-secteur/', views.api_equipements_par_secteur, name='api_equipements_secteur'),
    # --- GESTION DES ÉTATS PHYSIQUES (MODULE UNIFORME CALQUÉ) ---
    path('admin-space/etats-physiques/', views.liste_etats_physiques, name='liste_etats_physiques'),
    path('admin-dashboard/etats-physiques/add/', views.ajouter_etat_physique, name='ajouter_etat_physique'),
    path('admin-dashboard/etats-physiques/<int:pk>/edit/', views.modifier_etat_physique, name='modifier_etat_physique'),
    path('admin-space/etats-physiques/<int:pk>/delete/', views.supprimer_etat_physique, name='supprimer_etat_physique'),
    # --- GESTION DES STATUTS FONCTIONNELS (MODULE UNIFORME ALIGNÉ) ---
    path('admin-space/statuts-fonctionnels/', views.liste_statuts_fonctionnels, name='liste_statuts_fonctionnels'),
    path('admin-dashboard/statuts-fonctionnels/add/', views.ajouter_statut_fonctionnel, name='ajouter_statut_fonctionnel'),
    path('admin-dashboard/statuts-fonctionnels/<int:pk>/edit/', views.modifier_statut_fonctionnel, name='modifier_statut_fonctionnel'),
    path('admin-space/statuts-fonctionnels/<int:pk>/delete/', views.supprimer_statut_fonctionnel, name='supprimer_statut_fonctionnel'),
    
    path('connexion/', views.connexion_view, name='connexion'), # Page d'accueil par défaut de l'application
    path('logout/', views.deconnexion_view, name='deconnexion'),
    path('deconnexion/', views.deconnexion_view, name='deconnexion'),
    path('administration/journal-audit/', views.journal_audit_view, name='journal_audit'),
    
    
    # --- GESTION DES UTILISATEURS (TES PAGES PERSONNALISÉES) ---
    path('admin-space/utilisateurs/', views.liste_utilisateurs, name='liste_utilisateurs'),
    path('admin-space/utilisateurs/add/', views.ajouter_utilisateur, name='ajouter_utilisateur'),
    path('admin-space/utilisateurs/<int:pk>/edit/', views.modifier_utilisateur, name='modifier_utilisateur'),
    path('admin-space/utilisateurs/<int:pk>/delete/', views.supprimer_utilisateur, name='supprimer_utilisateur'),
    
# MODULE DE GESTION DES GROUPES (Uniformisé avec le préfixe gestion/)
    path('gestion/groupes/', views.liste_groupes, name='liste_groupes'),
    path('gestion/groupes/ajouter/', views.ajouter_groupe, name='ajouter_groupe'),
    path('gestion/groupes/modifier/<int:pk>/', views.modifier_groupe, name='modifier_groupe'),
    path('gestion/groupes/supprimer/<int:pk>/', views.supprimer_groupe, name='supprimer_groupe'), 
 
]
