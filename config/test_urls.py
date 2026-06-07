"""URLconf mínimo para la suite de tests.

El `config.urls` real depende de apps con URLs todavía rotas (p. ej. falta
`patients/urls.py`), lo que haría crashear el system check al correr `manage.py
test`. Los tests del componente `common` no rutean URLs (usan APIRequestFactory
y llaman a los métodos de las vistas directo), así que un urlconf vacío alcanza
y mantiene la suite aislada de esos bugs pre-existentes.
"""

urlpatterns = []
