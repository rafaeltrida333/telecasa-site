#!/usr/bin/env python3
"""Gera o site estático da Telecasa em _site/ a partir de data/.

data/imoveis.json   lista de imóveis aprovados (escrita pelo CRM do Zero2)
data/fotos/<id>.b64 cada foto como data URL JPEG (escrita pelo CRM)
config.json         dados da imobiliária (telefones, endereço, textos)

Só usa a biblioteca padrão do Python, para rodar no GitHub Actions sem instalar nada.
"""
import base64
import html
import json
import os
import re
import shutil
import sys
import unicodedata
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "_site")
E = lambda s: html.escape("" if s is None else str(s), quote=True)

CFG = json.load(open(os.path.join(ROOT, "config.json"), encoding="utf-8"))
_cname = os.path.join(ROOT, "CNAME")
DOMAIN = open(_cname).read().strip() if os.path.exists(_cname) else ""
# Sem domínio próprio o GitHub Pages serve em /<repo>/; com CNAME, na raiz.
BASE = os.environ.get("SITE_BASE") or ("/" if DOMAIN else "/" + os.environ.get("REPO_NAME", "telecasa-site") + "/")
SITE_URL = ("https://" + DOMAIN) if DOMAIN else os.environ.get("SITE_URL", "").rstrip("/")


def slug(s):
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "imovel"


def money(v):
    try:
        n = float(v)
    except (TypeError, ValueError):
        return ""
    if n <= 0:
        return ""
    return "R$ " + f"{n:,.0f}".replace(",", ".")


def num(v):
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def m2(v):
    n = num(v)
    if not n:
        return ""
    s = f"{n:,.2f}".rstrip("0").rstrip(".").replace(",", "X").replace(".", ",").replace("X", ".")
    return s + " m²"


def wa(msg):
    from urllib.parse import quote
    return "https://wa.me/" + CFG["whatsapp"] + "?text=" + quote(msg)


def finalidade(i):
    p = str(i.get("pretensao") or "Venda")
    return {"venda": "venda" in p.lower(), "aluguel": "alug" in p.lower()}


def preco(i):
    f = finalidade(i)
    parts = []
    if f["venda"] and money(i.get("valorVenda")):
        parts.append(money(i.get("valorVenda")))
    if f["aluguel"] and money(i.get("valorAluguel")):
        parts.append(money(i.get("valorAluguel")) + "/mês")
    return " · ".join(parts) or "Valor sob consulta"


FOTO_EXT = re.compile(r"https://lh3\.googleusercontent\.com/[A-Za-z0-9_=/.-]{10,400}")


def _read(name):
    p = os.path.join(ROOT, "data", name)
    return json.load(open(p, encoding="utf-8")).get("imoveis", []) if os.path.exists(p) else []


def load_imoveis():
    """Imóveis do CRM (data/imoveis.json) mais os importados do Kenlo (data/kenlo.json).
    Quando o código se repete, vale o do CRM."""
    out, vistos = [], set()
    for i in _read("imoveis.json") + _read("kenlo.json"):
        if not i.get("codigo") or str(i["codigo"]) in vistos:
            continue
        vistos.add(str(i["codigo"]))
        i["slug"] = slug(f'{i.get("tipo","")}-{i.get("bairro","")}-{i["codigo"]}')
        i["fotos"] = [f for f in (i.get("fotos") or []) if re.fullmatch(r"[A-Za-z0-9_-]{1,80}", str(f)) or FOTO_EXT.fullmatch(str(f))]
        out.append(i)
    out.sort(key=lambda i: str(i.get("publicadoEm") or ""), reverse=True)
    out.sort(key=lambda i: not i.get("destaque"))
    return out


def write_fotos(imoveis):
    """Decodifica as fotos .b64 que algum imóvel publicado usa."""
    dst = os.path.join(OUT, "fotos")
    os.makedirs(dst, exist_ok=True)
    have = set()
    for i in imoveis:
        ok = []
        for f in i["fotos"]:
            if f.startswith("https://"):
                ok.append(f)
                continue
            src = os.path.join(ROOT, "data", "fotos", f + ".b64")
            if not os.path.exists(src):
                print("aviso: foto ausente", f, "do imóvel", i["codigo"], file=sys.stderr)
                continue
            if f not in have:
                txt = open(src, encoding="ascii").read().strip()
                m = re.match(r"data:image/(jpeg|png|webp);base64,(.+)$", txt, re.S)
                if not m:
                    print("aviso: foto inválida", f, file=sys.stderr)
                    continue
                with open(os.path.join(dst, f + ".jpg"), "wb") as fh:
                    fh.write(base64.b64decode(m.group(2)))
                have.add(f)
            ok.append(f)
        i["fotos"] = ok


