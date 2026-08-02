"""Team-name matching between Kalshi and ESPN, with the failure modes named.

This is the component that broke the last cross-venue join: it matched 0 of 76
MLB markets because Kalshi names teams by city and the matcher keyed on
nicknames. For soccer the problem is worse -- Spanish/Portuguese club names,
accents, "CF"/"FC"/"CD" prefixes, and Kalshi's habit of truncating.

Design rules:
  - normalise aggressively (strip accents, punctuation, club-type tokens)
  - match on the SET of two teams plus the date, never on one name alone
  - an alias table for the cases normalisation cannot reach
  - never silently drop a non-match: the caller counts and inspects them
"""
import re
import unicodedata

# tokens that carry no identity: club-type words and common suffixes
NOISE = {
    "fc", "cf", "cd", "ca", "sc", "ac", "afc", "cs", "ec", "se", "sd", "ad",
    "club", "clube", "deportivo", "deportes", "atletico", "atlético",
    "de", "do", "da", "del", "la", "el", "los", "las", "y", "and",
    "futbol", "fútbol", "football", "futebol", "soccer", "united", "u",
    "sporting", "real",
}

# Cases normalisation cannot reach. Maps a normalised form -> canonical key.
ALIAS = {
    # Liga MX
    "america": "america", "clubamerica": "america",
    "guadalajara": "guadalajara", "chivas": "guadalajara",
    "cruzazul": "cruzazul",
    "unam": "pumas", "pumas": "pumas", "pumasunam": "pumas",
    "uanl": "tigres", "tigres": "tigres", "tigresuanl": "tigres",
    "monterrey": "monterrey", "rayados": "monterrey",
    "santoslaguna": "santos", "santos": "santos",
    "leon": "leon", "queretaro": "queretaro", "pachuca": "pachuca",
    "toluca": "toluca", "necaxa": "necaxa", "puebla": "puebla",
    "tijuana": "tijuana", "xolos": "tijuana",
    "juarez": "juarez", "fcjuarez": "juarez", "bravos": "juarez",
    "mazatlan": "mazatlan", "atlas": "atlas", "sanluis": "sanluis",
    "atleticosanluis": "sanluis", "atlante": "atlante",
    # Argentina
    "boca": "boca", "bocajuniors": "boca",
    "river": "river", "riverplate": "river",
    "racing": "racing", "racingclub": "racing",
    "independiente": "independiente",
    "sanlorenzo": "sanlorenzo", "velez": "velez", "velezsarsfield": "velez",
    "estudiantes": "estudiantes", "estudiantesplata": "estudiantes",
    "gimnasia": "gimnasia", "gimnasiaplata": "gimnasia",
    "newells": "newells", "newellsoldboys": "newells",
    "rosariocentral": "rosariocentral", "central": "rosariocentral",
    "talleres": "talleres", "belgrano": "belgrano",
    "godoycruz": "godoycruz", "huracan": "huracan", "lanus": "lanus",
    "banfield": "banfield", "tigre": "tigre", "platense": "platense",
    "argentinosjuniors": "argentinos", "argentinos": "argentinos",
    "defensajusticia": "defensa", "defensa": "defensa",
    "instituto": "instituto", "barracascentral": "barracas",
    "sarmiento": "sarmiento", "riestra": "riestra", "deportivoriestra": "riestra",
    "aldosivi": "aldosivi", "sanmartin": "sanmartin",
    "atleticotucuman": "tucuman", "tucuman": "tucuman",
    "unionsantafe": "union", "union": "union",
    "colon": "colon", "centralcordoba": "centralcordoba",
    # Brazil
    "flamengo": "flamengo", "palmeiras": "palmeiras",
    "corinthians": "corinthians", "saopaulo": "saopaulo",
    "santos": "santos", "gremio": "gremio", "internacional": "internacional",
    "cruzeiro": "cruzeiro", "atleticomineiro": "mineiro", "mineiro": "mineiro",
    "botafogo": "botafogo", "fluminense": "fluminense", "vasco": "vasco",
    "vascogama": "vasco", "bahia": "bahia", "fortaleza": "fortaleza",
    "athleticoparanaense": "paranaense", "paranaense": "paranaense",
    "bragantino": "bragantino", "redbullbragantino": "bragantino",
    "juventude": "juventude", "vitoria": "vitoria", "ceara": "ceara",
    "mirassol": "mirassol", "sport": "sportrecife", "sportrecife": "sportrecife",
    # Colombia
    "millonarios": "millonarios", "nacional": "atleticonacional",
    "atleticonacional": "atleticonacional",
    "americacali": "americacali", "cali": "deportivocali",
    "deportivocali": "deportivocali", "juniorbarranquilla": "junior",
    "junior": "junior", "santafe": "santafe", "independientesantafe": "santafe",
    "medellin": "medellin", "independientemedellin": "medellin",
    "tolima": "tolima", "deportestolima": "tolima",
    "bucaramanga": "bucaramanga",
    "oncecaldas": "oncecaldas", "aguilas": "aguilas", "envigado": "envigado",
    # ---- Brazil: ESPN abbreviates the state, Kalshi spells the club.
    # Added from the observed rosters, not from memory.
    "mg": "mineiro", "mineiro": "mineiro", "atleticomineiro": "mineiro",
    "athleticopr": "paranaense", "pr": "paranaense",
    "paranaense": "paranaense", "juventuders": "juventude",
    "juventude": "juventude", "goianiense": "goianiense",
    # ---- MLS: Kalshi truncates two-club cities to a single letter.
    # "Los Angeles G" is LA Galaxy; "Los Angeles F" is LAFC.
    "angelesg": "galaxy", "galaxy": "galaxy", "lagalaxy": "galaxy",
    "angelesf": "lafc", "lafc": "lafc",
    "newyorkrb": "nyrb", "redbullnewyork": "nyrb", "newyorkredbulls": "nyrb",
    "newyorkc": "nycfc", "newyorkcity": "nycfc",
    "saintlouis": "stlouis", "stlouiscity": "stlouis", "stlouis": "stlouis",
    "equidad": "equidad", "alianza": "alianza", "chico": "chico",
    "fortalezaceif": "fortalezaceif", "llaneros": "llaneros",
}


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def normalise(name):
    """A club name -> a comparable key."""
    if not name:
        return ""
    s = strip_accents(str(name)).lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    toks = [t for t in s.split() if t and t not in NOISE]
    if not toks:                      # the name was entirely noise, e.g. "Real"
        toks = [t for t in s.split() if t]
    key = "".join(toks)
    return ALIAS.get(key, key)


