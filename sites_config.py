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
  function itemFromNode(node) {
    const a = node.querySelector('a[href]');
    if (!a) return null;
    let u;
    try { u = new URL(a.href); } catch (e) { return null; }
    const hasImg = !!node.querySelector('img');
    let hasPlayableVideo = false;
    node.querySelectorAll('video').forEach(v => {
      if (!v.closest('a[href]')) hasPlayableVideo = true;
    });
    return { hostname: u.hostname, pathname: u.pathname, hasImg, hasPlayableVideo };
  }

  function dedupe(items) {
    const seen = new Set();
    return items.filter(it => {
      const key = it.hostname + it.pathname;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  function itemsFor(child) {
    // Preferred: one <article> (or similar repeating node) per visible card,
    // so a card with several internal <video> tags (different qualities)
    // still counts as ONE playable item, not several.
    let nodes = Array.from(child.querySelectorAll('article'));
    if (nodes.length === 0) nodes = Array.from(child.children);
    const items = dedupe(nodes.map(itemFromNode).filter(Boolean));
    if (items.length >= 1) return { items, precise: true };

    // Fallback: just dedupe every link in the module. Video/playable
    // detection is not reliable at this granularity, so it's left off
    // rather than risk over-counting.
    const seen = new Map();
    Array.from(child.querySelectorAll('a[href]')).forEach(a => {
      let u;
      try { u = new URL(a.href); } catch (e) { return; }
      const key = u.hostname + u.pathname;
      const hasImg = !!a.querySelector('img');
      if (!seen.has(key)) seen.set(key, { hostname: u.hostname, pathname: u.pathname, hasImg, hasPlayableVideo: false });
      else if (hasImg) seen.get(key).hasImg = true;
    });
    return { items: Array.from(seen.values()), precise: false };
  }

  const out = [];
  Array.from(container.children).forEach((child) => {
    const { items, precise } = itemsFor(child);
    if (items.length === 0) return;
    const h = child.querySelector('h1,h2,h3,[class*="title" i]');
    const name = h ? h.innerText.trim().slice(0, 60) : '';
    out.push({ name, items, precise });
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

# Best-effort click on the most common EU cookie-consent banners, so they
# don't sit on top of / block hydration of the content underneath.
DISMISS_COOKIES_JS = r"""
() => {
  const selectors = [
    '#onetrust-accept-btn-handler',
    'button[id*="accept" i][id*="cookie" i]',
    'button[class*="accept" i][class*="cookie" i]',
    'button[aria-label*="Aceptar" i]',
    'button[aria-label*="Accept" i]',
  ];
  for (const sel of selectors) {
    const btn = document.querySelector(sel);
    if (btn) { btn.click(); return true; }
  }
  return false;
}
"""