def foto_url(f):
    if f.startswith("https://"):
        return f
    return BASE + "fotos/" + f + ".jpg"


ICON = {
    "wa": '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="currentColor" d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2Zm0 18.2a8.2 8.2 0 0 1-4.2-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2Zm4.5-6.1c-.2-.1-1.5-.7-1.7-.8-.2-.1-.4-.1-.6.1l-.8 1c-.1.2-.3.2-.5.1a6.7 6.7 0 0 1-3.3-2.9c-.3-.4.2-.4.6-1.3.1-.2 0-.3 0-.4l-.8-1.8c-.2-.5-.4-.4-.6-.4h-.5a1 1 0 0 0-.7.3 3 3 0 0 0-.9 2.2 5.2 5.2 0 0 0 1.1 2.7 11.8 11.8 0 0 0 4.5 4c1.7.7 2.3.8 3.2.6.5-.1 1.5-.6 1.7-1.2.2-.6.2-1.1.2-1.2-.1-.1-.2-.2-.5-.3Z"/></svg>',
    "tel": '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2"/></svg>',
}


MENU = [("cadastre-seu-imovel/", "Cadastre seu imóvel"), ("quem-somos/", "Quem somos"), ("corretores/", "Corretores"),
        ("encomende-seu-imovel/", "Encomende seu imóvel"), ("financiamento-e-bancos/", "Financiamento e bancos"), ("fale-conosco/", "Fale conosco")]


def logo_html():
    return f'<a class="logo" href="{BASE}" aria-label="{E(CFG["nome"])}, página inicial"><span class="mark">T</span><span><b>Telecasa</b><small>Imobiliária</small></span></a>'


def links_html(links):
    return "".join(f'<a href="{BASE}{h}">{E(n)}</a>' for h, n in links)


def fcol(title, links):
    items = "".join(f'<li><a href="{BASE}{h}">{E(n)}</a></li>' for h, n in links)
    return f"<div><h2>{E(title)}</h2><ul>{items}</ul></div>"


def layout(title, body, desc="", path="", og_img="", extra_head=""):
    c = CFG
    canon = (SITE_URL + BASE + path) if SITE_URL else ""
    head_meta = f'<meta name="description" content="{E(desc or c["descricao"])}">'
    head_meta += f'<meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc or c["descricao"])}"><meta property="og:type" content="website">'
    if og_img and SITE_URL:
        head_meta += f'<meta property="og:image" content="{E(SITE_URL + og_img)}">'
    if canon:
        head_meta += f'<link rel="canonical" href="{E(canon)}">'
    wa_link = f'https://wa.me/{E(c["whatsapp"])}'
    soc = f'<a href="{E(c["facebook"])}" target="_blank" rel="noopener">Facebook</a><a href="{E(c["instagram"])}" target="_blank" rel="noopener">Instagram</a>'
    redes = fcol("Redes sociais", []).replace("<ul></ul>", f'<ul><li><a href="{E(c["facebook"])}" target="_blank" rel="noopener">Facebook</a></li><li><a href="{E(c["instagram"])}" target="_blank" rel="noopener">Instagram</a></li></ul>')
    return f'''<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
{head_meta}
<link rel="icon" href="{BASE}assets/icon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{BASE}assets/style.css">
{extra_head}
</head>
<body>
<a class="skip" href="#conteudo">Pular para o conteúdo</a>
<div class="topbar"><div class="wrap">
  <nav class="tnav" aria-label="Institucional">{links_html(MENU)}</nav>
  <span class="tsoc"><a href="{wa_link}" target="_blank" rel="noopener">{E(c["fone_whats"])}</a>{soc}</span>
</div></div>
<header class="hd"><div class="wrap">
  <div class="brand">{logo_html()}<span class="slogan">{E(c["slogan"])}</span></div>
  <div class="hcont"><a class="hwa" href="{wa_link}" target="_blank" rel="noopener">{ICON["wa"]}<span><small>Fale Conosco</small>{E(c["fone_whats"])}</span></a>
    <a class="htel" href="tel:+{E(c["fone_fixo_digits"])}">{ICON["tel"]}<span><small>Telefone</small>{E(c["fone_fixo"])}</span></a></div>
  <button class="menu" aria-expanded="false" aria-controls="nav" aria-label="Abrir menu"><span></span></button>
  <nav id="nav" aria-label="Principal">{links_html([("imoveis/a-venda/", "Comprar"), ("imoveis/para-alugar/", "Alugar")] + MENU)}</nav>
</div></header>
<main id="conteudo">
{body}
</main>
<footer class="ft"><div class="wrap">
  <div class="fcols">
    {fcol("Institucional", [("quem-somos/", "Quem somos"), ("corretores/", "Corretores"), ("politica-de-privacidade/", "Política de privacidade")])}
    {fcol("Imóveis", [("cadastre-seu-imovel/", "Cadastre seu imóvel"), ("encomende-seu-imovel/", "Encomende seu imóvel")])}
    {fcol("Serviços", [("financiamento-e-bancos/", "Financiamento e bancos")])}
    {fcol("Contato", [("fale-conosco/", "Fale conosco")])}
    {redes}
  </div>
  <div class="finfo">
    <div>{logo_html()}<p>CRECI: {E(c["creci"])}</p></div>
    <div><p>{E(c["endereco"])}</p><p><a href="{wa_link}" target="_blank" rel="noopener">{E(c["fone_whats"])}</a> · <a href="tel:+{E(c["fone_fixo_digits"])}">{E(c["fone_fixo"])}</a></p></div>
    <div><p><b>Horário de funcionamento</b><br>{E(c["horario"])}</p><p>Para mais informações, entre em contato conosco ou faça-nos uma visita.</p></div>
  </div>
  <p class="copy">© {datetime.now().year} {E(c["nome"])} · CRECI: {E(c["creci"])}</p>
</div></footer>
<a class="wa-float" href="{wa_link}" target="_blank" rel="noopener" aria-label="Contato WhatsApp">{ICON["wa"]}</a>
<script src="{BASE}assets/app.js" defer></script>
</body>
</html>'''