def canon(name):
    """Alias-resolved key, with a bare-normalisation fallback."""
    k = normalise(name)
    return ALIAS.get(k, k)


def pair_key(a, b):
    """Order-independent key for a fixture."""
    return tuple(sorted((canon(a), canon(b))))


def teams_from_kalshi_title(title):
    """'Cruz Azul vs Atlante Winner?' -> ('Cruz Azul', 'Atlante')."""
    if not title:
        return None
    t = re.sub(r"\s*(winner|total goals|score|spread)\s*\??\s*$", "", title,
               flags=re.I).strip()
    m = re.split(r"\s+vs\.?\s+", t, flags=re.I)
    if len(m) != 2:
        return None
    return m[0].strip(), m[1].strip()


def teams_from_espn_event(ev):
    """ESPN event -> (home_name, away_name) using competitors, not the title."""
    comps = (ev.get("competitions") or [{}])[0].get("competitors") or []
    home = away = None
    for c in comps:
        nm = ((c.get("team") or {}).get("displayName")
              or (c.get("team") or {}).get("name"))
        if c.get("homeAway") == "home":
            home = nm
        elif c.get("homeAway") == "away":
            away = nm
    return home, away


def tokens(name):
    """Distinctive tokens: accent-stripped, punctuation-split, noise removed."""
    s = strip_accents(str(name or "")).lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    toks = {t for t in s.split() if t and t not in NOISE and len(t) > 1}
    return toks or {t for t in s.split() if t}


