from strawberry.django.views import GraphQLView
from apps.graphql_api.schema import schema   # your strawberry.Schema instance
from django.urls import path

urlpatterns = [
    path("graphql/", GraphQLView.as_view(schema=schema)),
]