def card(i):
    f = finalidade(i)
    capa = (f'<img src="{foto_url(i["fotos"][0])}" alt="{E(i.get("titulo"))}" loading="lazy" width="640" height="480">'
            if i["fotos"] else '<span class="nofoto">Sem foto</span>')
    spec = []
    if num(i.get("quartos")):
        spec.append(f'{int(num(i["quartos"]))} quarto{"s" if num(i["quartos"]) > 1 else ""}')
    if num(i.get("vagas")):
        spec.append(f'{int(num(i["vagas"]))} vaga{"s" if num(i["vagas"]) > 1 else ""}')
    area = m2(i.get("areaUtil")) or m2(i.get("areaTotal"))
    if area:
        spec.append(area)
    tag = "Venda e aluguel" if f["venda"] and f["aluguel"] else ("Aluguel" if f["aluguel"] else "Venda")
    data = {
        "p": " ".join(k for k, v in f.items() if v), "tipo": slug(i.get("tipo")),
        "q": slug(" ".join(str(i.get(k) or "") for k in ("codigo", "titulo", "tipo", "bairro", "cidade", "empreendimento"))),
        "quartos": int(num(i.get("quartos")) or 0),
        "valor": int(num(i.get("valorVenda")) or 0), "aluguel": int(num(i.get("valorAluguel")) or 0),
    }
    attrs = " ".join(f'data-{k}="{E(v)}"' for k, v in data.items())
    return f'''<article class="card" {attrs}><a href="{BASE}imovel/{i["slug"]}/">
  <div class="ph">{capa}<span class="tag">{tag}</span></div>
  <div class="cb"><div class="loc">{E(i.get("tipo"))} · {E(i.get("bairro"))}{", " + E(i.get("cidade")) if i.get("cidade") else ""}</div>
  <h3>{E(i.get("titulo"))}</h3>
  <div class="price">{E(preco(i))}</div>
  {f'<div class="spec">{" · ".join(E(s) for s in spec)}</div>' if spec else ""}
  <div class="cod">Código {E(i["codigo"])}</div></div></a></article>'''


