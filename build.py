#!/usr/bin/env python3
"""Static-site generator for vamsi-kommineni.github.io.

Reads YAML from data/, renders Jinja2 templates/ to dist/.  Pure-Python build
(only Jinja2 + PyYAML + Markdown) so it runs anywhere, including CI.

    python3 build.py            # build into dist/
    python3 -m http.server -d dist 8000   # preview
"""
import datetime
import json
import math
import re
import shutil
from pathlib import Path

import yaml
import markdown as md
from markupsafe import Markup, escape
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
TEMPLATES = ROOT / "templates"
ASSETS = ROOT / "assets"
DIST = ROOT / "dist"
CV_SRC = ROOT / "CV_Kommineni.pdf"


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #
def load(name):
    return yaml.safe_load((DATA / name).read_text(encoding="utf-8"))


site = load("site.yaml")
about = load("about.yaml")
news = load("news.yaml")
research = load("research.yaml")
projects = load("projects.yaml")
pubs = load("publications.yaml")
experience = load("experience.yaml")
education = load("education.yaml")
skills = load("skills.yaml")
talks = load("talks.yaml")
contact = load("contact.yaml")

TODAY = datetime.date.today()
BASEURL = site.get("baseurl", "") or ""

# Surface the ORCID link in the sidebar only when an iD is configured.
if site.get("orcid"):
    site["socials"].append({
        "key": "orcid", "label": "ORCID",
        "href": "https://orcid.org/" + site["orcid"],
    })


# --------------------------------------------------------------------------- #
# URL helpers + Jinja filters
# --------------------------------------------------------------------------- #
def url(path):
    if path.startswith(("http://", "https://", "mailto:")):
        return path
    return BASEURL + path


def abs_url(path):
    if path.startswith(("http://", "https://", "mailto:")):
        return path
    return site["url"].rstrip("/") + BASEURL + path


def mdinline(text):
    """Render inline markdown (bold/italic/links); unwrap the <p> only when the
    result is a single paragraph (multi-paragraph input keeps its <p> tags)."""
    html = md.markdown(str(text).strip())
    m = re.fullmatch(r"<p>(.*)</p>", html, re.S)
    if m and "</p>" not in m.group(1):
        return Markup(m.group(1))
    return Markup(html)


def highlight_me(authors, me):
    """Bold the site owner's name inside an author list (escaped, then wrapped)."""
    out = str(escape(authors)).replace(
        str(escape(me)), '<span class="me">' + str(escape(me)) + "</span>"
    )
    return Markup(out)


def linklabel(u):
    u = u.lower()
    if u.endswith(".pdf"):
        return "PDF"
    if "doi.org" in u:
        return "DOI"
    if "arxiv.org" in u:
        return "arXiv"
    return "Link"


def autoescape(name):
    return bool(name) and name.endswith((".html.j2", ".xml.j2", ".html", ".xml"))


env = Environment(
    loader=FileSystemLoader(str(TEMPLATES)),
    autoescape=autoescape,
    trim_blocks=True,
    lstrip_blocks=False,
)
env.filters["mdinline"] = mdinline
env.filters["highlight_me"] = highlight_me
env.filters["linklabel"] = linklabel
env.globals.update(url=url, abs_url=abs_url)


# --------------------------------------------------------------------------- #
# Derived data
# --------------------------------------------------------------------------- #
def kg_layout(nodes, radius=40.0):
    n = len(nodes)
    out = []
    for i, label in enumerate(nodes):
        ang = math.radians(-90 + i * 360.0 / n)
        out.append({
            "label": label,
            "x": round(50 + radius * math.cos(ang), 2),
            "y": round(50 + radius * math.sin(ang), 2),
        })
    return out


kg = {"core": about["kg_core"], "nodes": kg_layout(about["kg_nodes"])}
years = sorted({i["year"] for i in pubs["items"]}, reverse=True)


