"""Tests for the join logic, especially team-name matching (backlog #6).

The real ESPN rosters are used, because a matcher tested only against invented
names proves nothing about the names it will actually see.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import teammatch as TM  # noqa: E402

ARG = ["Aldosivi", "Argentinos Juniors", "Atlético Tucumán", "Banfield",
       "Barracas Central", "Belgrano (Córdoba)", "Boca Juniors",
       "Central Córdoba (Santiago del Estero)", "Defensa y Justicia",
       "Deportivo Riestra", "Estudiantes de La Plata",
       "Estudiantes de Río Cuarto", "Gimnasia (Mendoza)", "Gimnasia La Plata",
       "Huracán", "Independiente", "Independiente Rivadavia",
       "Instituto (Córdoba)", "Lanús", "Newell's Old Boys", "Platense",
       "Racing Club", "River Plate", "Rosario Central", "San Lorenzo",
       "Sarmiento (Junín)", "Talleres (Córdoba)", "Tigre", "Unión (Santa Fe)",
       "Vélez Sarsfield"]

COL = ["Alianza FC", "América de Cali", "Atlético Bucaramanga",
       "Atlético Junior", "Atlético Nacional", "Boyacá Chicó FC",
       "Cúcuta Deportivo", "Deportes Tolima", "Deportivo Cali",
       "Deportivo Pasto", "Deportivo Pereira", "Fortaleza CEIF",
       "Independiente Medellín", "Independiente Santa Fe",
       "Internacional de Bogotá", "Jaguares de Córdoba", "Llaneros FC",
       "Millonarios", "Once Caldas", "Envigado"]

# (kalshi name, roster, expected ESPN name)
CASES = [
    ("Racing Avellaneda", ARG, "Racing Club"),
    ("Rio Cuarto", ARG, "Estudiantes de Río Cuarto"),
    ("Junin", ARG, "Sarmiento (Junín)"),
    ("Mendoza", ARG, "Gimnasia (Mendoza)"),
    ("Rivadavia", ARG, "Independiente Rivadavia"),
    ("Independiente Avellaneda", ARG, "Independiente"),
    ("Rosario", ARG, "Rosario Central"),
    ("San Lorenzo de Almagro", ARG, "San Lorenzo"),
    ("Central Cordoba", ARG, "Central Córdoba (Santiago del Estero)"),
    ("Tucuman", ARG, "Atlético Tucumán"),
    ("Belgrano de Cordoba", ARG, "Belgrano (Córdoba)"),
    ("Union Santa Fe", ARG, "Unión (Santa Fe)"),
    ("Gimnasia La Plata", ARG, "Gimnasia La Plata"),
    ("Estudiantes La Plata", ARG, "Estudiantes de La Plata"),
    ("Velez Sarsfield", ARG, "Vélez Sarsfield"),
    ("Newell's Old Boys", ARG, "Newell's Old Boys"),
    ("Boca Juniors", ARG, "Boca Juniors"),
    ("River Plate", ARG, "River Plate"),
    ("Talleres", ARG, "Talleres (Córdoba)"),
    ("Instituto", ARG, "Instituto (Córdoba)"),
    ("Medellin", COL, "Independiente Medellín"),
    ("Santa Fe", COL, "Independiente Santa Fe"),
    ("Nacional", COL, "Atlético Nacional"),
    ("Junior", COL, "Atlético Junior"),
    ("Tolima", COL, "Deportes Tolima"),
    ("Bucaramanga", COL, "Atlético Bucaramanga"),
    ("Pasto", COL, "Deportivo Pasto"),
    ("Pereira", COL, "Deportivo Pereira"),
    ("Once Caldas", COL, "Once Caldas"),
    ("Chico", COL, "Boyacá Chicó FC"),
]

# these MUST NOT resolve to each other
NEGATIVE = [
    ("Gimnasia La Plata", ARG, "Gimnasia (Mendoza)"),
    ("Estudiantes La Plata", ARG, "Estudiantes de Río Cuarto"),
    ("Independiente Avellaneda", ARG, "Independiente Rivadavia"),
    ("America de Cali", COL, "Atlético Nacional"),
]


def run():
    ok = fail = 0
    print(f"{'kalshi':28s} -> {'resolved':38s} {'expected':38s} verdict")
    for name, roster, want in CASES:
        got, score, why = TM.resolve_against_roster(name, roster)
        good = got == want
        ok, fail = (ok + good, fail + (not good))
        print(f"{name[:28]:28s} -> {str(got)[:38]:38s} {want[:38]:38s} "
              f"{'ok' if good else '**FAIL** ' + why}")
    print(f"\npositive cases: {ok} pass, {fail} FAIL")

    nok = nfail = 0
    for name, roster, forbidden in NEGATIVE:
        got, _, _ = TM.resolve_against_roster(name, roster)
        good = got != forbidden
        nok, nfail = (nok + good, nfail + (not good))
        if not good:
            print(f"**NEGATIVE FAIL** {name} wrongly resolved to {forbidden}")
    print(f"negative cases: {nok} pass, {nfail} FAIL")

    dead = TM._dead_alias_check()
    print(f"dead alias keys: {dead if dead else 'none'}")
    print(f"\nTOTAL: {'ALL PASS' if not (fail or nfail or dead) else 'FAILURES PRESENT'}")
    return not (fail or nfail or dead)


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