def busca_form(tipos):
    opts = "".join(f'<option value="{slug(t)}">{E(t)}</option>' for t in tipos)
    return f'''<form class="busca" action="{BASE}imoveis/" method="get" role="search">
  <label class="fld"><span>Buscar por pretensão</span><select name="p"><option value="venda">Comprar</option><option value="aluguel">Alugar</option></select></label>
  <label class="fld"><span>Buscar por tipo</span><select name="tipo"><option value="">Tipo imóvel</option>{opts}</select></label>
  <label class="fld grow"><span>Onde</span><input name="q" placeholder="Digite condomínio, região, bairro ou cidade"></label>
  <button class="btn pri" type="submit">Encontrar imóvel</button>
  <div class="bxtra"><a href="{BASE}imoveis/">Mais filtros</a><button type="button" class="lnk" data-cod>Busca por código</button><a href="https://wa.me/{E(CFG["whatsapp"])}" target="_blank" rel="noopener">Contato WhatsApp</a></div>
</form>'''


TIPOS_BASE = ["Apartamento", "Apartamento duplex", "Casa", "Casa em condomínio", "Terreno", "Lote em condomínio", "Área", "Sala comercial", "Loja", "Galpão", "Chácara", "Sítio", "Fazenda"]
CATS = [("para-alugar", "apartamento", "Apartamentos para alugar"), ("a-venda", "apartamento", "Apartamentos à venda"), ("a-venda", "area", "Áreas à venda"),
        ("para-alugar", "apartamento-duplex", "Apartamentos duplex para alugar"), ("a-venda", "apartamento-duplex", "Apartamentos duplex à venda"),
        ("para-alugar", "casa", "Casas para alugar"), ("a-venda", "casa", "Casas à venda"), ("para-alugar", "terreno", "Terrenos para alugar"),
        ("a-venda", "terreno", "Terrenos à venda"), ("para-alugar", "galpao", "Galpões para alugar"), ("a-venda", "galpao", "Galpões à venda"), ("a-venda", "chacara", "Chácaras à venda")]
PRET = {"a-venda": ("venda", "à venda"), "para-alugar": ("aluguel", "para alugar")}


def page_home(imoveis):
    tipos = sorted({i.get("tipo") for i in imoveis if i.get("tipo")} | set(TIPOS_BASE), key=lambda t: (t not in TIPOS_BASE, TIPOS_BASE.index(t) if t in TIPOS_BASE else 0, t))
    dest = imoveis[:9]
    grid = ("".join(card(i) for i in dest)) if dest else '<p class="empty">Os imóveis aprovados aparecem aqui assim que forem publicados.</p>'
    c = CFG
    cats = "".join(f'<a href="{BASE}imoveis/{p}/{t}/">{E(n)}</a>' for p, t, n in CATS)
    bairros = "".join(f'<a href="{BASE}imoveis/uberaba/{slug(b)}/">{E(b)}</a>' for b in c["bairros"])
    body = f'''<section class="hero"><div class="wrap">
  <h1>{E(c["hero_titulo"])}</h1>
  <p>{E(c["hero_sub"])}</p>
  {busca_form(tipos)}
</div></section>
<section class="sec"><div class="wrap cta3">
  <a class="cta" href="{BASE}encomende-seu-imovel/"><h3>Imóvel sob encomenda</h3><p>Descreva o imóvel que você procura e nós avisaremos quando encontrarmos.</p><span>Encomende seu imóvel →</span></a>
  <a class="cta" href="{BASE}financiamento-e-bancos/"><h3>Financiamento</h3><p>As melhores ofertas de crédito para você financiar seu imóvel.</p><span>Faça uma simulação →</span></a>
  <a class="cta" href="{BASE}cadastre-seu-imovel/"><h3>Cadastre seu imóvel</h3><p>Anuncie conosco! Nós encontraremos o melhor negócio para você.</p><span>Cadastre seu imóvel →</span></a>
</div></section>
<section class="sec alt"><div class="wrap">
  <div class="sh"><h2>Imóveis em destaque</h2><a href="{BASE}imoveis/">Ver todos os imóveis</a></div>
  <div class="grid">{grid}</div>
</div></section>
<section class="sec"><div class="wrap">
  <h2 class="h2">Descubra outras possibilidades de imóveis</h2>
  <div class="links">{cats}</div>
</div></section>
<section class="sec alt"><div class="wrap">
  <div class="sh"><h2>Bairros mais populares</h2><span class="car-nav"><button type="button" class="nvb" data-car="-1" aria-label="Anterior">‹</button><button type="button" class="nvb" data-car="1" aria-label="Próximo">›</button></span></div>
  <div class="carousel" id="bairros">{bairros}</div>
</div></section>
<section class="sec"><div class="wrap news">
  <h2>Acompanhe-nos :)</h2><p>Siga a Telecasa nas redes sociais e veja os imóveis novos primeiro.</p>
  <p><a class="btn" href="{E(c["instagram"])}" target="_blank" rel="noopener">Instagram</a> <a class="btn" href="{E(c["facebook"])}" target="_blank" rel="noopener">Facebook</a></p>
</div></section>'''
    return layout(f'{c["nome"]} | {c["slogan"]}', body, path="")


