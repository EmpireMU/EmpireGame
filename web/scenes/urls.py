from django.urls import path

from .views import SceneDetailView, SceneDownloadView, SceneListView

app_name = "scenes"

urlpatterns = [
    path("", SceneListView.as_view(), name="list"),
    path("<int:pk>/", SceneDetailView.as_view(), name="detail"),
    path("<int:pk>/download/", SceneDownloadView.as_view(), name="download"),
]
