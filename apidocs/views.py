from django.shortcuts import render


def inicio(request):
    return render(request, 'apidocs/inicio.html', {'active': 'inicio'})


def autenticacion(request):
    return render(request, 'apidocs/autenticacion.html', {'active': 'autenticacion'})


def auth_register(request):
    return render(request, 'apidocs/auth_register.html', {'active': 'auth_register'})


def auth_register_tutor(request):
    return render(request, 'apidocs/auth_register_tutor.html', {'active': 'auth_register_tutor'})


def auth_register_profesional(request):
    return render(request, 'apidocs/auth_register_profesional.html', {'active': 'auth_register_profesional'})


def auth_login(request):
    return render(request, 'apidocs/auth_login.html', {'active': 'auth_login'})


def auth_asignar_rol(request):
    return render(request, 'apidocs/auth_asignar_rol.html', {'active': 'auth_asignar_rol'})


def pacientes_list(request):
    return render(request, 'apidocs/pacientes_list.html', {'active': 'pacientes_list'})


def pacientes_create(request):
    return render(request, 'apidocs/pacientes_create.html', {'active': 'pacientes_create'})


def pacientes_detail(request):
    return render(request, 'apidocs/pacientes_detail.html', {'active': 'pacientes_detail'})


def pacientes_update(request):
    return render(request, 'apidocs/pacientes_update.html', {'active': 'pacientes_update'})


def pacientes_delete(request):
    return render(request, 'apidocs/pacientes_delete.html', {'active': 'pacientes_delete'})


def antecedentes_familiares(request):
    return render(request, 'apidocs/antecedentes_familiares.html', {'active': 'antecedentes_familiares'})


def antecedentes_familiares_put(request):
    return render(request, 'apidocs/antecedentes_familiares_put.html', {'active': 'antecedentes_familiares_put'})


def antecedentes_personales(request):
    return render(request, 'apidocs/antecedentes_personales.html', {'active': 'antecedentes_personales'})


def antecedentes_personales_put(request):
    return render(request, 'apidocs/antecedentes_personales_put.html', {'active': 'antecedentes_personales_put'})


def responsable_perfil(request):
    return render(request, 'apidocs/responsable_perfil.html', {'active': 'responsable_perfil'})


def responsable_perfil_put(request):
    return render(request, 'apidocs/responsable_perfil_put.html', {'active': 'responsable_perfil_put'})


def profesionales_perfil(request):
    return render(request, 'apidocs/profesionales_perfil.html', {'active': 'profesionales_perfil'})


def profesionales_perfil_put(request):
    return render(request, 'apidocs/profesionales_perfil_put.html', {'active': 'profesionales_perfil_put'})


def profesionales_validar_matricula(request):
    return render(request, 'apidocs/profesionales_validar_matricula.html', {'active': 'profesionales_validar_matricula'})


def profesionales_buscar_paciente(request):
    return render(request, 'apidocs/profesionales_buscar_paciente.html', {'active': 'profesionales_buscar_paciente'})