def page_lista(imoveis, titulo="Imóveis", path="imoveis/", preset=None):
    preset = preset or {}
    tipos = sorted({i.get("tipo") for i in imoveis if i.get("tipo")} | ({preset["tipo_nome"]} if preset.get("tipo_nome") else set()))
    grid = "".join(card(i) for i in imoveis)
    topts = "".join(f'<option value="{slug(t)}">{E(t)}</option>' for t in tipos)
    pre = E(json.dumps({k: v for k, v in preset.items() if k in ("p", "tipo", "q")}))
    body = f'''<section class="sec"><div class="wrap">
  <h1 class="pt">{E(titulo)}</h1>
  <form class="filtros" id="filtros" role="search" onsubmit="return false" data-preset="{pre}">
    <div class="seg" role="radiogroup" aria-label="Pretensão"><label><input type="radio" name="p" value=""><span>Todos</span></label><label><input type="radio" name="p" value="venda"><span>Comprar</span></label><label><input type="radio" name="p" value="aluguel"><span>Alugar</span></label></div>
    <label class="fld"><span>Tipo</span><select name="tipo"><option value="">Todos</option>{topts}</select></label>
    <label class="fld grow"><span>Condomínio, região, bairro, cidade ou código</span><input name="q" type="search"></label>
    <label class="fld"><span>Quartos</span><select name="quartos"><option value="0">Qualquer</option><option value="1">1 ou mais</option><option value="2">2 ou mais</option><option value="3">3 ou mais</option><option value="4">4 ou mais</option></select></label>
    <label class="fld"><span>Valor até</span><input name="max" inputmode="numeric" placeholder="R$"></label>
  </form>
  <p class="count" id="count" aria-live="polite">{len(imoveis)} imóve{"l" if len(imoveis) == 1 else "is"}</p>
  <div class="grid" id="lista">{grid}</div>
  <p class="empty" id="vazio" {"hidden" if imoveis else ""}>Nenhum imóvel encontrado com esses filtros. <a href="{BASE}encomende-seu-imovel/">Encomende seu imóvel</a> e nós avisaremos quando encontrarmos.</p>
</div></section>'''
    return layout(f'{titulo} em {CFG["cidade"]} | {CFG["nome"]}', body, path=path)


