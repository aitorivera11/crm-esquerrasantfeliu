from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, FormView, ListView, TemplateView, UpdateView

from core.mixins import AdminRequiredMixin

from .forms import (
    CampanyaPasswordChangeForm,
    PerfilForm,
    UsuariAdminCreateForm,
    UsuariAdminPasswordForm,
    UsuariAdminUpdateForm,
)
from .models import Usuari


class PerfilView(LoginRequiredMixin, UpdateView):
    form_class = PerfilForm
    template_name = 'usuaris/perfil.html'
    success_url = reverse_lazy('usuaris:perfil')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, 'Les dades del teu perfil s\'han actualitzat correctament.')
        return super().form_valid(form)


class CanviPasswordView(LoginRequiredMixin, FormView):
    form_class = CampanyaPasswordChangeForm
    template_name = 'usuaris/canvi_password.html'
    success_url = reverse_lazy('usuaris:canvi_password')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        user = form.save()
        update_session_auth_hash(self.request, user)
        messages.success(self.request, 'La contrasenya s\'ha canviat correctament.')
        return super().form_valid(form)


class UsuariListView(AdminRequiredMixin, ListView):
    model = Usuari
    template_name = 'usuaris/admin/usuari_list.html'
    context_object_name = 'usuaris'
    paginate_by = 20

    def get_queryset(self):
        queryset = Usuari.objects.order_by('nom_complet', 'username')
        q = self.request.GET.get('q', '').strip()
        rol = self.request.GET.get('rol', '').strip()
        if q:
            queryset = queryset.filter(
                Q(nom_complet__icontains=q)
                | Q(username__icontains=q)
                | Q(email__icontains=q)
                | Q(telefon__icontains=q)
            )
        if rol:
            queryset = queryset.filter(rol=rol)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '').strip()
        context['rol'] = self.request.GET.get('rol', '').strip()
        context['rols'] = Usuari.Rol.choices
        return context


class UsuariCreateView(AdminRequiredMixin, CreateView):
    model = Usuari
    form_class = UsuariAdminCreateForm
    template_name = 'usuaris/admin/usuari_form.html'
    success_url = reverse_lazy('usuaris:admin_usuari_list')

    def form_valid(self, form):
        messages.success(self.request, 'Usuari creat correctament.')
        return super().form_valid(form)


class UsuariUpdateView(AdminRequiredMixin, UpdateView):
    model = Usuari
    form_class = UsuariAdminUpdateForm
    template_name = 'usuaris/admin/usuari_form.html'
    success_url = reverse_lazy('usuaris:admin_usuari_list')

    def form_valid(self, form):
        messages.success(self.request, 'Usuari actualitzat correctament.')
        return super().form_valid(form)


class UsuariPasswordUpdateView(AdminRequiredMixin, FormView):
    template_name = 'usuaris/admin/usuari_password.html'
    form_class = UsuariAdminPasswordForm
    success_url = reverse_lazy('usuaris:admin_usuari_list')

    def dispatch(self, request, *args, **kwargs):
        self.target_user = Usuari.objects.get(pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.target_user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['target_user'] = self.target_user
        return context

    def form_valid(self, form):
        form.save()
        messages.success(self.request, f'Contrasenya actualitzada per a {self.target_user}.')
        return super().form_valid(form)


class UsuariDeleteView(AdminRequiredMixin, DeleteView):
    model = Usuari
    template_name = 'usuaris/admin/usuari_confirm_delete.html'
    success_url = reverse_lazy('usuaris:admin_usuari_list')

    def form_valid(self, form):
        messages.success(self.request, 'Usuari eliminat correctament.')
        return super().form_valid(form)


class UsuariToggleActiveView(AdminRequiredMixin, TemplateView):
    def post(self, request, *args, **kwargs):
        user = Usuari.objects.get(pk=kwargs['pk'])
        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])
        messages.success(request, f"L'estat de {user} s'ha actualitzat.")
        return redirect('usuaris:admin_usuari_list')
