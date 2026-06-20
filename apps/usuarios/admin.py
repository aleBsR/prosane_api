from django.contrib import admin

from apps.usuarios.models import Action, ActionRole, Usuario


admin.site.register(Usuario)
admin.site.register(Action)
admin.site.register(ActionRole)
