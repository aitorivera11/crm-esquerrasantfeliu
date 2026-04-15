from django.contrib import messages
from django.forms import inlineformset_factory
from django.db import transaction
from django.db.models import F, Q
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, FormView, ListView, TemplateView, UpdateView

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
from .services import lookup_product_by_barcode, parse_purchase_document


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
                'ultims_items': ItemMaterial.objects.select_related('ubicacio_actual').order_by('-creat_el')[:5],
                'ultims_stocks': StockMaterial.objects.select_related('ubicacio').order_by('-creat_el')[:5],
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

    LiniesFormset = inlineformset_factory(
        CompraMaterial,
        LiniaCompraMaterial,
        form=LiniaCompraMaterialForm,
        extra=0,
        can_delete=True,
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['linies_formset'] = kwargs.get('linies_formset') or self.LiniesFormset(
            self.request.POST if self.request.method == 'POST' else None,
            self.request.FILES if self.request.method == 'POST' else None,
            instance=getattr(self, 'object', None) or CompraMaterial(),
            prefix='linies',
        )
        context['linia_form_buida'] = context['linies_formset'].empty_form
        return context

    def _build_analyze_payload(self, request):
        parsed = parse_purchase_document(request.FILES.get('document_analisi'))

        payload = request.POST.copy()
        detected_fields = parsed.get('fields', {})
        for field_name in ['proveidor', 'num_factura_ticket', 'cost_total', 'data_compra']:
            current_value = (payload.get(field_name) or '').strip()
            detected_value = detected_fields.get(field_name)
            if current_value or not detected_value:
                continue
            if field_name == 'data_compra':
                payload[field_name] = detected_value.strftime('%Y-%m-%d')
            else:
                payload[field_name] = str(detected_value)

        lines = parsed.get('lines', [])
        total_forms = int(payload.get('linies-TOTAL_FORMS', 0) or 0)
        for index, line in enumerate(lines, start=total_forms):
            payload[f'linies-{index}-tipus_linia'] = (
                line.get('tipus_linia') or LiniaCompraMaterial.TipusLinia.CONSUMIBLE
            )
            payload[f'linies-{index}-descripcio'] = line.get('descripcio') or 'Línia detectada automàticament'
            payload[f'linies-{index}-quantitat'] = str(line.get('quantitat') or 1)
            payload[f'linies-{index}-preu_unitari'] = str(line.get('preu_unitari') or 0)
            payload[f'linies-{index}-iva_percent'] = str(line.get('iva_percent') or 21)
            payload[f'linies-{index}-total_linia'] = str(line.get('total_linia') or 0)
        if lines:
            payload['linies-TOTAL_FORMS'] = str(total_forms + len(lines))

        return payload, parsed

    def _sync_linea_material(self, compra, linia):
        ubicacio = UbicacioMaterial.objects.filter(activa=True).order_by('id').first()
        if not ubicacio:
            messages.warning(
                self.request,
                'No hi ha cap ubicació activa: no s’ha pogut registrar l’entrada automàtica de material.',
            )
            return

        if linia.tipus_linia == LiniaCompraMaterial.TipusLinia.INVENTARIABLE:
            if getattr(linia, 'stock_generat', None):
                linia.stock_generat.delete()

            item, _ = ItemMaterial.objects.get_or_create(
                linia_compra=linia,
                defaults={
                    'codi_intern': f'CMP-{compra.id:05d}-{linia.id:05d}',
                    'descripcio': linia.descripcio,
                    'categoria': linia.categoria,
                    'ubicacio_actual': ubicacio,
                    'data_alta': compra.data_compra,
                    'valor_estimad': linia.preu_unitari,
                    'codi_barres': linia.codi_barres,
                    'quantitat_actual': linia.quantitat,
                },
            )
            updated = []
            for field_name, value in [
                ('descripcio', linia.descripcio),
                ('categoria', linia.categoria),
                ('data_alta', compra.data_compra),
                ('valor_estimad', linia.preu_unitari),
                ('codi_barres', linia.codi_barres),
                ('quantitat_actual', linia.quantitat),
            ]:
                if getattr(item, field_name) != value:
                    setattr(item, field_name, value)
                    updated.append(field_name)
            if updated:
                item.save(update_fields=[*updated, 'actualitzat_el'])

            MovimentMaterial.objects.create(
                tipus_moviment=MovimentMaterial.Tipus.ENTRADA,
                desti=ubicacio,
                quantitat=linia.quantitat,
                item=item,
                actor=self.request.user,
                observacions=f'Entrada automàtica des de compra #{linia.compra_id}.',
            )
            return

        if getattr(linia, 'item_generat', None):
            linia.item_generat.delete()
        stock, _ = StockMaterial.objects.get_or_create(
            linia_compra=linia,
            defaults={
                'producte': linia.descripcio,
                'categoria': linia.categoria,
                'ubicacio': ubicacio,
                'quantitat_actual': linia.quantitat,
                'unitat': 'u',
                'llindar_minim': 0,
                'codi_barres': linia.codi_barres or '',
            },
        )
        updated = []
        for field_name, value in [
            ('producte', linia.descripcio),
            ('categoria', linia.categoria),
            ('codi_barres', linia.codi_barres or ''),
            ('quantitat_actual', linia.quantitat),
        ]:
            if getattr(stock, field_name) != value:
                setattr(stock, field_name, value)
                updated.append(field_name)
        if updated:
            stock.save(update_fields=[*updated, 'actualitzat_el'])
        MovimentMaterial.objects.create(
            tipus_moviment=MovimentMaterial.Tipus.ENTRADA,
            desti=ubicacio,
            quantitat=linia.quantitat,
            stock=stock,
            actor=self.request.user,
            observacions=f'Entrada automàtica des de compra #{linia.compra_id}.',
        )

    def _remove_linea_material(self, linia):
        if getattr(linia, 'item_generat', None):
            linia.item_generat.delete()
        if getattr(linia, 'stock_generat', None):
            linia.stock_generat.delete()

    def post(self, request, *args, **kwargs):
        self.object = None
        if 'analitzar_document' in request.POST:
            payload, parsed = self._build_analyze_payload(request)
            form = self.get_form_class()(payload, request.FILES)
            linies_formset = self.LiniesFormset(payload, request.FILES, instance=CompraMaterial(), prefix='linies')

            for warning in parsed.get('warnings', []):
                messages.warning(request, warning)
            if parsed.get('lines'):
                messages.success(
                    request,
                    f"S'han detectat {len(parsed['lines'])} línies automàtiques. Revisa-les abans de desar.",
                )
            if parsed.get('fields'):
                messages.success(request, 'S’han emplenat camps suggerits de capçalera. Revisa’ls abans de desar.')

            context = self.get_context_data(form=form, linies_formset=linies_formset)
            return self.render_to_response(context)
        return super().post(request, *args, **kwargs)

    @transaction.atomic
    def form_valid(self, form):
        context = self.get_context_data(form=form)
        linies_formset = context['linies_formset']
        if not linies_formset.is_valid():
            return self.form_invalid(form)

        self.object = form.save()
        linies = linies_formset.save(commit=False)
        for linia in linies:
            linia.compra = self.object
            linia.save()
        for to_delete in linies_formset.deleted_objects:
            to_delete.delete()
        for linia in linies:
            self._sync_linea_material(self.object, linia)
        messages.success(self.request, 'Compra i línies creades correctament.')
        return HttpResponseRedirect(self.get_success_url())


class CompraMaterialUpdateView(MaterialPermissionMixin, UpdateView):
    model = CompraMaterial
    form_class = CompraMaterialForm
    template_name = 'material/compra_form.html'
    success_url = reverse_lazy('material:compra_list')

    LiniesFormset = CompraMaterialCreateView.LiniesFormset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['linies_formset'] = kwargs.get('linies_formset') or self.LiniesFormset(
            self.request.POST if self.request.method == 'POST' else None,
            self.request.FILES if self.request.method == 'POST' else None,
            instance=self.object,
            prefix='linies',
        )
        context['linia_form_buida'] = context['linies_formset'].empty_form
        context['linies_existents'] = self.object.linies.all()
        return context

    def _build_analyze_payload(self, request):
        parsed = parse_purchase_document(request.FILES.get('document_analisi'))

        payload = request.POST.copy()
        detected_fields = parsed.get('fields', {})
        for field_name in ['proveidor', 'num_factura_ticket', 'cost_total', 'data_compra']:
            current_value = (payload.get(field_name) or '').strip()
            detected_value = detected_fields.get(field_name)
            if current_value or not detected_value:
                continue
            if field_name == 'data_compra':
                payload[field_name] = detected_value.strftime('%Y-%m-%d')
            else:
                payload[field_name] = str(detected_value)

        lines = parsed.get('lines', [])
        total_forms = int(payload.get('linies-TOTAL_FORMS', 0) or 0)
        for index, line in enumerate(lines, start=total_forms):
            payload[f'linies-{index}-tipus_linia'] = (
                line.get('tipus_linia') or LiniaCompraMaterial.TipusLinia.CONSUMIBLE
            )
            payload[f'linies-{index}-descripcio'] = line.get('descripcio') or 'Línia detectada automàticament'
            payload[f'linies-{index}-quantitat'] = str(line.get('quantitat') or 1)
            payload[f'linies-{index}-preu_unitari'] = str(line.get('preu_unitari') or 0)
            payload[f'linies-{index}-iva_percent'] = str(line.get('iva_percent') or 21)
            payload[f'linies-{index}-total_linia'] = str(line.get('total_linia') or 0)
        if lines:
            payload['linies-TOTAL_FORMS'] = str(total_forms + len(lines))

        return payload, parsed

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if 'analitzar_document' in request.POST:
            payload, parsed = self._build_analyze_payload(request)
            form = self.get_form_class()(payload, request.FILES, instance=self.object)
            linies_formset = self.LiniesFormset(payload, request.FILES, instance=self.object, prefix='linies')

            for warning in parsed.get('warnings', []):
                messages.warning(request, warning)
            if parsed.get('lines'):
                messages.success(
                    request,
                    f"S'han detectat {len(parsed['lines'])} línies automàtiques. Revisa-les abans de desar.",
                )
            if parsed.get('fields'):
                messages.success(request, 'S’han emplenat camps suggerits de capçalera. Revisa’ls abans de desar.')

            context = self.get_context_data(form=form, linies_formset=linies_formset)
            return self.render_to_response(context)
        return super().post(request, *args, **kwargs)

    @transaction.atomic
    def form_valid(self, form):
        context = self.get_context_data(form=form)
        linies_formset = context['linies_formset']
        if linies_formset.is_valid():
            self.object = form.save()
            linies = linies_formset.save(commit=False)
            for linia in linies:
                linia.compra = self.object
                linia.save()
                CompraMaterialCreateView._sync_linea_material(self, self.object, linia)
            for to_delete in linies_formset.deleted_objects:
                CompraMaterialCreateView._remove_linea_material(self, to_delete)
                to_delete.delete()
            messages.success(self.request, 'Compra i línies actualitzades correctament.')
            return HttpResponseRedirect(self.get_success_url())
        return self.form_invalid(form)


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


class ItemMaterialDeleteView(MaterialPermissionMixin, DeleteView):
    model = ItemMaterial
    success_url = reverse_lazy('material:item_list')

    def post(self, request, *args, **kwargs):
        messages.success(self.request, 'Ítem eliminat correctament.')
        return super().post(request, *args, **kwargs)


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


class StockMaterialDeleteView(MaterialPermissionMixin, DeleteView):
    model = StockMaterial
    success_url = reverse_lazy('material:stock_list')

    def post(self, request, *args, **kwargs):
        messages.success(self.request, 'Stock eliminat correctament.')
        return super().post(request, *args, **kwargs)


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
        quantitat = form.cleaned_data['quantitat']
        observacions = form.cleaned_data.get('observacions', '')
        if quantitat == item.quantitat_actual:
            item.ubicacio_actual = desti
            item.save(update_fields=['ubicacio_actual', 'actualitzat_el'])
            item_desti = item
        else:
            item.quantitat_actual = item.quantitat_actual - quantitat
            item.save(update_fields=['quantitat_actual', 'actualitzat_el'])
            split_counter = 1
            split_code = f'{item.codi_intern}-T{split_counter}'
            while ItemMaterial.objects.filter(codi_intern=split_code).exists():
                split_counter += 1
                split_code = f'{item.codi_intern}-T{split_counter}'
            item_desti = ItemMaterial.objects.create(
                codi_intern=split_code,
                descripcio=item.descripcio,
                categoria=item.categoria,
                estat=item.estat,
                ubicacio_actual=desti,
                data_alta=item.data_alta,
                valor_estimad=item.valor_estimad,
                codi_barres=item.codi_barres,
                foto_principal=item.foto_principal,
                quantitat_actual=quantitat,
            )
        MovimentMaterial.objects.create(
            tipus_moviment=MovimentMaterial.Tipus.TRASLLAT,
            origen=origen,
            desti=desti,
            item=item_desti,
            quantitat=quantitat,
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

        existing_codes = ItemMaterial.objects.filter(codi_intern__startswith=f'{prefix}-').values_list('codi_intern', flat=True)
        max_sequence = 0
        for code in existing_codes:
            try:
                seq = int(code.split('-')[-1])
                max_sequence = max(max_sequence, seq)
            except ValueError:
                continue

        codi_intern = f'{prefix}-{max_sequence + 1:04d}'
        item = ItemMaterial.objects.create(
            codi_intern=codi_intern,
            descripcio=descripcio,
            categoria=categoria,
            ubicacio_actual=ubicacio,
            data_alta=data_alta,
            valor_estimad=valor,
            quantitat_actual=quantitat,
        )
        MovimentMaterial.objects.create(
            tipus_moviment=MovimentMaterial.Tipus.ENTRADA,
            desti=ubicacio,
            item=item,
            quantitat=quantitat,
            actor=self.request.user,
            observacions='Alta des d’inventari ràpid.',
        )

        messages.success(self.request, f'S’ha creat un ítem agrupat amb quantitat {quantitat}.')
        return HttpResponseRedirect(self.get_success_url())
