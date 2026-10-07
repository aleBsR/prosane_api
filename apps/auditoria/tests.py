from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command

from rest_framework.test import APITestCase

from apps.auditoria.models import AuditoriaCambio
from apps.escuelas.models import Escuela
from apps.operativos.models import Operativo, OperativoAlumno
from apps.usuarios.models import Rol, Usuario


class AuditoriaCambiosTest(APITestCase):
    fixtures = ["roles", "users"]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        call_command("seed_permissions", verbosity=0)

    def setUp(self):
        self.superadmin = Usuario.objects.get(email="superadmin@prosane.test")
        self.client.force_authenticate(user=self.superadmin)

    def _rows(self, **kwargs):
        return AuditoriaCambio.objects.filter(**kwargs)

    # ── Escuelas y cursos ──
    def test_escuela_crud_audita(self):
        res = self.client.post("/api/v1/escuelas/",
                               {"nombre": "Escuela Audit", "cue": "AUD001"}, format="json")
        self.assertEqual(res.status_code, 201)
        escuela_id = res.data["id"]
        row = self._rows(entidad="escuela", accion="crear").first()
        self.assertIsNotNone(row)
        self.assertEqual(row.actor, self.superadmin)
        self.assertEqual(str(row.entidad_id), escuela_id)
        self.assertEqual(row.detalle["nombre"], "Escuela Audit")
        self.assertIsNotNone(row.ip)

        res = self.client.patch(f"/api/v1/escuelas/{escuela_id}/",
                                {"nombre": "Escuela Audit 2"}, format="json")
        self.assertEqual(res.status_code, 200)
        row = self._rows(entidad="escuela", accion="editar").first()
        self.assertIn("nombre", row.detalle["campos"])

        res = self.client.delete(f"/api/v1/escuelas/{escuela_id}/")
        self.assertEqual(res.status_code, 204)
        self.assertTrue(self._rows(entidad="escuela", accion="desactivar").exists())

    def test_no_audita_delete_escuela_rechazado(self):
        escuela = Escuela.objects.create(nombre="Con Op", cue="AUD002")
        Operativo.objects.create(escuela=escuela, fecha="2026-06-20")
        res = self.client.delete(f"/api/v1/escuelas/{escuela.id}/")
        self.assertEqual(res.status_code, 409)
        self.assertFalse(self._rows(entidad="escuela").exists())

    def test_curso_crud_audita(self):
        escuela = Escuela.objects.create(nombre="EC", cue="AUD003")
        res = self.client.post(f"/api/v1/escuelas/{escuela.id}/cursos/", {
            "nivel": "primario", "sala_grado_anio": "1°",
            "division": "A", "ciclo_lectivo": 2026,
        }, format="json")
        self.assertEqual(res.status_code, 201)
        curso_id = res.data["id"]
        self.assertTrue(self._rows(entidad="curso", accion="crear").exists())

        res = self.client.patch(
            f"/api/v1/escuelas/{escuela.id}/cursos/{curso_id}/",
            {"division": "B"}, format="json")
        self.assertEqual(res.status_code, 200)
        row = self._rows(entidad="curso", accion="editar").first()
        self.assertIn("division", row.detalle["campos"])

        res = self.client.delete(f"/api/v1/escuelas/{escuela.id}/cursos/{curso_id}/")
        self.assertEqual(res.status_code, 204)
        self.assertTrue(self._rows(entidad="curso", accion="eliminar").exists())

    # ── Operativos ──
    def _crear_operativo(self):
        escuela = Escuela.objects.create(nombre="EO", cue="AUD004")
        res = self.client.post("/api/v1/operativos/", {
            "nombre": "Op Audit", "escuela": str(escuela.id), "fecha": "2026-06-20",
        }, format="json")
        self.assertEqual(res.status_code, 201)
        return res.data["id"]

    def test_operativo_crud_y_transiciones_auditan(self):
        op_id = self._crear_operativo()
        self.assertTrue(self._rows(entidad="operativo", accion="crear").exists())

        res = self.client.patch(f"/api/v1/operativos/{op_id}/",
                                {"nombre": "Op Audit 2"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(self._rows(entidad="operativo", accion="editar").exists())

        from apps.operativos import services
        from apps.usuarios.models import Usuario as U
        medico = U.objects.create_user(email="med_op@test.com", password="x")
        medico.roles.add(Rol.objects.get(rol="medico"))
        services.asignar_profesional(op_id, medico.id, "medico")
        OperativoAlumno.objects.create(
            operativo_id=op_id, apellido="A", nombre="B", dni="40111225")
        res = self.client.post(f"/api/v1/operativos/{op_id}/confirmar/")
        self.assertEqual(res.status_code, 200)
        row = self._rows(entidad="operativo", accion="cambiar_estado").first()
        self.assertEqual(row.detalle["de"], Operativo.BORRADOR)
        self.assertEqual(row.detalle["a"], Operativo.CONFIRMADO)

        res = self.client.delete(f"/api/v1/operativos/{op_id}/")
        self.assertEqual(res.status_code, 204)
        row = self._rows(entidad="operativo", accion="cambiar_estado").first()
        self.assertEqual(row.detalle["a"], Operativo.CANCELADO)

    def test_alumno_crud_audita(self):
        op_id = self._crear_operativo()
        res = self.client.post(f"/api/v1/operativos/{op_id}/alumnos/", {
            "apellido": "Pérez", "nombre": "Ana", "dni": "30111222",
            "tipo_dni": "DNI", "sexo": "femenino",
        }, format="json")
        self.assertEqual(res.status_code, 201)
        alumno_id = res.data["id"]
        row = self._rows(entidad="alumno_operativo", accion="crear").first()
        self.assertEqual(row.detalle["dni"], "30111222")

        res = self.client.patch(
            f"/api/v1/operativos/{op_id}/alumnos/{alumno_id}/",
            {"estado": "presente"}, format="json")
        self.assertEqual(res.status_code, 200)
        row = self._rows(entidad="alumno_operativo", accion="editar").first()
        self.assertEqual(row.detalle["estado_de"], "pendiente")
        self.assertEqual(row.detalle["estado_a"], "presente")

        res = self.client.delete(f"/api/v1/operativos/{op_id}/alumnos/{alumno_id}/")
        self.assertEqual(res.status_code, 204)
        self.assertTrue(
            self._rows(entidad="alumno_operativo", accion="eliminar").exists())

    def test_import_csv_una_sola_fila(self):
        op_id = self._crear_operativo()
        csv = ("dni,apellido,nombre,tipo_dni,fecha_nacimiento,sexo,grado,division\n"
               "40111222,García,Luis,DNI,,,1,A\n")
        archivo = SimpleUploadedFile("nomina.csv", csv.encode("utf-8"),
                                     content_type="text/csv")
        res = self.client.post(f"/api/v1/operativos/{op_id}/alumnos/importar-csv/",
                               {"archivo": archivo}, format="multipart")
        self.assertEqual(res.status_code, 200)
        rows = self._rows(entidad="alumno_operativo", accion="importar")
        self.assertEqual(rows.count(), 1)
        self.assertEqual(rows.first().detalle["creados"], 1)
        self.assertEqual(rows.first().detalle["archivo"], "nomina.csv")

    def test_evaluaciones_crear_y_editar_auditan(self):
        from apps.operativos import services
        escuela = Escuela.objects.create(nombre="EM", cue="AUD005")
        op = Operativo.objects.create(escuela=escuela, fecha="2026-06-20",
                                      created_by=self.superadmin)
        alumno = OperativoAlumno.objects.create(
            operativo=op, apellido="A", nombre="B", dni="40111223")
        medico = Usuario.objects.get(email="medico@prosane.test")
        services.asignar_profesional(op.id, medico.id, "medico")
        services.confirmar_operativo(op.id)
        services.iniciar_operativo(op.id)
        self.client.force_authenticate(user=medico)

        url = f"/api/v1/operativos/{op.id}/alumnos/{alumno.id}/evaluacion-medica/"
        res = self.client.put(url, {"peso": 30}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(
            self._rows(entidad="evaluacion_medica", accion="crear").exists())
        res = self.client.put(url, {"peso": 31}, format="json")
        self.assertEqual(res.status_code, 200)
        row = self._rows(entidad="evaluacion_medica", accion="editar").first()
        self.assertIn("peso", row.detalle["campos"])

    def test_seccion_escuela_y_datos_auditan(self):
        op_id = self._crear_operativo()
        alumno = OperativoAlumno.objects.create(
            operativo_id=op_id, apellido="A", nombre="B", dni="40111224")
        res = self.client.patch(
            f"/api/v1/operativos/{op_id}/alumnos/{alumno.id}/seccion-escuela/",
            {"escuela_preocupa_salud": True}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(
            self._rows(entidad="seccion_escuela", accion="editar").exists())

        res = self.client.patch(
            f"/api/v1/operativos/{op_id}/alumnos/{alumno.id}/datos/",
            {"apellido": "A2"}, format="json")
        self.assertEqual(res.status_code, 200)
        row = self._rows(entidad="datos_alumno", accion="editar").first()
        self.assertIn("apellido", row.detalle["campos"])
        self.assertEqual(row.detalle["paciente"], "creado")

    # ── Pacientes y tutores ──
    def _usuario_escuela(self, escuela):
        user = Usuario.objects.create_user(email="esc_audit@test.com", password="x")
        user.roles.add(Rol.objects.get(rol="escuela"))
        user.escuela = escuela
        user.save()
        return user

    def test_paciente_alta_tutor_y_antecedentes_auditan(self):
        escuela = Escuela.objects.create(nombre="EP", cue="AUD006")
        self.client.force_authenticate(user=self._usuario_escuela(escuela))
        persona = {"nombre": "Ana", "apellido": "Paz", "dni": "50111222",
                   "tipo_dni": "DNI", "sexo": "femenino", "fecha_nacimiento": "2018-01-01"}
        res = self.client.post("/api/v1/alumnos/", {
            "persona": persona, "edad": 8,
            "tutor": {"persona": {**persona, "dni": "30111223", "nombre": "Mamá"},
                      "parentesco": "madre"},
        }, format="json")
        self.assertEqual(res.status_code, 201)
        paciente_id = res.data["id"]
        row = self._rows(entidad="paciente", accion="crear").first()
        self.assertEqual(row.detalle["dni"], "50111222")

        res = self.client.patch(f"/api/v1/alumnos/{paciente_id}/antecedentes/",
                                {"diabetes": "SI"}, format="json")
        self.assertEqual(res.status_code, 200)
        row = self._rows(entidad="antecedente", accion="editar").first()
        self.assertIn("diabetes", row.detalle["campos"])
        # Sin valores clínicos en el detalle
        self.assertNotIn("SI", str(row.detalle.values()))

    def test_tutor_registro_flujo_audita_sin_actor(self):
        # Registro público: sin autenticar → actor null.
        self.client.force_authenticate(user=None)
        res = self.client.post("/api/v1/auth/register/tutor/", {
            "email": "tutor_audit@test.com", "password": "Clave1234",
            "persona": {"nombre": "Tomás", "apellido": "Tutor", "dni": "25111222",
                        "tipo_dni": "DNI", "sexo": "masculino",
                        "fecha_nacimiento": "1990-01-01"},
            "parentesco": "padre",
        }, format="json")
        self.assertEqual(res.status_code, 201)
        row = self._rows(entidad="tutor", accion="crear").first()
        self.assertIsNotNone(row)
        self.assertIsNone(row.actor)
        self.assertEqual(row.detalle["email"], "tutor_audit@test.com")

        from apps.tutores.models import Tutor
        from apps.usuarios.models import Usuario as U
        tutor = Tutor.objects.get(usuario__email="tutor_audit@test.com")
        usuario = U.objects.get(email="tutor_audit@test.com")
        self.client.force_authenticate(user=usuario)

        res = self.client.post(f"/api/v1/tutores/{tutor.id}/consentimiento/", {},
                               format="json")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(self._rows(entidad="tutor", accion="editar").exists())

        res = self.client.post(f"/api/v1/tutores/{tutor.id}/hijos/", {
            "persona": {"nombre": "Hijo", "apellido": "Tutor", "dni": "60111222",
                        "tipo_dni": "DNI", "sexo": "masculino",
                        "fecha_nacimiento": "2020-01-01"},
            "domicilio": {"localidad": "Salta"},
            "edad": 6,
        }, format="json")
        self.assertEqual(res.status_code, 201)
        row = self._rows(entidad="paciente", accion="crear",
                         detalle__dni="60111222").first()
        self.assertIsNotNone(row)
        self.assertEqual(row.detalle["origen"], "tutor-hijo")
        self.assertEqual(row.actor, usuario)

    # ── Profesionales ──
    def test_profesional_crud_audita(self):
        res = self.client.post("/api/v1/profesionales/", {
            "email": "prof_audit@test.com", "rol": "medico", "matricula": "M-999",
        }, format="json")
        self.assertEqual(res.status_code, 201)
        prof_id = res.data["id"]
        row = self._rows(entidad="profesional_cuenta", accion="crear").first()
        self.assertEqual(row.detalle["email"], "prof_audit@test.com")

        res = self.client.patch(f"/api/v1/profesionales/{prof_id}/",
                                {"matricula": "M-999"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(
            self._rows(entidad="profesional_cuenta", accion="editar").exists())

        res = self.client.delete(f"/api/v1/profesionales/{prof_id}/")
        self.assertEqual(res.status_code, 204)
        self.assertTrue(
            self._rows(entidad="profesional_cuenta", accion="desactivar").exists())

    # ── Endpoint de consulta ──
    def test_endpoint_solo_superadmin_con_filtros(self):
        escuela = Escuela.objects.create(nombre="EQ", cue="AUD007")
        self.client.post("/api/v1/escuelas/", {"nombre": "EQ2"}, format="json")

        res = self.client.get("/api/v1/auditoria/cambios/")
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(len(res.data), 1)
        self.assertIn("actor_email", res.data[0])

        res = self.client.get("/api/v1/auditoria/cambios/?entidad=escuela&accion=crear")
        self.assertTrue(all(r["entidad"] == "escuela" and r["accion"] == "crear"
                            for r in res.data))
        res = self.client.get("/api/v1/auditoria/cambios/?actor=superadmin@prosane.test")
        self.assertGreaterEqual(len(res.data), 1)
        res = self.client.get("/api/v1/auditoria/cambios/?limit=1")
        self.assertEqual(len(res.data), 1)

    def test_endpoint_rango_fechas_invertido_da_400(self):
        res = self.client.get(
            "/api/v1/auditoria/cambios/?desde=2026-10-07&hasta=2026-10-01")
        self.assertEqual(res.status_code, 400)

        medico = Usuario.objects.get(email="medico@prosane.test")
        self.client.force_authenticate(user=medico)
        res = self.client.get("/api/v1/auditoria/cambios/")
        self.assertEqual(res.status_code, 403)

        self.client.force_authenticate(user=None)
        res = self.client.get("/api/v1/auditoria/cambios/")
        self.assertEqual(res.status_code, 401)
