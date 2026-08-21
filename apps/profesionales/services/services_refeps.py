from django.conf import settings


MATRICULAS_MOCK = {
    "541012497922": {
        "nombre": "Estela Rosa",
        "apellido": "Acevedo",
        "dni": "12497922",
        "sexo": "female",
        "fecha_nacimiento": "1956-10-18",
        "profesion": "Médico",
    },
    "123456789": {
        "nombre": "Carlos",
        "apellido": "López",
        "dni": "30123456",
        "sexo": "male",
        "fecha_nacimiento": "1980-05-22",
        "profesion": "Odontólogo",
    },
}


class RefepsService:
    @classmethod
    def consultar(cls, matricula: str) -> dict | None:
        """Consulta REFEPS por matrícula.

        Returns:
            dict con los datos del profesional, o None si la matrícula no existe.

        Raises:
            RefepsError: si el servicio REFEPS no está disponible (caído).
        """
        if getattr(settings, "REFEPS_MOCK", False):
            return MATRICULAS_MOCK.get(matricula)
        try:
            return cls._consultar_real(matricula)
        except RefepsError:
            raise
        except Exception:
            raise RefepsError("Servicio REFEPS no disponible")

    @classmethod
    def _consultar_real(cls, matricula: str) -> dict | None:
        raise NotImplementedError("API REFEPS real no implementada")


class RefepsError(Exception):
    pass