def ld_dumps(data):
    """Serialize JSON-LD and neutralise sequences that could break out of the
    inline <script> element (defensive: the data is author-controlled)."""
    s = json.dumps(data, ensure_ascii=False, indent=2)
    return s.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def person_jsonld():
    data = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": site["name"],
        "givenName": "Vamsi Krishna",
        "familyName": "Kommineni",
        "url": abs_url("/"),
        "image": abs_url(site["og_image"]),
        "jobTitle": site["role"],
        "worksFor": {"@type": "Organization", "name": site["affiliation"]},
        "affiliation": {"@type": "Organization", "name": site["affiliation"]},
        "address": {
            "@type": "PostalAddress",
            "addressLocality": "Friedberg",
            "addressRegion": "Hessen",
            "addressCountry": "DE",
        },
        "email": "mailto:" + site["email"],
        "knowsAbout": [k for k in site["keywords"] if k.lower() != "vamsi kommineni"],
        "sameAs": [site["scholar"], site["github"], site["linkedin"]],
    }
    if site.get("orcid"):
        orcid_url = "https://orcid.org/" + site["orcid"]
        data["sameAs"].append(orcid_url)
        data["identifier"] = {
            "@type": "PropertyValue", "propertyID": "ORCID", "value": orcid_url,
        }
    return ld_dumps(data)


def articles_jsonld():
    graph = []
    for it in pubs["items"]:
        entry = {
            "@type": "ScholarlyArticle",
            "headline": it["title"],
            "name": it["title"],
            "author": it["authors"],
            "datePublished": str(it["year"]),
            "isPartOf": {"@type": "Periodical", "name": it["venue"]},
        }
        if it.get("url"):
            entry["url"] = it["url"]
        graph.append(entry)
    return ld_dumps({"@context": "https://schema.org", "@graph": graph})


def projects_jsonld():
    items = []
    for i, p in enumerate(projects["items"], 1):
        items.append({
            "@type": "ListItem",
            "position": i,
            "item": {
                "@type": "SoftwareSourceCode",
                "name": p["name"],
                "description": " ".join(p["description"].split()),
                "codeRepository": p["repo"],
                "author": {"@type": "Person", "name": site["name"]},
            },
        })
    return ld_dumps({
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "Selected projects",
        "itemListElement": items,
    })


PERSON_LD = person_jsonld()
ARTICLES_LD = articles_jsonld()
PROJECTS_LD = projects_jsonld()


def validate_data():
    """Fail the build loudly on common content-authoring mistakes (e.g. the
    YAML colon-trap that silently turns a sentence into a mapping)."""
    errs = []

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                if isinstance(k, str) and " " in k:
                    errs.append(f"{path}: a string was parsed as a mapping key "
                                f"({k!r}: ...); quote it or remove the ': '")
                walk(v, f"{path}.{k}")
        elif isinstance(node, list):
            for j, v in enumerate(node):
                walk(v, f"{path}[{j}]")

    for nm, d in (("about", about), ("news", news), ("research", research),
                  ("projects", projects), ("experience", experience),
                  ("education", education), ("skills", skills), ("talks", talks)):
        walk(d, nm)

    known = {t["key"] for t in pubs["types"]}
    seen = set()
    for it in pubs["items"]:
        if it.get("type") not in known:
            errs.append(f"publication {it.get('id')!r}: unknown type {it.get('type')!r}")
        if it.get("id") in seen:
            errs.append(f"publication: duplicate id {it.get('id')!r}")
        seen.add(it.get("id"))
        for key in ("title", "year", "venue", "authors"):
            if not it.get(key):
                errs.append(f"publication {it.get('id')!r}: missing required key {key!r}")

    if errs:
        raise SystemExit("Data validation failed:\n  - " + "\n  - ".join(errs))


# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #
HOME_TITLE = site["name"] + " · " + site["role"]

