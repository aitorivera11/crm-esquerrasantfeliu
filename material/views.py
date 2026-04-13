from django.contrib import messages
from django.db.models import F, Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from core.mixins import RoleRequiredMixin
from usuaris.models import Usuari

from .forms import (
    AssignacioMaterialForm,
    CategoriaMaterialForm,
    CompraMaterialForm,
    ItemMaterialForm,
    LiniaCompraMaterialForm,
    StockMaterialForm,
    UbicacioMaterialForm,
)
from .models import AssignacioMaterial, CategoriaMaterial, CompraMaterial, ItemMaterial, LiniaCompraMaterial, StockMaterial, UbicacioMaterial


class MaterialPermissionMixin(RoleRequiredMixin):
    allowed_roles = (Usuari.Rol.ADMINISTRACIO, Usuari.Rol.COORDINACIO)


class MaterialDashboardView(MaterialPermissionMixin, TemplateView):
    template_name = 'material/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                'total_items': ItemMaterial.objects.count(),
                'total_stock': StockMaterial.objects.count(),
                'compres_mes': CompraMaterial.objects.order_by('-data_compra')[:5],
                'stocks_critics': StockMaterial.objects.filter(quantitat_actual__lte=F('llindar_minim'))[:10],
                'assignacions_obertes': AssignacioMaterial.objects.exclude(estat_reserva=AssignacioMaterial.EstatReserva.RETORNAT)[:10],
            }
        )
        return context


class CategoriaMaterialListView(MaterialPermissionMixin, ListView):
    model = CategoriaMaterial
    template_name = 'material/categoria_list.html'
    context_object_name = 'categories'


class CategoriaMaterialCreateView(MaterialPermissionMixin, CreateView):
    model = CategoriaMaterial
    form_class = CategoriaMaterialForm
    template_name = 'material/categoria_form.html'
    success_url = reverse_lazy('material:categoria_list')

    def form_valid(self, form):
        messages.success(self.request, 'Categoria creada correctament.')
        return super().form_valid(form)


class CategoriaMaterialUpdateView(MaterialPermissionMixin, UpdateView):
    model = CategoriaMaterial
    form_class = CategoriaMaterialForm
    template_name = 'material/categoria_form.html'
    success_url = reverse_lazy('material:categoria_list')

    def form_valid(self, form):
        messages.success(self.request, 'Categoria actualitzada correctament.')
        return super().form_valid(form)


class UbicacioMaterialListView(MaterialPermissionMixin, ListView):
    model = UbicacioMaterial
    template_name = 'material/ubicacio_list.html'
    context_object_name = 'ubicacions'


class UbicacioMaterialCreateView(MaterialPermissionMixin, CreateView):
    model = UbicacioMaterial
    form_class = UbicacioMaterialForm
    template_name = 'material/ubicacio_form.html'
    success_url = reverse_lazy('material:ubicacio_list')


class UbicacioMaterialUpdateView(MaterialPermissionMixin, UpdateView):
    model = UbicacioMaterial
    form_class = UbicacioMaterialForm
    template_name = 'material/ubicacio_form.html'
    success_url = reverse_lazy('material:ubicacio_list')


class CompraMaterialListView(MaterialPermissionMixin, ListView):
    model = CompraMaterial
    template_name = 'material/compra_list.html'
    context_object_name = 'compres'

    def get_queryset(self):
        queryset = CompraMaterial.objects.select_related('pagador_usuari', 'pagador_entitat').order_by('-data_compra')
        q = self.request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(Q(proveidor__icontains=q) | Q(num_factura_ticket__icontains=q))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '').strip()
        return context


class CompraMaterialCreateView(MaterialPermissionMixin, CreateView):
    model = CompraMaterial
    form_class = CompraMaterialForm
    template_name = 'material/compra_form.html'
    success_url = reverse_lazy('material:compra_list')


class CompraMaterialUpdateView(MaterialPermissionMixin, UpdateView):
    model = CompraMaterial
    form_class = CompraMaterialForm
    template_name = 'material/compra_form.html'
    success_url = reverse_lazy('material:compra_list')


class LiniaCompraMaterialCreateView(MaterialPermissionMixin, CreateView):
    model = LiniaCompraMaterial
    form_class = LiniaCompraMaterialForm
    template_name = 'material/linia_compra_form.html'
    success_url = reverse_lazy('material:compra_list')


class ItemMaterialListView(MaterialPermissionMixin, ListView):
    model = ItemMaterial
    template_name = 'material/item_list.html'
    context_object_name = 'items'


class ItemMaterialCreateView(MaterialPermissionMixin, CreateView):
    model = ItemMaterial
    form_class = ItemMaterialForm
    template_name = 'material/item_form.html'
    success_url = reverse_lazy('material:item_list')


class ItemMaterialUpdateView(MaterialPermissionMixin, UpdateView):
    model = ItemMaterial
    form_class = ItemMaterialForm
    template_name = 'material/item_form.html'
    success_url = reverse_lazy('material:item_list')


class StockMaterialListView(MaterialPermissionMixin, ListView):
    model = StockMaterial
    template_name = 'material/stock_list.html'
    context_object_name = 'stocks'


class StockMaterialCreateView(MaterialPermissionMixin, CreateView):
    model = StockMaterial
    form_class = StockMaterialForm
    template_name = 'material/stock_form.html'
    success_url = reverse_lazy('material:stock_list')


class StockMaterialUpdateView(MaterialPermissionMixin, UpdateView):
    model = StockMaterial
    form_class = StockMaterialForm
    template_name = 'material/stock_form.html'
    success_url = reverse_lazy('material:stock_list')


class AssignacioMaterialListView(MaterialPermissionMixin, ListView):
    model = AssignacioMaterial
    template_name = 'material/assignacio_list.html'
    context_object_name = 'assignacions'


class AssignacioMaterialCreateView(MaterialPermissionMixin, CreateView):
    model = AssignacioMaterial
    form_class = AssignacioMaterialForm
    template_name = 'material/assignacio_form.html'
    success_url = reverse_lazy('material:assignacio_list')


class AssignacioMaterialUpdateView(MaterialPermissionMixin, UpdateView):
    model = AssignacioMaterial
    form_class = AssignacioMaterialForm
    template_name = 'material/assignacio_form.html'
    success_url = reverse_lazy('material:assignacio_list')
