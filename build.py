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


ICON.update({
    "home": '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M12 3 2 12h3v8h5v-5h4v5h5v-8h3z"/></svg>',
    "mega": '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M3 10v4h3l5 4V6L6 10H3Zm10-3v10c2.5-.6 4-2.6 4-5s-1.5-4.4-4-5Zm6 1-1 1.5c.6.7 1 1.6 1 2.5s-.4 1.8-1 2.5l1 1.5c1-1 2-2.4 2-4s-1-3-2-4Z"/></svg>',
    "users": '<svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true"><path fill="currentColor" d="M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Zm7 0a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM2 19c0-3 3-5 7-5s7 2 7 5v1H2v-1Zm15.5-4.8c2.6.4 4.5 2 4.5 4.3v1.5h-4.5V19c0-1.9-.7-3.6-2-4.8Z"/></svg>',
    "fb": '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M14 8V6.5c0-.7.2-1.2 1.2-1.2H17V2.2A23 23 0 0 0 14.6 2C12.2 2 10.6 3.5 10.6 6.2V8H8v3.4h2.6V22H14V11.4h2.7L17 8h-3Z"/></svg>',
    "ig": '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1" fill="currentColor"/></svg>',
    "lupa": '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.4" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m20 20-4.5-4.5"/></svg>',
    "filtro": '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M3 6h18M6 12h12M10 18h4"/></svg>',
    "seta": '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M3 12h17m-6-6 6 6-6 6"/></svg>',
    "enc": '<svg viewBox="0 0 24 24" width="34" height="34" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M7 3h9l3 3v12H7z"/><path d="M5 6v15h11M10 8h6M10 11h6M10 14h4"/></svg>',
    "din": '<svg viewBox="0 0 24 24" width="34" height="34" aria-hidden="true"><path fill="currentColor" d="M13 2v2.1c2.3.3 4 1.8 4.3 4h-2.8c-.2-1-1.1-1.7-2.5-1.7-1.6 0-2.5.7-2.5 1.7 0 .9.7 1.4 2.9 2l1.1.3c3 .8 4.4 2.1 4.4 4.4 0 2.4-1.8 4-4.9 4.3V22h-2v-2.9c-2.7-.3-4.6-1.9-4.8-4.4h2.8c.2 1.2 1.3 2 3 2s2.8-.8 2.8-1.9c0-.9-.7-1.4-2.6-1.9l-1.3-.3C7.9 11.9 6.7 10.6 6.7 8.6c0-2.3 1.8-4 4.3-4.4V2h2Z"/></svg>',
    "placa": '<svg viewBox="0 0 24 24" width="34" height="34" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M5 2v20M5 5h15M9 5v3M17 5v3M8 8h12v7H8z"/></svg>',
})

MENU = [("cadastre-seu-imovel/", "Cadastre seu imóvel"), ("quem-somos/", "Quem somos"), ("corretores/", "Corretores"),
        ("encomende-seu-imovel/", "Encomende seu imóvel"), ("financiamento-e-bancos/", "Financiamento e bancos"), ("fale-conosco/", "Fale conosco")]


def logo_svg(cls="logo-svg"):
    # Desenho do logo da Telecasa: telhado dourado e chaminé cinza, nome sem a barra do A
    return f'''<svg class="{cls}" viewBox="0 0 220 120" role="img" aria-label="Telecasa Negócios Imobiliários">
<path d="M58 52 92 18l40 40" fill="none" stroke="#b19e6d" stroke-width="11" stroke-linejoin="miter"/>
<path d="M96 11h19l40 40-9 9-37-37h-13z" fill="#3f3f3f"/>
<text x="110" y="92" text-anchor="middle" font-family="Red Hat Display,Manrope,sans-serif" font-size="34" font-weight="400" letter-spacing="1.5" fill="#3f3f3f">TELEC&#923;S&#923;</text>
<text x="110" y="111" text-anchor="middle" font-family="Red Hat Display,Manrope,sans-serif" font-size="11.5" letter-spacing=".8" fill="#b19e6d">Negócios Imobiliários</text>
</svg>'''