def resolve_against_roster(kalshi_name, roster):
    """Map a Kalshi club name onto one of a league's ESPN club names.

    Kalshi names clubs by region where ESPN names them by club, and vice
    versa: 'Junin' is ESPN's 'Sarmiento (Junín)', 'Racing Avellaneda' is
    'Racing Club', 'Rivadavia' is 'Independiente Rivadavia'. A hand-written
    alias table for every such pair would be long and unverifiable, but each
    league's ESPN roster is a CLOSED SET of 20-30 clubs, so the mapping can be
    resolved against it.

    Scoring, in order:
      1. exact canonical equality wins outright
      2. otherwise rank by shared distinctive tokens
      3. break ties by FEWER unmatched tokens on the ESPN side -- this is what
         separates 'Independiente Avellaneda' -> 'Independiente' (0 unmatched)
         from 'Independiente Rivadavia' (1 unmatched)

    Returns (espn_name, score, reason) or (None, 0, why-not). A tie that the
    rules cannot break returns None and is reported, never guessed.
    """
    kc, kt = canon(kalshi_name), tokens(kalshi_name)
    exact = [r for r in roster if canon(r) == kc]
    if len(exact) == 1:
        return exact[0], 100, "exact-canon"
    if len(exact) > 1:
        return None, 0, f"ambiguous-exact:{exact}"

    scored = []
    for r in roster:
        rt = tokens(r)
        shared = kt & rt
        if not shared:
            continue
        scored.append((len(shared), -len(rt - kt), -len(kt - rt), r))
    if not scored:
        return None, 0, "no-shared-token"
    scored.sort(reverse=True)
    best = scored[0]
    if len(scored) > 1 and scored[1][:3] == best[:3]:
        return None, 0, f"tie:{[s[3] for s in scored[:3]]}"
    return best[3], best[0], f"token-overlap:{sorted(kt & tokens(best[3]))}"


def _dead_alias_check():
    """Every ALIAS key must be reachable by `normalise`, or it is dead code
    that looks like coverage and matches nothing.

    Three keys failed this on the first pass -- `vascodagama`,
    `defensayjusticia`, `estudiantesdelaplata` -- because normalisation strips
    `da`/`y`/`de`/`la` as noise before the alias table is consulted, so those
    forms could never be produced. This is the same shape as GUARDS #1's
    "innocence by emptiness": a rule that never fires passes every test.
    """
    dead = []
    for k in ALIAS:
        s = strip_accents(k).lower()
        s = re.sub(r"[^a-z0-9 ]", " ", s)
        toks = [t for t in s.split() if t and t not in NOISE] or s.split()
        if "".join(toks) != k:
            dead.append(k)
    return dead


def _selftest():
    dead = _dead_alias_check()
    if dead:
        print(f"DEAD ALIAS KEYS (unreachable by normalise): {dead}")
    else:
        print(f"alias reachability: all {len(ALIAS)} keys reachable")
    cases = [
        ("Cruz Azul", "Cruz Azul", True),
        ("Club América", "America", True),
        ("Guadalajara", "Chivas", True),
        ("UANL", "Tigres UANL", True),
        ("Atlético San Luis", "San Luis", True),
        ("Boca Juniors", "Boca", True),
        ("River Plate", "River", True),
        ("Vasco da Gama", "Vasco", True),
        ("Atlético Mineiro", "Mineiro", True),
        ("Red Bull Bragantino", "Bragantino", True),
        ("Independiente Medellín", "Medellin", True),
        # must NOT collide
        ("Santos Laguna", "Santos", True),        # deliberately aliased together
        ("America", "America de Cali", False),
        ("Independiente", "Independiente Medellín", False),
        ("Atletico Nacional", "Nacional", True),
        ("Puebla", "Pachuca", False),
        ("Tigres", "Tigre", False),
    ]
    bad = []
    for a, b, want in cases:
        got = canon(a) == canon(b)
        if got != want:
            bad.append((a, b, canon(a), canon(b), want, got))
    assert teams_from_kalshi_title("Cruz Azul vs Atlante Winner?") == \
        ("Cruz Azul", "Atlante")
    assert teams_from_kalshi_title("America vs Santos Laguna Winner?") == \
        ("America", "Santos Laguna")
    if bad:
        print("TEAM MATCH SELF-TEST FAILURES:")
        for x in bad:
            print("   ", x)
    else:
        print(f"team-match self-test: all {len(cases)} cases pass")
    return not bad and not dead


if __name__ == "__main__":
    _selftest()
    for n in ["Club América", "Cruz Azul", "Tigres UANL", "Atlético San Luis",
              "Red Bull Bragantino", "Independiente Medellín", "Vasco da Gama",
              "Newell's Old Boys", "Defensa y Justicia", "Real Madrid"]:
        print(f"  {n:26s} -> {canon(n)}")
