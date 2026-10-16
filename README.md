# Site da Telecasa Negócios Imobiliários

Site estático que substitui o site do Kenlo. Ele é gerado a partir dos imóveis que o gerente aprova no **CRM do Zero2**.

## Como os imóveis chegam ao site

1. O corretor cadastra o imóvel com fotos na aba **Imóveis** do CRM e envia para aprovação.
2. O gerente aprova. O CRM grava, pelo conector GitHub do gerente:
   - `data/imoveis.json`, com os dados públicos dos imóveis aprovados (sem dados do proprietário);
   - `data/fotos/<id>.b64`, uma foto por arquivo (JPEG em data URL).
3. Cada gravação na branch `main` dispara o GitHub Actions (`.github/workflows/pages.yml`), que roda `build.py` e publica o resultado no ramo `gh-pages`, servido pelo GitHub Pages.

Quando o gerente tira um imóvel do site, o CRM regrava `data/imoveis.json` sem ele.

## Arquivos

- `config.json`: nome, telefones, WhatsApp, endereço, horário, CRECI, redes sociais, texto do "Quem somos" e bancos do financiamento. Altere aqui e o site é republicado.
- `build.py`: gera `_site/` (início, lista com filtros, página de cada imóvel, anuncie, encomende, financiamento, quem somos, contato, privacidade, sitemap). Usa só a biblioteca padrão do Python.
- `assets/`: estilo, script (filtros, galeria, formulários que abrem o WhatsApp) e ícone.

## Rodar localmente

```sh
SITE_BASE=/ python3 build.py
python3 -m http.server -d _site 8000
```

## Domínio próprio

Crie um arquivo `CNAME` na raiz com `www.telecasaimobiliaria.com.br`, configure o domínio em Settings › Pages e aponte o DNS no registro.br para o GitHub Pages (CNAME de `www` para `rafaeltrida333.github.io`).