def logo_img(key="logo_img", cls="logo-svg"):
    """Logo original (config logo_img); se a imagem não carregar, mostra o desenho em SVG."""
    u = CFG.get(key)
    if not u:
        return logo_svg(cls)
    return (f'<img class="{cls}" src="{E(u)}" alt="Telecasa Negócios Imobiliários" onerror="this.hidden=true;this.nextElementSibling.removeAttribute(&quot;hidden&quot;)">'
            + logo_svg(cls).replace("<svg ", "<svg hidden ", 1))


def logo_html():
    return f'<a class="logo" href="{BASE}" aria-label="{E(CFG["nome"])}, página inicial">{logo_img()}</a>'


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
    redes = f'<a href="{E(c["facebook"])}" target="_blank" rel="noopener">{ICON["fb"]} Facebook</a><a href="{E(c["instagram"])}" target="_blank" rel="noopener">{ICON["ig"]} Instagram</a>'
    return f'''<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
{head_meta}
<link rel="icon" href="{BASE}assets/icon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Red+Hat+Display:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{BASE}assets/style.css">
{extra_head}
</head>
<body>
<a class="skip" href="#conteudo">Pular para o conteúdo</a>
<header class="hd"><div class="hwrap">
  {logo_html()}
  <nav class="hnav" aria-label="Atalhos">
    <a class="hph" href="{wa_link}" target="_blank" rel="noopener">{ICON["tel"]}<span><b>{ICON["wa"]} {E(c["fone_whats"])}</b><small>Fale Conosco</small></span></a>
    <details class="dd"><summary aria-label="Outros telefones"></summary><div><a href="{wa_link}" target="_blank" rel="noopener">{ICON["wa"]} {E(c["fone_whats"])}</a><a href="tel:+{E(c["fone_fixo_digits"])}">{ICON["tel"]} {E(c["fone_fixo"])}</a></div></details>
    <a href="{BASE}cadastre-seu-imovel/">{ICON["home"]}Cadastre seu imóvel</a>
    <a href="{BASE}quem-somos/">{ICON["mega"]}Quem somos</a>
    <details class="dd"><summary>{ICON["users"]}Redes sociais</summary><div>{redes}</div></details>
  </nav>
  <button class="menu" aria-expanded="false" aria-controls="nav" aria-label="Abrir menu"><span></span></button>
  <nav id="nav" aria-label="Principal">{links_html([("", "Início"), ("imoveis/a-venda/", "Comprar"), ("imoveis/para-alugar/", "Alugar")] + MENU)}
    <a href="{wa_link}" target="_blank" rel="noopener">WhatsApp {E(c["fone_whats"])}</a><a href="tel:+{E(c["fone_fixo_digits"])}">Telefone {E(c["fone_fixo"])}</a></nav>
</div></header>
<main id="conteudo">
{body}
</main>
<footer class="ft"><div class="wrap fcols">
    {fcol("Institucional", [("quem-somos/", "Quem somos"), ("corretores/", "Corretores"), ("politica-de-privacidade/", "Política de privacidade")])}
    {fcol("Imóveis", [("cadastre-seu-imovel/", "Cadastre seu imóvel"), ("encomende-seu-imovel/", "Encomende seu imóvel")])}
    {fcol("Serviços", [("financiamento-e-bancos/", "Financiamento e bancos")])}
    {fcol("Contato", [("fale-conosco/", "Fale conosco")])}
</div></footer>
<div class="fbar"><div class="wrap"><span>© {datetime.now().year} {E(c["nome"])} · CRECI: {E(c["creci"])}</span>
  <span class="soc"><a href="{E(c["facebook"])}" target="_blank" rel="noopener" aria-label="Facebook">{ICON["fb"]}</a><a href="{E(c["instagram"])}" target="_blank" rel="noopener" aria-label="Instagram">{ICON["ig"]}</a></span></div></div>
<a class="wa-float" href="{wa_link}" target="_blank" rel="noopener" aria-label="Contato WhatsApp">{ICON["wa"]}</a>
<script src="{BASE}assets/app.js" defer></script>
</body>
</html>'''


