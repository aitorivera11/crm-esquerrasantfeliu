from django import forms


class SearchableSelectMultiple(forms.SelectMultiple):
    template_name = "widgets/searchable_select_multiple.html"

    def __init__(self, attrs=None, search_placeholder='Cerca per nom…', empty_text='No hi ha opcions disponibles.', **kwargs):
        attrs = attrs or {}
        attrs.setdefault('data-searchable-multiselect-select', 'true')
        attrs.setdefault('size', 10)
        super().__init__(attrs=attrs, **kwargs)
        self.search_placeholder = search_placeholder
        self.empty_text = empty_text

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        widget = context['widget']
        widget['search_placeholder'] = self.search_placeholder
        widget['empty_text'] = self.empty_text
        widget['summary_text'] = 'Cap element seleccionat'
        help_text_id = widget['attrs'].get('aria-describedby')
        if help_text_id:
            widget['attrs']['aria-describedby'] = f"{help_text_id} {widget['attrs'].get('id', name)}_search_help"
        else:
            widget['attrs']['aria-describedby'] = f"{widget['attrs'].get('id', name)}_search_help"
        return context
