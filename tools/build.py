#!/usr/bin/env python3
"""Static site generator for the portfolio.

Reads content/site.json and content/projects/*.json, writes index.html,
projects/<slug>.html, 404.html, sitemap.xml and robots.txt into the repo root.
Standard library only.  Usage:  python3 tools/build.py
"""
import datetime
import html
import json
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = json.loads((ROOT / "content/site.json").read_text(encoding="utf-8"))
PROJECTS = {}
for _p in sorted((ROOT / "content/projects").glob("*.json")):
    _d = json.loads(_p.read_text(encoding="utf-8"))
    PROJECTS[_d["slug"]] = _d
ORDER = [s for s in SITE["project_order"] if s in PROJECTS]
CATS = {c["id"]: c for c in SITE["categories"]}
BASE = SITE["url"].rstrip("/") + "/"

KINDS = {
    "measured": ("Measured", "Instrument reading from a test or inspection."),
    "calculated": ("Calculated", "Analytical result from design calculations."),
    "simulated": ("Simulated", "Output of a simulation, not a physical test."),
    "reported": ("Reported", "Workplace or lab figure as stated on my resume or portfolio."),
    "projected": ("Projected", "Forecast, not yet realized."),
    "demonstrated": ("Demonstrated", "Observed in a working prototype."),
}

DEFAULT_CONFIDENTIALITY = (
    "All figures and information presented here have been reviewed and approved by the relevant "
    "advisors, assignment leaders, and company managers. The material has been carefully selected "
    "and presented at a level that does not disclose confidential, proprietary, or otherwise "
    "sensitive company information."
)


# ---------------------------------------------------------------- helpers
def esc(s):
    return html.escape(str(s), quote=True)


def md(s):
    """Escape text, then allow **bold**."""
    s = html.escape(str(s), quote=False)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def webp_size(path):
    b = Path(path).read_bytes()
    if b[:4] != b"RIFF" or b[8:12] != b"WEBP":
        raise ValueError(f"{path} is not a WebP file")
    fmt = b[12:16]
    if fmt == b"VP8 ":
        w, h = struct.unpack("<HH", b[26:30])
        return w & 0x3FFF, h & 0x3FFF
    if fmt == b"VP8L":
        bits = struct.unpack("<I", b[21:25])[0]
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    if fmt == b"VP8X":
        return 1 + int.from_bytes(b[24:27], "little"), 1 + int.from_bytes(b[27:30], "little")
    raise ValueError(f"unsupported WebP chunk {fmt!r} in {path}")


def img_path(src):
    p = ROOT / "assets/img" / (src + ".webp")
    if not p.exists():
        raise FileNotFoundError(p)
    return p


def img_tag(src, alt, root, variants=None, sizes=None, loading="lazy", priority=False):
    w, h = webp_size(img_path(src))
    url = f"{root}assets/img/{src}.webp"
    srcset = ""
    if variants:
        parts = [f"{root}assets/img/{v}.webp {vw}w" for v, vw in variants] + [f"{url} {w}w"]
        srcset = f' srcset="{", ".join(parts)}" sizes="{sizes or "(min-width: 900px) 720px, 100vw"}"'
    extra = ' fetchpriority="high"' if priority else ""
    return (
        f'<img src="{url}"{srcset} width="{w}" height="{h}" alt="{esc(alt)}" '
        f'style="--w:{w}px;--h:{h}px" loading="{loading}" decoding="async"{extra}>'
    )


def link_target(target, root):
    """Project slug -> case study URL; '#anchor' -> home anchor."""
    if target.startswith("#"):
        return f"{root}index.html{target}" if root else target
    return f"{root}projects/{target}.html"


def short_desc(s, limit=158):
    s = re.sub(r"\*\*", "", s)
    if len(s) <= limit:
        return s
    cut = s[:limit].rsplit(" ", 1)[0].rstrip(",;:")
    return cut + "..."


