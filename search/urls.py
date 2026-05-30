from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'search'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('results/', views.ResultsView.as_view(), name='results'),
    path('evaluate/', views.EvaluateView.as_view(), name='evaluate'),
    path('upload/', views.UploadView.as_view(), name='upload'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('history/', views.SearchHistoryView.as_view(), name='history'),
    path('doc/<int:doc_id>/', views.DocumentDetailView.as_view(), name='document_detail'),
    path('autocomplete/', views.AutocompleteView.as_view(), name='autocomplete'),
    
    # Auth URLs
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]