def page_imovel(i):
    c = CFG
    fotos = i["fotos"]
    gal = ""
    if fotos:
        thumbs = "".join(f'<button type="button" class="th" data-i="{k}" aria-label="Ver foto {k+1}"><img src="{foto_url(f)}" alt="" loading="lazy"></button>' for k, f in enumerate(fotos))
        gal = f'''<div class="gal" data-n="{len(fotos)}">
  <div class="main"><img id="gmain" src="{foto_url(fotos[0])}" alt="{E(i.get("titulo"))}, foto 1 de {len(fotos)}" width="1200" height="900">
  {'<button type="button" class="nv prev" aria-label="Foto anterior">‹</button><button type="button" class="nv next" aria-label="Próxima foto">›</button>' if len(fotos) > 1 else ''}<span class="gc" id="gc">1 / {len(fotos)}</span></div>
  {f'<div class="thumbs">{thumbs}</div>' if len(fotos) > 1 else ''}
  <script type="application/json" id="gdata">{json.dumps([foto_url(f) for f in fotos])}</script>
</div>'''
    specs = [("Quartos", num(i.get("quartos")) and int(num(i["quartos"]))), ("Suítes", num(i.get("suites")) and int(num(i["suites"]))),
             ("Banheiros", num(i.get("banheiros")) and int(num(i["banheiros"]))), ("Vagas", num(i.get("vagas")) and int(num(i["vagas"]))),
             ("Área construída", m2(i.get("areaUtil"))), ("Área do terreno", m2(i.get("areaTotal"))), ("Andar", i.get("andar") and f'{i["andar"]}º')]
    specs = [(k, v) for k, v in specs if v]
    custos = [("Condomínio", money(i.get("condominio")) and money(i["condominio"]) + "/mês"), ("IPTU", money(i.get("iptu")) and money(i["iptu"]) + "/ano")]
    custos = [(k, v) for k, v in custos if v]
    car = [x.strip() for x in str(i.get("caracteristicas") or "").split(",") if x.strip()]
    end = ", ".join(x for x in [i.get("empreendimento"), i.get("rua") and (i["rua"] + (", " + i["numero"] if i.get("numero") else "")), i.get("bairro"), i.get("cidade")] if x)
    msg = f'Olá! Tenho interesse no imóvel {i["codigo"]} ({i.get("titulo")}) que vi no site.'
    desc_txt = str(i.get("descricao") or "")
    body = f'''<section class="sec im"><div class="wrap">
  <nav class="crumb" aria-label="Você está em"><a href="{BASE}">Início</a> › <a href="{BASE}imoveis/">Imóveis</a> › {E(i["codigo"])}</nav>
  <div class="imh"><div><div class="loc">{E(i.get("tipo"))} · {E(i.get("pretensao"))}</div><h1>{E(i.get("titulo"))}</h1><p class="addr">{E(end)}</p></div>
    <div class="pbox"><div class="price big">{E(preco(i))}</div>{'<div class="neg">Aceita negociação</div>' if i.get("aceitaNegociacao") else ''}<div class="cod">Código {E(i["codigo"])}</div></div></div>
  {gal}
  <div class="imb">
    <div>
      {f'<ul class="specs">{"".join(f"<li><span>{E(k)}</span><b>{E(v)}</b></li>" for k, v in specs)}</ul>' if specs else ''}
      {f'<h2>Sobre o imóvel</h2><div class="desc">{E(desc_txt)}</div>' if desc_txt else ''}
      {f'<h2>Características</h2><ul class="feat">{"".join(f"<li>{E(x)}</li>" for x in car)}</ul>' if car else ''}
      {f'<h2>Custos mensais e anuais</h2><ul class="specs">{"".join(f"<li><span>{E(k)}</span><b>{E(v)}</b></li>" for k, v in custos)}</ul>' if custos else ''}
    </div>
    <aside class="contact"><h2>Gostou deste imóvel?</h2><p>Fale com a Telecasa e agende uma visita.</p>
      <a class="btn pri wide" href="{E(wa(msg))}" target="_blank" rel="noopener">{ICON["wa"]} Chamar no WhatsApp</a>
      <a class="btn wide" href="tel:+{E(c["fone_fixo_digits"])}">{ICON["tel"]} Ligar {E(c["fone_fixo"])}</a>
      {f'<p class="small">Corretor responsável: {E(i.get("corretor"))}</p>' if i.get("corretor") else ''}
      <p class="small">CRECI {E(c["creci"])}</p></aside>
  </div>
</div></section>'''
    d = (desc_txt[:150] + "…") if len(desc_txt) > 150 else desc_txt
    return layout(f'{i.get("titulo")} | {i["codigo"]} | {c["nome"]}', body, desc=d or f'{i.get("tipo")} em {i.get("bairro")}, {i.get("cidade")}. {preco(i)}.',
                  path=f'imovel/{i["slug"]}/', og_img=foto_url(fotos[0]) if fotos and not fotos[0].startswith("https://") else "")


def form_page(title, intro, campos, assunto, path):
    rows = []
    for name, label, kind, extra in campos:
        req = " required" if extra.get("req") else ""
        lab = E(label) + (" *" if req else "")
        if kind == "textarea":
            rows.append(f'<label class="fld full"><span>{lab}</span><textarea name="{name}" rows="4"{req}></textarea></label>')
        elif kind == "select":
            rows.append(f'<label class="fld"><span>{lab}</span><select name="{name}"{req}>{"".join(f"<option>{E(o)}</option>" for o in extra["opts"])}</select></label>')
        else:
            rows.append(f'<label class="fld"><span>{lab}</span><input name="{name}" type="{kind}"{req}{" inputmode=numeric" if extra.get("num") else ""}></label>')
    body = f'''<section class="sec"><div class="wrap narrow">
  <h1 class="pt">{E(title)}</h1><p class="lead">{E(intro)}</p>
  <form class="wform" data-assunto="{E(assunto)}" data-wa="{E(CFG["whatsapp"])}">{"".join(rows)}
    <button class="btn pri" type="submit">{ICON["wa"]} Enviar pelo WhatsApp</button>
    <p class="small">Ao enviar, abrimos o WhatsApp com a mensagem pronta para você confirmar.</p>
  </form>
</div></section>'''
    return layout(f'{title} | {CFG["nome"]}', body, path=path)


