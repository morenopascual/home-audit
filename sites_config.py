"""
Configuration for each homepage: how to find the module container on the
page, and the rules used to classify every link inside it as:
  - "own"     -> the channel's own site
  - "ip"      -> streaming platform, page-type link
  - "ipl"     -> streaming platform, direct player / autoplay link
  - "om"      -> another brand in the same group
  - excluded  -> ads, social icons, app-store badges, login/account links

These rules mirror the manual analysis done for Cuatro, Telecinco, Antena3,
laSexta and RTVE in September 2026. Site redesigns WILL eventually break the
`container_js` selectors below -- if a site comes back with 0 modules, that's
the first thing to check and fix.
"""

# JS snippet run in the page for each site. It must return the module
# container element (the parent whose children are the homepage's content
# blocks). Kept separate per site because each CMS nests things differently.
CONTAINER_JS = {
    "antena3": "document.querySelector('main')",
    "lasexta": "document.querySelector('main')",
    "cuatro": "document.querySelector('main').children[0].children[1]",
    "telecinco": "document.querySelector('[class*=\"contentBoards\" i]')",
    "rtve": "document.querySelector('main').children[1].children[0]",
}

# Generic module-walking script: given a container, returns one entry per
# child that has at least one link, each with its (deduped) list of items.
# An item is "playable" if it contains a real <video> element that is NOT
# itself wrapped in a navigating <a href> (that pattern -- video wrapped in
# a link -- is how every site's "Stories" carousel works: it looks like
# inline video but actually opens a separate viewer page).
EXTRACT_MODULES_JS = r"""
(container) => {
  function classify(el) {
    const links = Array.from(el.querySelectorAll('a[href]'));
    const seen = new Map();
    links.forEach(a => {
      let u;
      try { u = new URL(a.href); } catch (e) { return; }
      const key = u.hostname + u.pathname;
      const hasImg = !!a.querySelector('img');
      if (!seen.has(key)) seen.set(key, { hostname: u.hostname, pathname: u.pathname, hasImg });
      else if (hasImg) seen.get(key).hasImg = true;
    });
    return Array.from(seen.values());
  }
  const out = [];
  Array.from(container.children).forEach((child) => {
    const items = classify(child);
    if (items.length === 0) return;
    const h = child.querySelector('h1,h2,h3,[class*="title" i]');
    const name = h ? h.innerText.trim().slice(0, 60) : '';
    // playable = a <video> in this child that is not wrapped in a navigating <a>
    let playableCount = 0;
    child.querySelectorAll('video').forEach(v => {
      if (!v.closest('a[href]')) playableCount++;
    });
    out.push({ name, items, playableCount });
  });
  return out;
}
"""


def classify_link(site_key, hostname, pathname):
    """Returns one of 'own', 'ip', 'ipl', 'om', or None (=excluded)."""

    # --- global excludes: ads, social, app stores, accounts, betting ---
    EXCLUDE_SUBSTR = [
        "retabet", "apuestas", "instagram.com", "tiktok.com", "facebook.com",
        "x.com", "whatsapp.com", "google.com/cp", "t.me/", "itunes.apple.com",
        "play.google.com", "secure2.rtve.es", "/usuarios/",
    ]
    haystack = hostname + pathname
    if any(s in haystack for s in EXCLUDE_SUBSTR):
        return None

    if site_key == "antena3":
        if hostname.endswith("antena3.com"):
            return "own"
        if hostname == "www.atresplayer.com":
            return "ipl" if pathname.startswith("/directos/") else "ip"
        return "om"

    if site_key == "lasexta":
        if hostname.endswith("lasexta.com"):
            return "own"
        if hostname == "www.atresplayer.com":
            return "ipl" if pathname.startswith("/directos/") else "ip"
        return "om"

    if site_key == "cuatro":
        if hostname.endswith("cuatro.com"):
            return "own"
        if "mediasetinfinity.es" in hostname:
            return "ipl" if "/player/" in pathname else "ip"
        if "mitele" in pathname.lower():
            return None  # native/advertorial module
        return "om"

    if site_key == "telecinco":
        if hostname.endswith("telecinco.es"):
            return "own"
        if "mediasetinfinity.es" in hostname:
            return "ipl" if "/player/" in pathname else "ip"
        if "regalos" in pathname.lower():
            return None  # affiliate/advertorial module
        return "om"

    if site_key == "rtve":
        if hostname.endswith("rtve.es"):
            if pathname.startswith("/play/videos/"):
                if "/directo/" in pathname:
                    return "ipl"
                depth = len([p for p in pathname.strip("/").split("/") if p])
                return "ip" if depth <= 3 else "ipl"
            if pathname.startswith("/play/audios/") or pathname.startswith("/play/radio"):
                return "om"  # RNE audio, same domain, different product
            return "own"  # includes /play/noticias/ editorial articles
        return "om"

    return None


SITES = {
    "antena3": {"label": "Antena 3", "url": "https://www.antena3.com/",
                "own_label": "Antena3", "om_label": "Otras marcas del grupo"},
    "lasexta": {"label": "laSexta", "url": "https://www.lasexta.com/",
                "own_label": "laSexta", "om_label": "Otras marcas del grupo"},
    "telecinco": {"label": "Telecinco", "url": "https://www.telecinco.es/",
                  "own_label": "Telecinco", "om_label": "Otro Mediaset"},
    "cuatro": {"label": "Cuatro", "url": "https://www.cuatro.com/",
               "own_label": "Cuatro", "om_label": "Otro Mediaset"},
    "rtve": {"label": "RTVE.es", "url": "https://www.rtve.es/",
             "own_label": "RTVE.es", "om_label": "RNE (audio, mismo dominio)"},
}

SITE_ORDER = ["antena3", "lasexta", "telecinco", "cuatro", "rtve"]