# ---------------------------------------------------------------- layout
def head(title, desc, path, root, og_title=None):
    url = BASE + path
    og_img = BASE + "assets/og-card.png"
    person = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": SITE["name"],
        "url": BASE,
        "image": BASE + "assets/img/portrait.webp",
        "jobTitle": "Mechanical engineering student",
        "affiliation": {"@type": "CollegeOrUniversity", "name": "The Ohio State University"},
        "sameAs": [SITE["links"]["linkedin"], SITE["links"]["github"]],
    }
    fonts = "".join(
        f'<link rel="preload" href="{root}assets/fonts/{f}.woff2" as="font" type="font/woff2" crossorigin>\n'
        for f in ("ibm-plex-sans-latin-400-normal", "ibm-plex-sans-latin-500-normal")
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{esc(url)}">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#f4f3ef" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#101315" media="(prefers-color-scheme: dark)">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{esc(SITE['name'])}">
<meta property="og:title" content="{esc(og_title or title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{esc(url)}">
<meta property="og:image" content="{esc(og_img)}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Franky Lian, mechanical engineering portfolio">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{root}assets/favicon.svg" type="image/svg+xml">
{fonts}<link rel="stylesheet" href="{root}assets/css/main.css">
<script type="application/ld+json">{json.dumps(person)}</script>
</head>
"""


def header(root):
    home = f"{root}index.html"
    nav = "".join(
        f'<a href="{home}#{a}">{label}</a>'
        for a, label in (("work", "Work"), ("experience", "Experience"), ("skills", "Skills"),
                         ("about", "About"), ("contact", "Contact"))
    )
    return f"""<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site-header">
  <div class="wrap bar">
    <a class="brand" href="{home}"><span class="brand-mark" aria-hidden="true">FL</span><span>Franky Lian</span></a>
    <nav aria-label="Primary">{nav}<a class="nav-resume" href="{root}{SITE['links']['resume']}" target="_blank" rel="noopener">Resume</a></nav>
  </div>
</header>
"""


def footer(root):
    L = SITE["links"]
    conf = SITE.get("confidentiality", DEFAULT_CONFIDENTIALITY)
    return f"""<footer class="site-footer">
  <div class="wrap">
    <p class="conf"><span class="mono">Confidentiality</span> {esc(conf)}</p>
    <div class="foot-row">
      <p>&copy; {datetime.date.today().year} {esc(SITE['name'])}</p>
      <p class="foot-links">
        <a href="{esc(L['linkedin'])}" rel="noopener">LinkedIn</a>
        <a href="{esc(L['github'])}" rel="noopener">GitHub</a>
        <a href="{esc(L['repo'])}" rel="noopener">Site source</a>
      </p>
      <p class="muted">Set in IBM Plex. Self-hosted, SIL Open Font License.</p>
    </div>
  </div>
</footer>
<dialog id="lightbox" aria-label="Image viewer">
  <figure>
    <img alt="">
    <figcaption></figcaption>
  </figure>
  <button type="button" class="lb-close" aria-label="Close image viewer">Close</button>
</dialog>
<script src="{root}assets/js/main.js" defer></script>
</body>
</html>
"""


# ---------------------------------------------------------------- components
def zoom_figure(fig, root, num, loading="lazy"):
    w, h = webp_size(img_path(fig["src"]))
    url = f"{root}assets/img/{fig['src']}.webp"
    tag = img_tag(fig["src"], fig["alt"], root, variants=fig.get("variants"), loading=loading)
    return (
        f'<figure class="fig" style="--w:{w}px">'
        f'<a class="zoom" href="{url}" data-caption="{esc(fig["caption"])}" data-alt="{esc(fig["alt"])}" '
        f'aria-label="View larger: {esc(fig["caption"])}">{tag}</a>'
        f'<figcaption><span class="mono">FIG. {num:02d}</span> {md(fig["caption"])}</figcaption></figure>'
    )


def thumb(p, root):
    t = p["thumb"]
    if "stat" in t:
        s = t["stat"]
        kind = KINDS[s["kind"]][0] if s.get("kind") else ""
        return (
            '<div class="plate plate-stat">'
            f'<span class="mono">{esc(kind)}</span>'
            f'<strong>{esc(s["value"])}</strong>'
            f'<span class="stat-label">{esc(s["label"])}</span></div>'
        )
    return f'<div class="plate">{img_tag(t["src"], t.get("alt", ""), root)}</div>'


def project_card(i, slug, root, feature=False):
    p = PROJECTS[slug]
    chips = "".join(f'<span class="chip mono">{esc(CATS[c]["label"])}</span>' for c in p["cats"])
    return f"""<article class="card{' feature' if feature else ''}" data-cats="{' '.join(p['cats'])}">
  {thumb(p, root)}
  <div class="card-body">
    <p class="card-top mono"><span>{i:02d}</span>{chips}</p>
    <h3><a href="{root}projects/{slug}.html">{esc(p['title'])}</a></h3>
    <p class="card-sum">{md(p['short'])}</p>
    <p class="card-meta">{esc(p['org'])} <span aria-hidden="true">&middot;</span> {esc(p['dates'])}</p>
    <p class="card-cta mono" aria-hidden="true">Case study <span class="arrow">&rarr;</span></p>
  </div>
</article>"""


def sec_head(idx, title, intro, hid):
    intro_html = f'<p class="sec-intro">{md(intro)}</p>' if intro else ""
    return (
        f'<header class="sec-head"><p class="idx mono">{idx}</p>'
        f'<div><h2 id="{hid}">{esc(title)}</h2>{intro_html}</div></header>'
    )


def hero_sheet(root):
    hs = SITE["hero_sheet"]
    states = ""
    for i, im in enumerate(hs["images"]):
        w, h = webp_size(img_path(im["src"]))
        url = f"{root}assets/img/{im['src']}.webp"
        tag = img_tag(im["src"], im["alt"], root, loading="eager" if i == 0 else "lazy", priority=(i == 0))
        states += (
            f'<div class="state{" is-active" if i == 0 else ""}" data-tag="{esc(im["tag"])}">'
            f'<a class="zoom" href="{url}" data-caption="{esc(im["caption"])}" data-alt="{esc(im["alt"])}" '
            f'aria-label="View larger: {esc(im["tag"])} scan">{tag}</a>'
            f'<p class="state-cap"><span class="mono tag">{esc(im["tag"])}</span> {esc(im["caption"])}</p></div>'
        )
    rows = ""
    for r in hs["titleblock"]:
        badge = ""
        if len(r) > 2:
            badge = f' <span class="badge {esc(r[2])}">{"Pass" if r[2] == "pass" else "Fail"}</span>'
        rows += f'<tr><th scope="row">{esc(r[0])}</th><td>{esc(r[1])}{badge}</td></tr>'
    case = f"{root}projects/{hs['project']}.html"
    return f"""<figure class="sheet" data-sheet aria-labelledby="sheet-cap">
  <div class="sheet-states">{states}</div>
  <table class="titleblock"><caption class="sr-only">Inspection summary</caption><tbody>{rows}</tbody></table>
  <figcaption id="sheet-cap" class="mono"><span>{esc(hs['fig'])}</span> {esc(hs['caption'])} <a href="{case}">Read the case study <span aria-hidden="true">&rarr;</span></a></figcaption>
</figure>"""


# ---------------------------------------------------------------- pages
def build_home():
    root = ""
    L = SITE["links"]
    out = [head(SITE["title"], SITE["description"], "", root), header(root), '<main id="main">']

    out.append(f"""<section class="hero" id="top">
  <div class="wrap hero-grid">
    <div class="hero-copy">
      <p class="eyebrow mono">{esc(SITE['eyebrow'])}</p>
      <h1><span class="name mono">{esc(SITE['name'])}</span><span class="headline">{esc(SITE['headline'])}</span></h1>
      <p class="lede">{esc(SITE['intro'])}</p>
      <p class="hero-actions">
        <a class="btn" href="#work">Selected projects</a>
        <a class="link" href="{root}{L['resume']}" target="_blank" rel="noopener">Resume (PDF)</a>
        <a class="link" href="{esc(L['linkedin'])}" rel="noopener">LinkedIn</a>
        <a class="link" href="{esc(L['github'])}" rel="noopener">GitHub</a>
      </p>
    </div>
    {hero_sheet(root)}
  </div>
</section>""")

    pillars = ""
    for p in SITE["pillars"]:
        links = "".join(
            f'<a href="{link_target(t, root)}">{esc(lbl)} <span aria-hidden="true">&rarr;</span></a>' for t, lbl in p["links"]
        )
        pillars += (
            f'<li><p class="mono pn">{p["n"]}</p><h3>{esc(p["title"])}</h3>'
            f'<p>{md(p["text"])}</p><p class="plinks">{links}</p></li>'
        )
    out.append(f"""<section class="section" id="focus" aria-labelledby="focus-h"><div class="wrap">
  {sec_head("01", "What I do", "", "focus-h")}
  <ol class="pillars">{pillars}</ol>
</div></section>""")

    filters = '<button type="button" class="filter is-active" data-filter="all" aria-pressed="true">All</button>' + "".join(
        f'<button type="button" class="filter" data-filter="{c["id"]}" aria-pressed="false">{esc(c["label"])}</button>'
        for c in SITE["categories"]
    )
    cards = "".join(project_card(i + 1, s, root, feature=(i == 0)) for i, s in enumerate(ORDER))
    team = ""
    for t in SITE["team_projects"]:
        bl = "".join(f"<li>{md(b)}</li>" for b in t["bullets"])
        team += (
            f'<li class="team"><p class="mono dates">{esc(t["dates"])}</p>'
            f'<div><h4>{esc(t["title"])}</h4><p class="org">{esc(t["org"])}</p><ul>{bl}</ul></div></li>'
        )
    out.append(f"""<section class="section" id="work" aria-labelledby="work-h"><div class="wrap">
  {sec_head("02", "Selected work", f"{len(ORDER)} case studies. Each follows the same path: problem, approach, validation, result.", "work-h")}
  <div class="filters" role="group" aria-label="Filter projects by category">{filters}</div>
  <p class="sr-only" id="filter-status" aria-live="polite"></p>
  <div class="cards" id="cards">{cards}</div>
  <h3 class="sub-h">Team projects</h3>
  <ul class="team-list">{team}</ul>
</div></section>""")

    jobs = ""
    for e in SITE["experience"]:
        bl = "".join(f"<li>{md(b)}</li>" for b in e["bullets"])
        rel = ""
        if e.get("related"):
            rel = '<p class="rel">' + "".join(
                f'<a href="{link_target(t, root)}">{esc(lbl)} <span aria-hidden="true">&rarr;</span></a>' for t, lbl in e["related"]
            ) + "</p>"
        jobs += (
            f'<li class="job" id="exp-{esc(e["id"])}"><p class="mono dates">{esc(e["dates"])}</p>'
            f'<div><h3>{esc(e["title"])}</h3><p class="org">{esc(e["org"])} <span aria-hidden="true">&middot;</span> {esc(e["place"])}</p>'
            f'<ul>{bl}</ul>{rel}</div></li>'
        )
    ed = SITE["education"]
    out.append(f"""<section class="section" id="experience" aria-labelledby="exp-h"><div class="wrap">
  {sec_head("03", "Experience", "", "exp-h")}
  <ol class="timeline">{jobs}</ol>
  <div class="edu">
    <p class="mono dates">Education</p>
    <div><h3>{esc(ed['degree'])}</h3><p class="org">{esc(ed['school'])} <span aria-hidden="true">&middot;</span> {esc(ed['dates'])}</p>
    <p>{esc(ed['gpa'])}</p><p>{esc(ed['cert'])}</p></div>
  </div>
</div></section>""")

    groups = ""
    for g in SITE["skills"]:
        items = "".join(f"<div><dt>{esc(n)}</dt><dd>{esc(ev)}</dd></div>" for n, ev in g["items"])
        also = ""
        if g.get("also"):
            names = ", ".join(re.sub(r"\s*\(listed on resume\)", "", a) for a in g["also"])
            also = f'<p class="also"><span class="mono">Also on my resume</span> {esc(names)}</p>'
        groups += f'<section class="skill-group"><h3>{esc(g["group"])}</h3><dl>{items}</dl>{also}</section>'
    out.append(f"""<section class="section" id="skills" aria-labelledby="skills-h"><div class="wrap">
  {sec_head("04", "Skills", "Grouped by what they were used for, with where I used them. Tools listed only on my resume appear below each group without a project attached.", "skills-h")}
  <div class="skills">{groups}</div>
</div></section>""")

    about = "".join(f"<p>{md(p)}</p>" for p in SITE["about"])
    out.append(f"""<section class="section" id="about" aria-labelledby="about-h"><div class="wrap">
  {sec_head("05", "About", "", "about-h")}
  <div class="about">
    <div class="portrait plate">{img_tag("portrait", "Portrait of Franky Lian in a dark blue striped shirt.", root)}</div>
    <div class="prose">{about}</div>
  </div>
</div></section>""")

    em = SITE["links"]
    out.append(f"""<section class="section" id="contact" aria-labelledby="contact-h"><div class="wrap">
  {sec_head("06", "Contact", SITE['contact_text'], "contact-h")}
  <ul class="contact-list">
    <li><span class="mono">Email</span><span class="email" data-user="{esc(em['email_user'])}" data-domain="{esc(em['email_domain'])}">{esc(em['email_user'])} [at] {esc(em['email_domain'].replace('.', ' [dot] '))}</span></li>
    <li><span class="mono">LinkedIn</span><a href="{esc(em['linkedin'])}" rel="noopener">{esc(em['linkedin'].replace('https://www.', ''))}</a></li>
    <li><span class="mono">GitHub</span><a href="{esc(em['github'])}" rel="noopener">{esc(em['github'].replace('https://', ''))}</a></li>
    <li><span class="mono">Resume</span><a href="{root}{em['resume']}" target="_blank" rel="noopener">Download PDF</a></li>
  </ul>
</div></section>""")

    out.append("</main>")
    out.append(footer(root))
    return "".join(out)


def build_project(slug):
    p = PROJECTS[slug]
    root = "../"
    idx = ORDER.index(slug)
    nxt = PROJECTS[ORDER[(idx + 1) % len(ORDER)]]
    title = f"{p['title']} | {SITE['name']}"
    desc = p.get("meta_desc") or short_desc(p["lede"])
    out = [head(title, desc, f"projects/{slug}.html", root, og_title=p["title"]), header(root), '<main id="main">']

    cats = ", ".join(CATS[c]["full"] for c in p["cats"])
    facts = "".join(
        f"<div><dt>{k}</dt><dd>{esc(v)}</dd></div>"
        for k, v in (("Organization", p["org"]), ("Role", p["role"]), ("Dates", p["dates"]),
                     ("Status", p["status"]), ("Category", cats))
    )
    out.append(f"""<article class="case">
  <header class="case-head"><div class="wrap">
    <p class="crumbs mono"><a href="{root}index.html#work">Work</a> / {esc(cats)}</p>
    <h1>{esc(p['title'])}</h1>
    <p class="dek">{md(p['lede'])}</p>
    <dl class="facts">{facts}</dl>
  </div></header>
  <div class="wrap case-wrap">
    <aside class="own" aria-labelledby="own-h"><h2 id="own-h" class="mono">My contribution</h2><p>{md(p['ownership'])}</p></aside>""")

    if p.get("results"):
        tiles = ""
        used = []
        for r in p["results"]:
            kind = r.get("kind")
            kl = ""
            if kind:
                used.append(kind)
                kl = f'<p class="kind mono kind-{kind}">{KINDS[kind][0]}</p>'
            tiles += f'<li><p class="val">{esc(r["value"])}</p><p class="lbl">{esc(r["label"])}</p>{kl}</li>'
        legend = "".join(
            f"<div><dt class=\"mono kind-{k}\">{KINDS[k][0]}</dt><dd>{esc(KINDS[k][1])}</dd></div>"
            for k in dict.fromkeys(used)
        )
        out.append(
            f'<section class="results-wrap" aria-labelledby="res-h"><h2 id="res-h" class="sr-only">Key results</h2>'
            f'<ul class="results">{tiles}</ul><dl class="legend">{legend}</dl></section>'
        )

    n = 0
    for sec in p["sections"]:
        sid = slugify(sec["heading"])
        body = "".join(f"<p>{md(t)}</p>" for t in sec.get("paras", []))
        if sec.get("bullets"):
            body += "<ul>" + "".join(f"<li>{md(b)}</li>" for b in sec["bullets"]) + "</ul>"
        figs = sec.get("figures", [])
        if figs:
            html_figs = ""
            for f in figs:
                n += 1
                html_figs += zoom_figure(f, root, n)
            body += f'<div class="figs figs-{min(len(figs), 3)}">{html_figs}</div>'
        out.append(
            f'<section class="case-sec" aria-labelledby="{sid}"><h2 id="{sid}">{esc(sec["heading"])}</h2>'
            f'<div class="case-body">{body}</div></section>'
        )

    tools = "".join(f"<li>{esc(t)}</li>" for t in p.get("tools", []))
    note = f'<p class="note">{esc(p["note"])}</p>' if p.get("note") else ""
    out.append(
        f'<section class="case-sec" aria-labelledby="tools-h"><h2 id="tools-h">Tools and methods</h2>'
        f'<div class="case-body"><ul class="tools">{tools}</ul>{note}</div></section>'
    )
    out.append(f"""<nav class="case-nav" aria-label="Case studies">
      <a href="{root}index.html#work"><span class="mono">Back</span> All work</a>
      <a href="{nxt['slug']}.html"><span class="mono">Next case study</span> {esc(nxt['title'])} <span aria-hidden="true">&rarr;</span></a>
    </nav>
  </div>
</article>""")
    out.append("</main>")
    out.append(footer(root))
    return "".join(out)


def build_404():
    root = BASE
    out = [head("Page not found | " + SITE["name"], "This page does not exist.", "404.html", root), header(root),
           '<main id="main"><section class="section"><div class="wrap"><p class="mono">404</p>'
           f'<h1 class="headline">That page does not exist.</h1><p class="lede"><a href="{root}index.html">Back to the portfolio</a></p>'
           "</div></section></main>", footer(root)]
    return "".join(out)


def main():
    (ROOT / "projects").mkdir(exist_ok=True)
    (ROOT / "index.html").write_text(build_home(), encoding="utf-8")
    for slug in ORDER:
        (ROOT / "projects" / f"{slug}.html").write_text(build_project(slug), encoding="utf-8")
    (ROOT / "404.html").write_text(build_404(), encoding="utf-8")
    today = datetime.date.today().isoformat()
    urls = [BASE] + [f"{BASE}projects/{s}.html" for s in ORDER]
    sm = "".join(f"  <url><loc>{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls)
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + sm + "</urlset>\n",
        encoding="utf-8",
    )
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {BASE}sitemap.xml\n", encoding="utf-8")
    (ROOT / ".nojekyll").write_text("", encoding="utf-8")
    print(f"built index.html, {len(ORDER)} case studies, 404.html, sitemap.xml, robots.txt")


if __name__ == "__main__":
    main()