TIPOS_FORM = TIPOS_BASE + ["Outro"]


def static_pages():
    c = CFG
    pages = {}
    pages["cadastre-seu-imovel"] = form_page("Anuncie seu imóvel", "Quer vender ou alugar? Mande os dados do imóvel e um corretor da Telecasa entra em contato para avaliar e fotografar.", [
        ("Nome", "Seu nome", "text", {"req": 1}), ("Telefone", "Telefone", "tel", {"req": 1}), ("E-mail", "E-mail", "email", {}),
        ("Finalidade", "Finalidade", "select", {"opts": ["Vender", "Alugar", "Vender ou alugar"]}), ("Tipo", "Tipo de imóvel", "select", {"opts": TIPOS_FORM}),
        ("Endereço", "Endereço com CEP", "text", {"req": 1}), ("Área construída", "Área construída (m²)", "text", {"num": 1}),
        ("Valor pretendido", "Valor pretendido", "text", {}), ("Descrição", "Conte sobre o imóvel", "textarea", {})], "Quero anunciar meu imóvel", "cadastre-seu-imovel/")
    pages["encomende-seu-imovel"] = form_page("Encomende seu imóvel", "Não encontrou o imóvel ideal? Diga o que você procura e a Telecasa busca para você.", [
        ("Nome", "Seu nome", "text", {"req": 1}), ("Telefone", "Telefone", "tel", {"req": 1}),
        ("Finalidade", "Quero", "select", {"opts": ["Comprar", "Alugar"]}), ("Tipo", "Tipo de imóvel", "select", {"opts": TIPOS_FORM}),
        ("Bairros", "Bairros de interesse", "text", {}), ("Quartos", "Quartos", "text", {"num": 1}), ("Valor máximo", "Valor máximo", "text", {}),
        ("Detalhes", "O que é importante para você", "textarea", {})], "Encomenda de imóvel", "encomende-seu-imovel/")
    pages["fale-conosco"] = form_page("Fale conosco", f'{c["endereco"]} · {c["horario"]}. Telefone {c["fone_fixo"]} e WhatsApp {c["fone_whats"]}.', [
        ("Nome", "Seu nome", "text", {"req": 1}), ("Telefone", "Telefone", "tel", {"req": 1}), ("Mensagem", "Mensagem", "textarea", {"req": 1})], "Contato pelo site", "fale-conosco/")
    pages["fale-conosco"] = pages["fale-conosco"].replace('</form>', '</form><div class="map"><iframe title="Mapa da Telecasa" loading="lazy" src="https://www.google.com/maps?q=' + E(c["endereco"]).replace(" ", "+") + '&output=embed"></iframe></div>', 1)
    bancos = "".join(f'<li><a class="btn" href="{E(u)}" target="_blank" rel="noopener">{E(n)}</a></li>' for n, u in c["bancos"])
    pages["financiamento-e-bancos"] = layout(f'Financiamento e bancos | {c["nome"]}', f'''<section class="sec"><div class="wrap narrow">
  <h1 class="pt">Financiamento e bancos</h1><p class="lead">Escolha um banco e faça a sua simulação. Se precisar de ajuda, nossa equipe acompanha todo o processo.</p>
  <ul class="bancos">{bancos}</ul>
  <p><a class="btn pri" href="{E(wa("Olá! Quero ajuda com financiamento imobiliário."))}" target="_blank" rel="noopener">{ICON["wa"]} Falar sobre financiamento</a></p>
</div></section>''', path="financiamento-e-bancos/")
    pages["quem-somos"] = layout(f'Quem somos | {c["nome"]}', f'''<section class="sec"><div class="wrap narrow">
  <h1 class="pt">Quem somos</h1>{"".join(f"<p class=lead>{E(p)}</p>" if k == 0 else f"<p>{E(p)}</p>" for k, p in enumerate(c["quem_somos"]))}
  <p><a class="btn pri" href="{BASE}fale-conosco/">Fale com a gente</a></p>
</div></section>''', path="quem-somos/")
    pages["politica-de-privacidade"] = layout(f'Política de privacidade | {c["nome"]}', f'''<section class="sec"><div class="wrap narrow">
  <h1 class="pt">Política de privacidade</h1>
  <p>Este site não usa cadastro, não guarda dados pessoais e não usa cookies de rastreamento. Os formulários apenas abrem o WhatsApp com a mensagem que você escreveu; nada é enviado antes de você confirmar no aplicativo.</p>
  <p>Os dados que você nos enviar pelo WhatsApp ou telefone são usados só para o atendimento sobre imóveis, conforme a Lei Geral de Proteção de Dados (Lei 13.709/2018). Para pedir a exclusão dos seus dados, fale com a gente pelos contatos do rodapé.</p>
</div></section>''', path="politica-de-privacidade/")
    pages["corretores"] = layout(f'Corretores | {c["nome"]}', f'''<section class="sec"><div class="wrap narrow">
  <h1 class="pt">Corretores</h1><p class="lead">Nossa equipe de corretores está pronta para encontrar o imóvel certo para você, com segurança em todas as etapas da negociação.</p>
  <p><a class="btn pri" href="{E(wa("Olá! Quero falar com um corretor da Telecasa."))}" target="_blank" rel="noopener">{ICON["wa"]} Falar com um corretor</a> <a class="btn" href="tel:+{E(c["fone_fixo_digits"])}">{ICON["tel"]} {E(c["fone_fixo"])}</a></p>
</div></section>''', path="corretores/")
    return pages


