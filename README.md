# andolini-ig

Sistema de carrosséis automáticos para Instagram da Andolini Labs.

## Estrutura

- `content/posts.json`: banco com 30 posts.
- `generate.py`: gera os JPEGs em `output/post_XX/slide_XX.jpg`.
- `publish.py`: publica o próximo post pendente via Composio.
- `state/published.json`: controle do que já foi publicado.
- `.github/workflows/publish.yml`: agenda de segunda a sexta, 08:12 de Brasilia.

## Setup local

1. Crie uma conta Instagram Business ou Creator conectada a uma pagina do Facebook.
2. Conecte o Instagram na Composio.
3. Instale dependencias:

```bash
pip install -r requirements.txt
```

4. Copie `.env.example` para `.env` e preencha:

```bash
COMPOSIO_API_KEY=
COMPOSIO_USER_ID=
IG_USER_ID=
IMAGE_BASE_URL=https://raw.githubusercontent.com/guilhermeQA7/andolini-ig/main/output
PUBLISH_START_DATE=
```

`PUBLISH_START_DATE` é opcional. Use `YYYY-MM-DD` para impedir publicações antes de uma data, por exemplo `2026-10-01`.

5. Gere as imagens:

```bash
python generate.py
```

Para gerar posts específicos:

```bash
python generate.py 3 7
```

## Testes com Composio

Confira a conta conectada:

```bash
python publish.py --whoami
```

Inspecione os schemas das ferramentas:

```bash
python publish.py --inspect
```

Veja o próximo post sem publicar:

```bash
python publish.py --dry-run
```

Se quiser testar uma data de inicio localmente:

```bash
PUBLISH_START_DATE=2026-10-01 python publish.py
```

Publique um post especifico em modo teste:

```bash
python publish.py --id 3 --dry-run
```

## GitHub Actions

1. Publique este repositorio como publico. O Instagram precisa acessar as imagens em `output`.
2. Gere e commite a pasta `output`.
3. Cadastre os secrets:

- `COMPOSIO_API_KEY`
- `COMPOSIO_USER_ID`
- `IG_USER_ID`

4. Opcional: em `Settings > Secrets and variables > Actions > Variables`, crie:

- `PUBLISH_START_DATE`: data de inicio no formato `YYYY-MM-DD`

5. Rode o workflow manualmente em `Actions > Publish Instagram Carousel`.
6. Para testar um post especifico, use o input `post_id`.

Depois de publicar, o workflow atualiza `state/published.json` e faz commit automático.

## Rotina de crescimento

Reserve 20 minutos por dia:

- Responder os CTAs por DM com diagnóstico leve do processo e convite para uma call quando fizer sentido.
- Comentar em perfis locais de Bangu/RJ e negócios complementares.
- Fazer Stories manualmente nos fins de semana com caixinha de perguntas.

Toda semana, transforme o carrossel mais salvo em 1 Reels curto.

Todo mês, revise salvamentos e compartilhamentos para decidir quais temas repetir, aprofundar ou transformar em oferta.
