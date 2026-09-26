# ReservaPlay 🏐

API RESTful para **reserva de quadras e espaços esportivos**, desenvolvida com **Django** e **Django REST Framework (DRF)**.

O sistema permite cadastrar espaços esportivos (quadras, campos, piscinas, ginásios), as modalidades praticadas em cada um e as reservas feitas pelos clientes, com validação de conflitos de horário, horário de funcionamento e cálculo automático do valor da reserva.

---

## Tecnologias

| Pacote | Uso |
|---|---|
| Django 6.1 | Framework web e ORM |
| Django REST Framework | Serializers, ViewSets, roteamento e paginação |
| django-filter | Filtros por query string |
| python-dotenv | Leitura das variáveis do arquivo `.env` |
| SQLite (padrão) / MySQL | Banco de dados relacional |

---

## Modelagem

```
┌──────────────┐        N:N        ┌──────────────────┐        1:N        ┌──────────────────┐
│  Modalidade  │◄─────────────────►│      Espaco      │──────────────────►│     Reserva      │
├──────────────┤  (ManyToMany)     ├──────────────────┤   (ForeignKey)    ├──────────────────┤
│ nome (único) │                   │ nome (único)     │                   │ espaco (FK)      │
│ descricao    │                   │ tipo             │                   │ cliente_nome     │
└──────────────┘                   │ descricao        │                   │ cliente_email    │
                                   │ capacidade       │                   │ cliente_telefone │
                                   │ preco_hora       │                   │ data             │
                                   │ coberto / ativo  │                   │ hora_inicio/fim  │
                                   │ horario_abertura │                   │ status           │
                                   │ horario_fechamento│                  │ observacoes      │
                                   │ modalidades (M2M)│                   │ valor_total      │
                                   └──────────────────┘                   └──────────────────┘
```

- **Espaco → Reserva (1:N)** — `models.ForeignKey(Espaco, on_delete=models.PROTECT, related_name='reservas')`.
  O `PROTECT` impede apagar um espaço que ainda possui reservas; a API responde **400** com uma mensagem explicativa.
- **Espaco ↔ Modalidade (N:N)** — `models.ManyToManyField(Modalidade, related_name='espacos')`.
- `valor_total` é calculado no `save()` da reserva: `preco_hora × duração`.
- Restrições no banco (`CheckConstraint`): `hora_fim > hora_inicio` e `horario_fechamento > horario_abertura`.

### Regras de negócio validadas no `ReservaSerializer`

- Horário de término deve ser posterior ao de início;
- Não é possível reservar em data passada;
- A reserva deve estar dentro do horário de funcionamento do espaço;
- Espaço inativo não aceita reservas;
- Não pode haver **sobreposição de horário** com outra reserva não cancelada do mesmo espaço (reservas canceladas liberam o horário).

---

## Estrutura do projeto

```
ReservaPlay/
├── config/                  # Projeto Django (settings, urls raiz, wsgi/asgi)
├── reservas/                # App do domínio
│   ├── models.py            # Modalidade, Espaco, Reserva
│   ├── serializers.py       # ModelSerializers (leitura aninhada / escrita por ID)
│   ├── views.py             # ModelViewSets + ações extras
│   ├── urls.py              # DefaultRouter
│   ├── filters.py           # FilterSets (django-filter)
│   ├── exceptions.py        # Handler de exceções (400 integridade / 500 JSON)
│   ├── admin.py
│   ├── tests.py             # 30 testes da API
│   └── management/commands/popular_dados.py
├── api.http                 # Requisições prontas para demonstração
├── .env.example
├── requirements.txt
└── manage.py
```

---

## Como executar

### 1. Clonar o repositório

```bash
git clone https://github.com/odairoliv/ReservaPlay.git
cd ReservaPlay
```

### 2. Criar e ativar o ambiente virtual

```bash
python -m venv .venv
```

Windows (PowerShell):

```powershell
.venv\Scripts\Activate.ps1
```

Linux / macOS:

```bash
source .venv/bin/activate
```

### 3. Instalar as dependências

```bash
pip install -r requirements.txt
```

### 4. Configurar as variáveis de ambiente

Copie o arquivo de exemplo e ajuste a `SECRET_KEY`:

```bash
cp .env.example .env
```

Para gerar uma chave nova:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

