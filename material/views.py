from django.contrib import messages
from django.db import transaction
from django.db.models import F, Q
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, FormView, ListView, TemplateView, UpdateView

from core.mixins import RoleRequiredMixin
from usuaris.models import Usuari

from .forms import (
    AssignacioMaterialForm,
    CategoriaMaterialForm,
    CompraMaterialForm,
    InventariRapidForm,
    ItemMaterialForm,
    LiniaCompraMaterialForm,
    StockMaterialForm,
    TrasllatRapidForm,
    UbicacioMaterialForm,
)
from .models import AssignacioMaterial, CategoriaMaterial, CompraMaterial, ItemMaterial, LiniaCompraMaterial, MovimentMaterial, StockMaterial, UbicacioMaterial
from .services import lookup_product_by_barcode


class MaterialPermissionMixin(RoleRequiredMixin):
    allowed_roles = (Usuari.Rol.ADMINISTRACIO, Usuari.Rol.COORDINACIO)




class BarcodeLookupView(MaterialPermissionMixin, View):
    def get(self, request, *args, **kwargs):
        upc = request.GET.get('upc', '').strip()
        if not upc:
            return JsonResponse({'ok': False, 'error': 'Cal indicar un codi UPC/EAN.'}, status=400)

        try:
            result = lookup_product_by_barcode(upc)
        except Exception:
            return JsonResponse({'ok': False, 'error': 'Servei UPCitemdb no disponible ara mateix.'}, status=503)

        if not result:
            return JsonResponse({'ok': False, 'error': "No s'ha trobat cap producte amb aquest codi."}, status=404)
        return JsonResponse({'ok': True, 'item': result})

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


class ItemMaterialDetailView(MaterialPermissionMixin, DetailView):
    model = ItemMaterial
    template_name = 'material/item_detail.html'
    context_object_name = 'item'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['moviments'] = self.object.moviments.select_related('actor', 'origen', 'desti').all()[:20]
        return context


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


class TrasllatRapidView(MaterialPermissionMixin, FormView):
    template_name = 'material/trasllat_form.html'
    form_class = TrasllatRapidForm
    success_url = reverse_lazy('material:item_list')

    @transaction.atomic
    def form_valid(self, form):
        item = form.cleaned_data['item']
        origen = item.ubicacio_actual
        desti = form.cleaned_data['desti']
        observacions = form.cleaned_data.get('observacions', '')
        item.ubicacio_actual = desti
        item.save(update_fields=['ubicacio_actual', 'actualitzat_el'])
        MovimentMaterial.objects.create(
            tipus_moviment=MovimentMaterial.Tipus.TRASLLAT,
            origen=origen,
            desti=desti,
            item=item,
            actor=self.request.user,
            observacions=observacions,
        )
        messages.success(self.request, 'Trasllat registrat correctament.')
        return super().form_valid(form)


class InventariRapidCreateView(MaterialPermissionMixin, FormView):
    template_name = 'material/inventari_rapid_form.html'
    form_class = InventariRapidForm
    success_url = reverse_lazy('material:item_list')

    @transaction.atomic
    def form_valid(self, form):
        prefix = form.cleaned_data['prefix_codi'].upper().strip()
        descripcio = form.cleaned_data['descripcio']
        categoria = form.cleaned_data['categoria']
        ubicacio = form.cleaned_data['ubicacio_actual']
        quantitat = form.cleaned_data['quantitat']
        data_alta = form.cleaned_data['data_alta']
        valor = form.cleaned_data['valor_estimad']

        existing_codes = (
            ItemMaterial.objects.filter(codi_intern__startswith=f'{prefix}-')
            .values_list('codi_intern', flat=True)
        )
        max_sequence = 0
        for code in existing_codes:
            try:
                seq = int(code.split('-')[-1])
                max_sequence = max(max_sequence, seq)
            except ValueError:
                continue

        created = 0
        for offset in range(1, quantitat + 1):
            sequence = max_sequence + offset
            codi_intern = f'{prefix}-{sequence:04d}'
            item = ItemMaterial.objects.create(
                codi_intern=codi_intern,
                descripcio=descripcio,
                categoria=categoria,
                ubicacio_actual=ubicacio,
                data_alta=data_alta,
                valor_estimad=valor,
            )
            MovimentMaterial.objects.create(
                tipus_moviment=MovimentMaterial.Tipus.ENTRADA,
                desti=ubicacio,
                item=item,
                actor=self.request.user,
                observacions='Alta múltiple des d’inventari ràpid.',
            )
            created += 1

        messages.success(self.request, f'S’han creat {created} ítems correctament.')
        return HttpResponseRedirect(self.get_success_url())

