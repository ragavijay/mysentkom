from django.urls import path
from . import views

urlpatterns = [
    path('', views.user_login, name='login'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('sentiment/', views.sentiment_analysis, name='sentiment_analysis'),
    path('cluster/', views.cluster_analysis, name='cluster_analysis'),
    path('demographic/', views.demographic_analysis, name='demographic_analysis'),
    
    # Management URLs
    path('manage/clusters/', views.manage_clusters, name='manage_clusters'),
    path('manage/clusters/add/', views.add_cluster, name='add_cluster'),
    path('manage/clusters/edit/<int:cluster_id>/', views.edit_cluster, name='edit_cluster'),
    path('manage/clusters/delete/<int:cluster_id>/', views.delete_cluster, name='delete_cluster'),
    path('manage/posts/', views.manage_posts, name='manage_posts'),
    path('manage/posts/add/', views.add_post, name='add_post'),
    path('manage/posts/edit/<int:post_id>/', views.edit_post, name='edit_post'),
    path('manage/posts/delete/<int:post_id>/', views.delete_post, name='delete_post'),
]