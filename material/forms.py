from io import BytesIO

from django import forms
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db.models import Sum
from django.utils.text import slugify

from usuaris.forms import StyledFormMixin

from .models import (
    AssignacioMaterial,
    CategoriaMaterial,
    CompraMaterial,
    ItemMaterial,
    LiniaCompraMaterial,
    StockMaterial,
    UbicacioMaterial,
)

try:
    from PIL import Image
except ImportError:  # pillow is in requirements, this is only a safe guard for local tooling
    Image = None


MAX_UPLOAD_SIZE = 4 * 1024 * 1024


def optimize_uploaded_image(uploaded_file):
    if not uploaded_file:
        return uploaded_file
    if uploaded_file.size > MAX_UPLOAD_SIZE:
        raise forms.ValidationError('La imatge supera el límit de 4MB.')
    if Image is None:
        return uploaded_file

    image = Image.open(uploaded_file)
    image = image.convert('RGB')
    max_size = (1600, 1600)
    image.thumbnail(max_size, Image.Resampling.LANCZOS)

    output = BytesIO()
    image.save(output, format='JPEG', quality=78, optimize=True)
    output.seek(0)

    filename = uploaded_file.name.rsplit('.', 1)[0]
    return InMemoryUploadedFile(
        output,
        field_name=uploaded_file.field_name,
        name=f'{filename}.jpg',
        content_type='image/jpeg',
        size=output.getbuffer().nbytes,
        charset=None,
    )


class CategoriaMaterialForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = CategoriaMaterial
        fields = ['nom', 'pare', 'activa']


class UbicacioMaterialForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = UbicacioMaterial
        fields = ['nom', 'adreca', 'responsable_per_defecte', 'notes', 'activa']
        widgets = {'notes': forms.Textarea(attrs={'rows': 3})}