PAGES = [
    {"template": "about.html.j2", "out": "index.html", "url": "/", "nav": "about",
     "title_full": HOME_TITLE, "desc": " ".join(site["description"].split()),
     "og_type": "website", "priority": "1.0"},
    {"template": "research.html.j2", "out": "research/index.html", "url": "/research/",
     "nav": "research", "title": "Research", "priority": "0.8",
     "desc": "Research focus of Vamsi Kommineni: generative AI & LLMs, knowledge graphs & NLP, "
             "computer vision & multimodal models, medical & clinical AI, reproducible ML, and AI for science."},
    {"template": "projects.html.j2", "out": "projects/index.html", "url": "/projects/",
     "nav": "projects", "title": "Projects", "priority": "0.7", "projects_ld": True,
     "desc": "Code and projects by Vamsi Kommineni: Inagecas (AI customer support), automatic "
             "knowledge-graph & ontology construction, multi-LLM retrieval with RAG, and agentic pipelines."},
    {"template": "publications.html.j2", "out": "publications/index.html", "url": "/publications/",
     "nav": "publications", "title": "Publications", "priority": "0.9", "articles": True,
     "desc": "Peer-reviewed journal articles, conference papers, preprints, and abstracts by "
             "Vamsi Kommineni, each with a DOI / link and copy-ready BibTeX."},
    {"template": "cv.html.j2", "out": "cv/index.html", "url": "/cv/", "nav": "cv",
     "title": "CV", "og_type": "profile", "priority": "0.8",
     "desc": "Curriculum vitae of Vamsi Kommineni: experience, education, and skills. Download the PDF."},
    {"template": "talks.html.j2", "out": "talks/index.html", "url": "/talks/", "nav": "talks",
     "title": "Talks & outreach", "priority": "0.6",
     "desc": "Talks and outreach by Vamsi Kommineni: organized sessions (TDWG, GfÖ), conference "
             "presentations (SEMANTiCS, TDWG/BISS), thesis supervision, and community work (EcoHack)."},
    {"template": "contact.html.j2", "out": "contact/index.html", "url": "/contact/", "nav": "contact",
     "title": "Contact", "priority": "0.6",
     "desc": "Contact Vamsi Kommineni: open to GenAI, applied-AI, and medical-AI roles in the "
             "Frankfurt–Rhine-Main area or remote in Germany."},
]

BASE_CTX = dict(
    site=site, about=about, news=news, research=research, projects=projects, pubs=pubs,
    years=years, experience=experience, education=education, skills=skills, talks=talks,
    contact=contact, kg=kg, year=TODAY.year, person_jsonld=PERSON_LD,
)


def write(rel, content):
    out = DIST / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")


def render_page(p):
    page = {
        "url": p["url"],
        "nav": p.get("nav"),
        "desc": " ".join(p["desc"].split()),
        "og_type": p.get("og_type", "website"),
        "title_full": p.get("title_full") or (p["title"] + " · " + site["name"]),
    }
    ctx = dict(BASE_CTX)
    ctx["page"] = page
    ctx["articles_jsonld"] = ARTICLES_LD if p.get("articles") else None
    ctx["projects_jsonld"] = PROJECTS_LD if p.get("projects_ld") else None
    write(p["out"], env.get_template(p["template"]).render(**ctx))


def build():
    validate_data()
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    # pages
    for p in PAGES:
        render_page(p)

    # 404
    write("404.html", env.get_template("404.html.j2").render(
        **dict(BASE_CTX, page={"url": "/404.html", "nav": None, "noindex": True,
                               "desc": "Page not found.", "og_type": "website",
                               "title_full": "Page not found · " + site["name"]},
               articles_jsonld=None, projects_jsonld=None)))

    # sitemap + robots
    write("sitemap.xml", env.get_template("sitemap.xml.j2").render(
        pages=PAGES, lastmod=TODAY.isoformat(), abs_url=abs_url))
    write("robots.txt", env.get_template("robots.txt.j2").render(abs_url=abs_url))

    # web manifest
    manifest = {
        "name": site["name"],
        "short_name": "V. Kommineni",
        "description": " ".join(site["description"].split()),
        "start_url": url("/"),
        "scope": url("/"),
        "display": "standalone",
        "background_color": "#0d1626",
        "theme_color": "#0d1626",
        "icons": [
            {"src": url("/assets/img/icon-192.png"), "sizes": "192x192", "type": "image/png"},
            {"src": url("/assets/img/icon-512.png"), "sizes": "512x512", "type": "image/png"},
            {"src": url("/assets/img/icon-512.png"), "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }
    write("site.webmanifest", json.dumps(manifest, ensure_ascii=False, indent=2))

    # static assets
    shutil.copytree(ASSETS, DIST / "assets")
    shutil.copy2(ASSETS / "img" / "favicon.ico", DIST / "favicon.ico")

    # CV pdf
    if CV_SRC.exists():
        shutil.copy2(CV_SRC, DIST / "Vamsi-Kommineni-CV.pdf")
    else:
        print("  ! warning: CV_Kommineni.pdf not found: download button will 404")

    # GitHub Pages: don't run Jekyll
    (DIST / ".nojekyll").write_text("", encoding="utf-8")

    n = len(PAGES) + 1
    print(f"Built {n} pages -> {DIST}")


if __name__ == "__main__":
    build()