def write(rel, content):
    p = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(content)


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    shutil.copytree(os.path.join(ROOT, "assets"), os.path.join(OUT, "assets"))
    imoveis = load_imoveis()
    write_fotos(imoveis)
    write("index.html", page_home(imoveis))
    write("imoveis/index.html", page_lista(imoveis))
    listas = []
    tipos = {slug(t): t for t in TIPOS_BASE + [i.get("tipo") for i in imoveis if i.get("tipo")]}
    for pp, (p, txt) in PRET.items():
        sel = [i for i in imoveis if finalidade(i)[p]]
        listas.append((f"imoveis/{pp}/", page_lista(sel, f"Imóveis {txt}", f"imoveis/{pp}/", {"p": p})))
        for ts, tn in tipos.items():
            st = [i for i in sel if slug(i.get("tipo")) == ts]
            if st or (pp, ts) in {(a, b) for a, b, _ in CATS}:
                listas.append((f"imoveis/{pp}/{ts}/", page_lista(st, f"{tn} {txt}", f"imoveis/{pp}/{ts}/", {"p": p, "tipo": ts, "tipo_nome": tn})))
    for b in sorted(set(CFG["bairros"]) | {i.get("bairro") for i in imoveis if i.get("bairro")}):
        sb = [i for i in imoveis if slug(i.get("bairro")) == slug(b)]
        listas.append((f"imoveis/uberaba/{slug(b)}/", page_lista(sb, f"Imóveis no bairro {b}", f"imoveis/uberaba/{slug(b)}/", {"q": b})))
    for path, content in listas:
        write(path + "index.html", content)
    for i in imoveis:
        write(f'imovel/{i["slug"]}/index.html', page_imovel(i))
    for name, content in static_pages().items():
        write(f"{name}/index.html", content)
    write("404.html", layout(f'Página não encontrada | {CFG["nome"]}', f'<section class="sec"><div class="wrap narrow"><h1 class="pt">Página não encontrada</h1><p class="lead">Este imóvel pode ter sido vendido ou alugado.</p><p><a class="btn pri" href="{BASE}imoveis/">Ver imóveis disponíveis</a></p></div></section>'))
    if DOMAIN:
        write("CNAME", DOMAIN + "\n")
    write(".nojekyll", "")
    urls = ["", "imoveis/", "cadastre-seu-imovel/", "encomende-seu-imovel/", "financiamento-e-bancos/", "quem-somos/", "corretores/", "fale-conosco/"] + [p for p, _ in listas] + [f'imovel/{i["slug"]}/' for i in imoveis]
    if SITE_URL:
        today = datetime.now(timezone.utc).date().isoformat()
        write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
              + "".join(f"<url><loc>{E(SITE_URL + BASE + u)}</loc><lastmod>{today}</lastmod></url>" for u in urls) + "</urlset>\n")
        write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}{BASE}sitemap.xml\n")
    print(f"site gerado em _site/ com {len(imoveis)} imóveis (base {BASE})")


if __name__ == "__main__":
    main()