class CompraMaterialForm(StyledFormMixin, forms.ModelForm):
    document_analisi = forms.FileField(
        required=False,
        label='Importar ticket/factura (PDF o imatge)',
        help_text='Carrega un fitxer per generar suggeriments automàtics de capçalera i línies.',
        widget=forms.ClearableFileInput(attrs={'accept': '.pdf,image/*'}),
    )

    class Meta:
        model = CompraMaterial
        fields = [
            'data_compra',
            'proveidor',
            'pagador_usuari',
            'pagador_entitat',
            'cost_total',
            'metode_pagament',
            'num_factura_ticket',
            'document',
            'observacions',
        ]
        widgets = {
            'data_compra': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'observacions': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['data_compra'].input_formats = ['%Y-%m-%d']


class LiniaCompraMaterialForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = LiniaCompraMaterial
        fields = [
            'compra',
            'categoria',
            'tipus_linia',
            'descripcio',
            'quantitat',
            'preu_unitari',
            'iva_percent',
            'total_linia',
            'codi_barres',
            'foto',
        ]
        widgets = {
            'codi_barres': forms.TextInput(attrs={'data-barcode-target': 'true'}),
            'foto': forms.ClearableFileInput(attrs={'accept': 'image/*', 'capture': 'environment'}),
        }

    def clean_foto(self):
        foto = self.cleaned_data.get('foto')
        return optimize_uploaded_image(foto)


class ItemMaterialForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = ItemMaterial
        fields = [
            'codi_intern',
            'descripcio',
            'categoria',
            'estat',
            'ubicacio_actual',
            'data_alta',
            'valor_estimad',
            'quantitat_actual',
            'codi_barres',
            'foto_principal',
        ]
        widgets = {
            'data_alta': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'codi_barres': forms.TextInput(attrs={'data-barcode-target': 'true'}),
            'foto_principal': forms.ClearableFileInput(attrs={'accept': 'image/*', 'capture': 'environment'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['data_alta'].input_formats = ['%Y-%m-%d']

    def clean_foto_principal(self):
        foto = self.cleaned_data.get('foto_principal')
        foto = optimize_uploaded_image(foto)
        if not foto:
            return foto
        codi_intern = (self.cleaned_data.get('codi_intern') or '').strip()
        if codi_intern:
            extensio = foto.name.rsplit('.', 1)[-1].lower()
            nom_base = slugify(codi_intern) or 'item'
            foto.name = f'{nom_base}.{extensio}'
        return foto


class StockMaterialForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = StockMaterial
        fields = [
            'producte',
            'categoria',
            'ubicacio',
            'quantitat_actual',
            'unitat',
            'llindar_minim',
            'codi_barres',
            'foto_principal',
        ]
        widgets = {
            'codi_barres': forms.TextInput(attrs={'data-barcode-target': 'true'}),
            'foto_principal': forms.ClearableFileInput(attrs={'accept': 'image/*', 'capture': 'environment'}),
        }

    def clean_foto_principal(self):
        foto = self.cleaned_data.get('foto_principal')
        return optimize_uploaded_image(foto)


class AssignacioMaterialForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = AssignacioMaterial
        fields = [
            'acte',
            'tasca',
            'item',
            'stock',
            'quantitat_reservada',
            'quantitat_retornada',
            'estat_reserva',
        ]

    def clean(self):
        cleaned_data = super().clean()
        stock = cleaned_data.get('stock')
        item = cleaned_data.get('item')
        quantitat_reservada = cleaned_data.get('quantitat_reservada') or 0

        if item:
            assignacions_item = item.assignacions.exclude(pk=self.instance.pk).exclude(
                estat_reserva=AssignacioMaterial.EstatReserva.RETORNAT
            )
            if assignacions_item.exists():
                raise forms.ValidationError('Aquest ítem ja està reservat en una altra assignació oberta.')

        if stock and quantitat_reservada > 0:
            reservat = (
                AssignacioMaterial.objects.filter(stock=stock)
                .exclude(pk=self.instance.pk)
                .exclude(estat_reserva=AssignacioMaterial.EstatReserva.RETORNAT)
                .aggregate(total=Sum('quantitat_reservada'))['total']
                or 0
            )
            disponible = stock.quantitat_actual - reservat
            if quantitat_reservada > disponible:
                raise forms.ValidationError(
                    f'No hi ha disponibilitat suficient. Disponible: {disponible} {stock.unitat}.'
                )
        return cleaned_data


class TrasllatRapidForm(StyledFormMixin, forms.Form):
    item = forms.ModelChoiceField(queryset=ItemMaterial.objects.select_related('ubicacio_actual'), label='Ítem')
    desti = forms.ModelChoiceField(queryset=UbicacioMaterial.objects.filter(activa=True), label='Ubicació destí')
    quantitat = forms.DecimalField(min_value=0.01, decimal_places=2, max_digits=12, initial=1)
    observacions = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3}))

    def clean(self):
        cleaned_data = super().clean()
        item = cleaned_data.get('item')
        desti = cleaned_data.get('desti')
        if item and desti and item.ubicacio_actual_id == desti.id:
            raise forms.ValidationError('L’origen i el destí no poden ser la mateixa ubicació.')
        quantitat = cleaned_data.get('quantitat')
        if item and quantitat and quantitat > item.quantitat_actual:
            raise forms.ValidationError(f'La quantitat supera l’existent. Disponible: {item.quantitat_actual}.')
        return cleaned_data


class InventariRapidForm(StyledFormMixin, forms.Form):
    prefix_codi = forms.CharField(max_length=12, initial='INV', help_text='Prefix del codi intern')
    descripcio = forms.CharField(max_length=255)
    categoria = forms.ModelChoiceField(queryset=CategoriaMaterial.objects.filter(activa=True), required=False)
    ubicacio_actual = forms.ModelChoiceField(queryset=UbicacioMaterial.objects.filter(activa=True))
    quantitat = forms.IntegerField(min_value=1, max_value=200, initial=1)
    data_alta = forms.DateField(
        input_formats=['%Y-%m-%d'],
        widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
    )
    valor_estimad = forms.DecimalField(min_value=0, decimal_places=2, max_digits=10, initial=0)
