from django.contrib import admin

from .models import Espaco, Reserva


class ReservaInline(admin.TabularInline):
    model = Reserva
    extra = 0
    readonly_fields = ['valor_total']


@admin.register(Espaco)
class EspacoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'tipo', 'capacidade', 'preco_hora', 'coberto', 'ativo']
    list_filter = ['tipo', 'coberto', 'ativo']
    search_fields = ['nome']
    inlines = [ReservaInline]


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ['id', 'espaco', 'cliente_nome', 'data', 'hora_inicio', 'hora_fim', 'status', 'valor_total']
    list_filter = ['status', 'espaco', 'data']
    search_fields = ['cliente_nome', 'cliente_email']
    readonly_fields = ['valor_total']
