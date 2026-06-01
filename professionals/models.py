from django.db import models


class Profesionales(models.Model):
    matricula = models.CharField(max_length=256)
    id_usuario = models.ForeignKey('authentication.Usuarios', models.DO_NOTHING, db_column='id_usuario')

    class Meta:
        managed = False
        db_table = 'profesionales'