| Variável | Descrição | Padrão |
|---|---|---|
| `SECRET_KEY` | Chave secreta do Django (**obrigatória**) | — |
| `DEBUG` | Modo de depuração | `False` |
| `ALLOWED_HOSTS` | Hosts permitidos, separados por vírgula | `localhost,127.0.0.1` |
| `DB_ENGINE` | `sqlite` ou `mysql` | `sqlite` |
| `DB_NAME` | Arquivo SQLite ou nome do banco MySQL | `db.sqlite3` |
| `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Credenciais do MySQL | — |

> Para usar MySQL: defina `DB_ENGINE=mysql`, preencha as credenciais, crie o banco e instale o driver com `pip install mysqlclient`.

### 5. Aplicar as migrações

```bash
python manage.py migrate
```

(Ao alterar os models: `python manage.py makemigrations` e depois `python manage.py migrate`.)

### 6. (Opcional) Popular com dados de exemplo

```bash
python manage.py popular_dados
```

Use `--limpar` para apagar os dados existentes antes.

### 7. Iniciar o servidor

```bash
python manage.py runserver
```

A API fica em **http://127.0.0.1:8000/api/** — a interface navegável do DRF permite testar todos os endpoints pelo navegador.

Para acessar o admin, crie um usuário com `python manage.py createsuperuser` e abra http://127.0.0.1:8000/admin/.

### 8. Rodar os testes

```bash
python manage.py test
```

---

## Endpoints

Todos os recursos seguem o mesmo padrão gerado pelo `DefaultRouter`:

| Método | Rota | Descrição | Sucesso |
|---|---|---|---|
| GET | `/api/<recurso>/` | Lista paginada com filtros | 200 |
| GET | `/api/<recurso>/<id>/` | Detalhe com relacionamentos aninhados | 200 |
| POST | `/api/<recurso>/` | Cria um registro | 201 |
| PUT | `/api/<recurso>/<id>/` | Atualização completa | 200 |
| PATCH | `/api/<recurso>/<id>/` | Atualização parcial | 200 |
| DELETE | `/api/<recurso>/<id>/` | Remove o registro | 204 |

Recursos: `espacos`, `reservas` e `modalidades`.

Ações extras:

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/espacos/<id>/disponibilidade/?data=AAAA-MM-DD` | Horários ocupados no dia |
| POST | `/api/reservas/<id>/cancelar/` | Muda o status da reserva para `CANCELADA` |

### Paginação, filtros, busca e ordenação

Paginação por página (10 itens): `?page=2`.

**Espaços** — `/api/espacos/`
- `tipo` (`QUADRA`, `CAMPO`, `PISCINA`, `GINASIO`, `SALAO`), `coberto`, `ativo`
- `modalidade=<id>`, `preco_min`, `preco_max`, `capacidade_min`
- `search=` (nome, descrição) · `ordering=` (`nome`, `preco_hora`, `capacidade`, `criado_em`; prefixo `-` para decrescente)

**Reservas** — `/api/reservas/`
- `espaco=<id>`, `status` (`PENDENTE`, `CONFIRMADA`, `CANCELADA`), `data`
- `data_inicio`, `data_fim` (período), `cliente_email`
- `search=` (cliente, e-mail, nome do espaço) · `ordering=` (`data`, `hora_inicio`, `valor_total`, `criado_em`)

**Modalidades** — `/api/modalidades/` · `search=`, `ordering=nome`

### Serialização dos relacionamentos

Na **leitura** os relacionamentos vêm aninhados; na **escrita** o cliente envia apenas os IDs:

```jsonc
// POST /api/reservas/
{
  "espaco_id": 1,
  "cliente_nome": "Lucas Ferreira",
  "cliente_email": "lucas@email.com",
  "data": "2026-12-01",
  "hora_inicio": "18:00",
  "hora_fim": "19:30"
}

// 201 Created
{
  "id": 6,
  "espaco": {
    "id": 1,
    "nome": "Quadra Poliesportiva Central",
    "tipo": "QUADRA",
    "tipo_display": "Quadra",
    "preco_hora": "90.00",
    "coberto": true
  },
  "cliente_nome": "Lucas Ferreira",
  "cliente_email": "lucas@email.com",
  "cliente_telefone": "",
  "data": "2026-12-01",
  "hora_inicio": "18:00:00",
  "hora_fim": "19:30:00",
  "status": "PENDENTE",
  "status_display": "Pendente",
  "observacoes": "",
  "valor_total": "135.00",
  "criado_em": "...",
  "atualizado_em": "..."
}
```

Para evitar ciclos (espaço → reservas → espaço → ...), os objetos aninhados usam serializers "resumo" (`EspacoResumoSerializer`, `ReservaResumoSerializer`) que não aninham de volta. O detalhe de um espaço (`GET /api/espacos/<id>/`) usa o `EspacoDetalheSerializer`, que inclui as modalidades e a lista resumida de reservas.

### Códigos de status

| Código | Quando |
|---|---|
| 200 OK | GET, PUT, PATCH bem-sucedidos |
| 201 Created | POST bem-sucedido |
| 204 No Content | DELETE bem-sucedido (sem corpo) |
| 400 Bad Request | Payload inválido, regra de negócio violada, conflito de horário ou exclusão bloqueada por integridade referencial |
| 404 Not Found | ID inexistente |
| 500 Internal Server Error | Erro não previsto (resposta JSON padronizada em `reservas/exceptions.py`) |

O arquivo [`api.http`](api.http) contém requisições prontas para cada cenário (extensão *REST Client* do VS Code, ou copie para Postman/Insomnia).