def card(i, mini=False):
    f = finalidade(i)
    capa = (f'<img src="{foto_url(i["fotos"][0])}" alt="{E(i.get("titulo"))}" loading="lazy" width="640" height="420">'
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
    loc = " - ".join(x for x in [i.get("bairro"), i.get("cidade") or "Uberaba", "MG"] if x)
    extra = "" if mini else f'''<div class="ct">{E(i.get("tipo"))} · {E(tag)}</div>
  {f'<div class="spec">{" · ".join(E(s) for s in spec)}</div>' if spec else ""}'''
    return f'''<article class="card{" mini" if mini else ""}" {attrs}><a href="{BASE}imovel/{i["slug"]}/">
  <div class="ph">{capa}</div>
  <div class="cb"><div class="loc">{E(loc)}</div>{extra}
  <div class="price">{E(preco(i))}</div>
  {"" if mini else f'<div class="cod">Código {E(i["codigo"])}</div>'}</div></a></article>'''



def busca_form(tipos):
    opts = "".join(f'<option value="{slug(t)}">{E(t)}</option>' for t in tipos)
    return f'''<form class="busca" action="{BASE}imoveis/" method="get" role="search">
  <label class="bf sel"><small>Pretensão</small><select name="p" aria-label="Pretensão"><option value="venda">Comprar</option><option value="aluguel">Alugar</option></select></label>
  <label class="bf sel"><select name="tipo" aria-label="Tipo de imóvel"><option value="">Tipo imóvel</option>{opts}</select></label>
  <label class="bf q">{ICON["lupa"]}<input name="q" aria-label="Onde" placeholder="Digite condomínio, região, bairro ou cidade"></label>
  <a class="pill" href="{BASE}imoveis/">Mais filtros {ICON["filtro"]}</a>
  <button class="btn pri" type="submit">Encontrar imóvel</button>
</form>
<button type="button" class="codb" data-cod>Busca por código</button>'''


TIPOS_BASE = ["Apartamento", "Apartamento duplex", "Casa", "Casa em condomínio", "Terreno", "Lote em condomínio", "Área", "Sala comercial", "Loja", "Galpão", "Chácara", "Sítio", "Fazenda"]
CATS = [("para-alugar", "apartamento", "Apartamentos para alugar"), ("a-venda", "apartamento", "Apartamentos à venda"), ("a-venda", "area", "Áreas à venda"),
        ("para-alugar", "apartamento-duplex", "Apartamentos duplex para alugar"), ("a-venda", "apartamento-duplex", "Apartamentos duplex à venda"),
        ("para-alugar", "casa", "Casas para alugar"), ("a-venda", "casa", "Casas à venda"), ("para-alugar", "terreno", "Terrenos para alugar"),
        ("a-venda", "terreno", "Terrenos à venda"), ("para-alugar", "galpao", "Galpões para alugar"), ("a-venda", "galpao", "Galpões à venda"), ("a-venda", "chacara", "Chácaras à venda")]
PRET = {"a-venda": ("venda", "à venda"), "para-alugar": ("aluguel", "para alugar")}


def foto_de(imoveis, codigo, k=0):
    """Foto usada de fundo na capa e na faixa de serviços (config hero_img/faixa_img, ou a foto de um imóvel)."""
    for i in imoveis:
        if i["codigo"] == codigo and len(i["fotos"]) > k:
            return foto_url(i["fotos"][k])
    return foto_url(imoveis[0]["fotos"][0]) if imoveis and imoveis[0]["fotos"] else ""


def page_home(imoveis):
    c = CFG
    tipos = sorted({i.get("tipo") for i in imoveis if i.get("tipo")} | set(TIPOS_BASE), key=lambda t: (t not in TIPOS_BASE, TIPOS_BASE.index(t) if t in TIPOS_BASE else 0, t))
    venda = [i for i in imoveis if finalidade(i)["venda"]][:8]
    alug = [i for i in imoveis if finalidade(i)["aluguel"]][:6]
    vazio = '<p class="empty">Os imóveis aprovados aparecem aqui assim que forem publicados.</p>'
    cats = "".join(f'<a href="{BASE}imoveis/{p}/{t}/">{E(n)}</a>' for p, t, n in CATS)
    bairros = "".join(f'<a href="{BASE}imoveis/uberaba/{slug(b)}/" data-pg="{k // 16}">{E(b)} - Uberaba</a>' for k, b in enumerate(c["bairros"]))
    # Fundo original do site; a foto de um imóvel fica por baixo caso ele não carregue
    bg = lambda *us: ",".join(f"url('{E(u)}')" for u in us if u)
    hero = bg(c.get("hero_img"), foto_de(imoveis, "AD0001"))
    faixa = bg(c.get("faixa_img"), foto_de(imoveis, "CA0126", 1))
    end = c["endereco"].split(", ")
    body = f'''<section class="hero" style="background-image:{hero}"><div class="hin">
  <h1>{E(c["hero_titulo"])}</h1>
  <p>{E(c["hero_sub"])}</p>
  {busca_form(tipos)}
</div></section>
<section class="sec"><div class="wrap">
  <h2 class="st">Sua Próxima História em Nossos Imóveis!</h2>
  <div class="tabs"><span class="on">Destaques</span><a href="{BASE}imoveis/a-venda/">Ver mais</a></div>
  <div class="hgrid g4">{"".join(card(i, True) for i in venda) or vazio}</div>
</div></section>
<section class="sec"><div class="wrap">
  <h2 class="st">Seu Lar Temporário!</h2>
  <div class="tabs"><span class="on">Destaques</span><a href="{BASE}imoveis/para-alugar/">Ver mais</a></div>
  <div class="hgrid g3">{"".join(card(i, True) for i in alug) or vazio}</div>
</div></section>
<section class="faixa" style="background-image:{faixa}"><div class="wrap cta3">
  <a class="cta" href="{BASE}encomende-seu-imovel/">{ICON["enc"]}<h3>Imóvel sob encomenda</h3><p>Descreva o imóvel que você procura e nós avisaremos quando encontrarmos.</p><span>Encomende seu imóvel {ICON["seta"]}</span></a>
  <a class="cta" href="{BASE}financiamento-e-bancos/">{ICON["din"]}<h3>Financiamento</h3><p>As melhores ofertas de crédito para você financiar seu imóvel.</p><span>Faça uma simulação {ICON["seta"]}</span></a>
  <a class="cta" href="{BASE}cadastre-seu-imovel/">{ICON["placa"]}<h3>Cadastre seu imóvel</h3><p>Anuncie conosco! Nós encontraremos o melhor negócio para você.</p><span>Cadastre seu imóvel {ICON["seta"]}</span></a>
</div></section>
<section class="sec"><div class="wrap center">
  <div class="ucard"><div class="uh">{logo_img("logo_img_rodape", "logo-sm")}<span class="creci">CRECI: {E(c["creci"])}</span></div>
    <h3>{E(c["nome"])}</h3><p>{"<br>".join(E(x) for x in [", ".join(end[:2]), end[2] if len(end) > 2 else "", ", ".join(end[3:])] if x)}</p>
    <p><a href="https://wa.me/{E(c["whatsapp"])}" target="_blank" rel="noopener">{E(c["fone_whats"])}</a><br><a href="tel:+{E(c["fone_fixo_digits"])}">{E(c["fone_fixo"])}</a></p></div>
  <p class="hor"><b>Horário de funcionamento</b><br>{E(c["horario"])}<br>Para mais informações, entre em contato conosco ou faça-nos uma visita.</p>
  <p class="hor">CRECI: {E(c["creci"])}</p>
  <h2 class="acomp">ACOMPANHE-NOS :)</h2>
  <form class="wform newsf" data-assunto="Quero receber as novidades da Telecasa" data-wa="{E(c["whatsapp"])}"><input name="E-mail" type="email" required placeholder="seunome@email.com.br" aria-label="Seu e-mail"><button type="submit">Enviar</button></form>
  <h2 class="st sm">Descubra outras possibilidades de imóveis</h2>
  <div class="links">{cats}</div>
  <h2 class="st sm">Bairros mais populares</h2>
  <div class="links" id="bairros">{bairros}</div>
  <div class="pgn"><button type="button" data-car="-1">Anterior</button><button type="button" data-car="1">Próximo</button></div>
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
