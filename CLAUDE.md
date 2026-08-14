# Notely Platform — Projektkontext

## Was das ist
Lernprojekt von Burhan (Jakala Germany), Ziel: **DevOps Engineer werden**.
Die FastAPI-Notiz-App ist nur das Vehikel. Es geht um den kompletten Zyklus:
Code → Container → CI/CD → Kubernetes → Observability.

## ⚠️ Arbeitsweise — bitte einhalten
- **Du erklärst, Burhan tippt.** Schreibe **keinen** Code direkt in Dateien, außer er
  bittet ausdrücklich darum. Gib Dateiinhalte in Code-Blöcken aus und begründe jede
  Entscheidung. Das *Warum* ist wichtiger als das *Was* — es ist ein Lernprojekt.
- Antworte auf **Deutsch**.
- Wenn mehrere Terminals nötig sind, sag bei jedem Befehl dazu, in welches er gehört.
- Nach jedem Schritt, der etwas erzeugt, eine **Kontrolle** nennen (`ls`, `wc -l`,
  `git log`, `kubectl get`, `podman ps`). Erfahrung: Fehler standen mehrfach in einer
  Zahl der Werkzeugausgabe, die überlesen wurde („2 files changed, 18 insertions“ bei
  einem halb gespeicherten Dockerfile; „4 files changed“, als eine Datei im Merge fehlte).
- **Reihenfolge erzwingen, nicht nur empfehlen.** Mehrzeilige Befehlsblöcke, bei denen
  ein Zwischenschritt auf GitHub passieren muss, wurden mehrfach am Stück ausgeführt.
  Lieber Blöcke trennen und Prüfpunkte dazwischen setzen.
- Branch pro Etappe + Pull Request. Nach dem Merge den **„Delete branch“-Knopf im PR**
  benutzen (erzwingt die richtige Reihenfolge).
- Fehlermeldungen gemeinsam lesen statt nur die Lösung nennen — das ist ausdrücklich Teil
  des Lernziels. Bei einem Fehler immer in dieser Reihenfolge: (1) was die Meldung
  **wörtlich** sagt, (2) was wirklich passiert ist, (3) der Fix und warum er greift,
  (4) welcher Befehl es selbst gezeigt hätte, (5) **Fehlerklasse benennen**, damit der
  Einzelfall zu Wissen wird.
- **Knapp, aber technisch tief.** Keine Wiederholungen, keine Optionslisten, keine
  Abschluss-Zusammenfassungen — dafür Erklärungen *zeilenweise* und Fachbegriffe beim Namen
  (DSN, folded block scalar, nameReference-Transformer), damit sie nachschlagbar und im
  Bewerbungsgespräch benutzbar sind. Gekürzt wird Prosa, nicht Tiefe.
- **Kein `gh auth login`.** Firmenrechner, das Org-Repo enthält sensible Daten. Lokal lesen
  und prüfen ist in Ordnung; `push`, `gh pr create`, Merge und Branch-Löschen macht Burhan
  selbst. CI-Logs nicht selbst abrufen, sondern danach fragen. (*least privilege* ist hier
  selbst der Lerninhalt.)

## Umgebung
- macOS arm64, Firmenrechner, VS Code.
- **Docker Desktop ist bei Jakala lizenzpflichtig und vom Rechner entfernt.**
  Ersatz: **Podman 6.0.2 (rootful) + Podman Desktop**. Niemals Docker-Desktop-Lösungen
  vorschlagen. `docker`-CLI existiert nicht.
- `export KIND_EXPERIMENTAL_PROVIDER=podman` steht in `~/.zshrc`.
- Image in den kind-Cluster bringen (Podman präfixt lokale Images mit `localhost/`,
  Kubernetes erwartet `docker.io/library/`):
  ```
  podman build -t notely:dev .
  podman tag localhost/notely:dev docker.io/library/notely:dev
  podman save docker.io/library/notely:dev -o /tmp/notely.tar
  kind load image-archive /tmp/notely.tar --name notely
  kubectl rollout restart deployment/notely      # Tag bleibt "dev" → sonst keine Änderung
  podman exec notely-control-plane crictl images # Kontrolle
  ```
  `rollout restart` ist **nur** nötig, wenn sich ausschließlich der Image-*Inhalt* ändert.
  Ändert ein `configMapGenerator`/`secretGenerator` seinen Hash, ändert sich das
  Pod-Template und Kubernetes rollt von selbst. Merksatz: **Kubernetes reagiert auf
  geänderte Spezifikation, nicht auf geänderten Inhalt.**
- Lokale Entwicklungs-DB: Podman-Container `notely-db` auf `localhost:5432`
  (DB/User `notely`, Passwort `notely`), zusätzlich Datenbank `notely_test` für pytest.
- `.venv` wird **nur** für `pytest` und `ruff` gebraucht — nicht für podman/kubectl/kind/git.
- App im Cluster erreichbar unter **http://localhost:8080** (ingress-nginx, kein port-forward).
- Cluster: kind, Name `notely`, Config in `cluster/kind-cluster.yaml`.

## Aufbau
```
app/            main.py (FastAPI), models.py (SQLAlchemy + Pydantic), db.py (Engine/Session)
tests/          conftest.py, test_api.py (7 Tests, prüfen nur HTTP-Verhalten)
cluster/        kind-cluster.yaml   (kind-CLI-Config, KEINE k8s-Ressource)
k8s/base/       deployment.yaml, service.yaml, ingress.yaml, kustomization.yaml
k8s/postgres/   pvc.yaml, deployment.yaml, service.yaml, kustomization.yaml
k8s/overlays/   local/kustomization.yaml, prod/kustomization.yaml
.github/workflows/ci.yml
Dockerfile, .dockerignore, requirements.txt, requirements-dev.txt
```

## Was schon fertig ist (in `main`, PR #12 = `7e70e47`)
1. **API + Tests** — `/healthz`, `/readyz`, CRUD `/notes`, `APP_VERSION` aus Env. 7 pytest-Tests, ruff sauber.
2. **Container** — Multi-Stage Dockerfile, `python:3.12-slim`, non-root uid 10001,
   `ARG/ENV APP_VERSION` ganz unten (Layer-Cache), exec-form CMD, `--host 0.0.0.0`.
   Größe: **239 MB unkomprimiert** (`podman images`, arm64) — davon 148,6 MB geerbt von
   `python:3.12-slim`, 90,5 MB das kopierte venv, 20 kB eigener Code. Die früher hier
   notierten „58,9 MB" waren eine **komprimierte** Größe; auf dieser Basis ist eine
   On-Disk-Größe unter 148 MB unmöglich. **Kennzahlen immer mit Werkzeug und Einheit
   notieren** — eine nackte Zahl hat schon eine Fehlersuche ohne Fehler ausgelöst.
3. **CI** — `ci.yml`: Job `quality` (ruff + pytest), Job `image` (`needs: quality`,
   `packages: write`, GHCR-Login via `secrets.GITHUB_TOKEN`, metadata-action;
   Push nur wenn kein PR). Tags: `sha` (unveränderlich, für Deployments), `pr-<n>`, `latest` nur auf main.
4. **Kubernetes lokal** — Deployment (2 Replicas, Liveness `/healthz`, Readiness `/readyz`,
   requests/limits, runAsNonRoot, readOnlyRootFilesystem, drop ALL), Service, ConfigMap,
   ingress-nginx. Danach **Kustomize** (base + overlays local/prod). `configMapGenerator`
   hängt einen Inhalts-Hash an → Config-Änderung löst den Rollout automatisch aus.
5. **Postgres + App auf SQL** (Etappe 5, Teil A+B — PR #12) — `k8s/postgres/` mit PVC,
   `strategy: Recreate`, `pg_isready`-Probes; `app/db.py` (Engine/Session, `DATABASE_URL`
   aus Env, `pool_pre_ping=True`), SQLAlchemy-`Note`, alle Endpunkte auf Sessions;
   `notely-db`-Secret per `secretGenerator` + `envFrom.secretRef`; Postgres-Service-Container
   im CI-Job `quality`.

   **Im Cluster bewiesen, in drei Stufen** (jede sagt etwas anderes aus):
   1. 6× `GET /notes` → *immer* dieselbe UUID, nie `[]` → Zustand ist zwischen den 2 Replicas
      geteilt. Vorher wechselte es ab, weil der Service Round-Robin auf zwei Pods verteilt,
      die jeder ihr eigenes Dict im Speicher hatten. **Zustand im Prozess und horizontale
      Skalierung schließen sich aus** — das ist die Kernlektion der Etappe.
   2. `kubectl delete pod -l app=notely` → Notiz überlebt → Zustand hat den **Prozess** verlassen.
   3. `kubectl delete pod -l app=postgres` → Notiz überlebt → Zustand liegt im **PVC**.

   **Nebenbefund, der das Probe-Design bestätigt:** Nach (3) stand bei beiden App-Pods
   `RESTARTS 0`. Grund: `livenessProbe` → `/healthz` fasst die DB **nicht** an und blieb grün,
   `readinessProbe` → `/readyz` (`SELECT 1`) wurde rot und nahm die Pods aus dem Service.
   Würde `/healthz` die DB prüfen, hätte Kubernetes gesunde App-Pods getötet, weil die
   *Datenbank* weg war → Kaskadenausfall. **Regel: Liveness fragt „bin ich kaputt?",
   Readiness fragt „kann ich gerade arbeiten?" — fremde Abhängigkeiten nur in Readiness.**

## Wo wir gerade stehen
`main` = `7e70e47` (Merge PR #12), Arbeitsverzeichnis sauber, Etappe 5 Teil A+B fertig.
Nächster Schritt: **Alembic** (siehe unten).

## 🔴 Offene Punkte
1. **`tests/conftest.py` — stille Umgebungsübernahme.** Zeile 7 nutzt
   `os.environ.setdefault`, eine bereits gesetzte `DATABASE_URL` gewinnt also. In der CI
   ist das gewollt. Lokal: wer für einen manuellen `uvicorn`-Start
   `export DATABASE_URL=...@localhost:5432/notely` macht und im selben Terminal `pytest`
   startet, lässt das `TRUNCATE TABLE notes` der Fixture auf die **Entwicklungs-DB** laufen.
   Keine Warnung, Tests grün, Daten weg. Absicherung (noch nicht eingebaut), direkt nach
   dem `setdefault`-Block:
   ```python
   assert os.environ["DATABASE_URL"].endswith("_test"), (
       "Refusing to run tests against a non-test database: "
       f"{os.environ['DATABASE_URL']}"
   )
   ```
   Bewusst eine Zusicherung statt hartem Überschreiben: die CI darf einen anderen Host
   setzen, nur das Gefährliche wird verboten.
2. **`k8s/overlays/prod` kennt kein `notely-db`-Secret.** `base/deployment.yaml` verlangt es
   seit PR #12 per `envFrom`. `kubectl kustomize k8s/overlays/prod` läuft trotzdem durch
   (kustomize prüft keine Existenz), die Pods gingen aber in `CreateContainerConfigError`.
   Bewusst offen gelassen, statt ein zweites Klartext-Passwort ins Git zu schreiben —
   gehört zusammen mit echter Secret-Verwaltung erledigt.
3. **Image-Diät**, kein Blocker: die 90,5 MB des venv enthalten `pip`, `setuptools` und
   `.pyc`-Dateien, die zur Laufzeit niemand braucht. `pip install --no-compile` plus
   `pip uninstall -y pip setuptools` im Builder holen ~25 MB.

## Danach geplant (Etappe 5, Rest)
- **Alembic** statt `Base.metadata.create_all` (`app/main.py`, `lifespan`) — nächster Schritt.
  Warum `create_all` nicht reicht: es legt **fehlende Tabellen** an und tut sonst nichts —
  keine Spaltenänderung, keine Datenmigration. Nach einem Schema-Zusatz passiert beim Deploy
  nichts, und der erste `SELECT` stirbt an `column does not exist`. Dazu läuft es derzeit in
  **beiden** Pods gleichzeitig = Wettrennen. Migrationen gehören **einmal** vor den Rollout,
  als k8s-`Job` oder `initContainer`, nicht in jeden Pod.
- Trivy-Image-Scan + SBOM in der CI.
- Strukturiertes JSON-Logging, Prometheus `/metrics`.
- Echte Secret-Verwaltung: SOPS / Sealed Secrets / External Secrets Operator.
  (Aktuell steht das Postgres-Passwort im Klartext im Git — bewusst, nur für die lokale
  Wegwerf-DB, und Burhan weiß, dass das sonst nicht geht.)
- `README.md` füllen (aktuell 17 Bytes): Werkzeuge, lokaler Start, Architektur.
- GitOps: CI trägt den `sha`-Tag ins prod-Overlay ein.

## Konventionen, die sich bewährt haben
- Vor jedem Löschen (Branch, Datei, Cluster): **„Wo ist die Kopie, und habe ich sie mit
  eigenen Augen gesehen?"**
- Fehlermeldungen: kustomize von **innen nach außen** lesen; Python-Tracebacks von der
  **letzten Zeile** und der ersten Zeile mit eigenem Dateipfad; Werkzeugketten von der
  **ersten** roten Zeile.
- `curl -s` unterdrückt auch Fehler → beim Debuggen `-v`; `; echo` für lesbare Ausgabe.
- **Erste Frage bei jedem Fehler: „wer spricht?"** Jede Meldung kommt aus *einer* Schicht
  (zsh → python/pytest → SQLAlchemy → psycopg → Netzwerk → Postgres, bzw. kubectl →
  kustomize → k8s-API → containerd → Prozess). Der häufigste Anfängerfehler ist nicht die
  falsche Lösung, sondern **Reparatur in der falschen Schicht**.
- **Halbiere den Weg**, statt die App zu debuggen: `podman exec notely-db pg_isready ...`
  bzw. `curl /readyz` schließt in Sekunden die Hälfte des Suchraums aus.
- Wörtlich lesen, nicht interpretieren: `connection refused` (niemand hört zu) ≠
  `authentication failed` (Passwort) ≠ `timeout` (Route/Firewall). Drei Meldungen,
  drei Ursachen.
- Eine Hypothese, **eine** Änderung, dann prüfen. Zwei Änderungen gleichzeitig, und Grün
  sagt dir nicht, welche geholfen hat.
- Sekundäre Prompts (`quote>`, `dquote>`, `heredoc>`, `pipe>`) sind kein Fehler, sondern
  „Eingabe unvollständig" → `Ctrl+C`. Wo Anführungszeichen nur Kosmetik sind, weglassen;
  wo sie Bedeutung tragen (JSON in `curl -d`), sind sie Pflicht.
- **`git add -A`, nicht `git commit -am`.** `-a` merkt nur *verfolgte* Dateien vor; eine
  neue Datei mit `??` fehlt still im Commit — lokal läuft alles, die CI stirbt an
  `ModuleNotFoundError`. Danach zählen: `git diff --cached --stat | tail -1`.
- **Branch löschen nur mit `-d`, nie `-D`.** `-d` weigert sich bei nicht gemergter Arbeit —
  diese Weigerung ist Information, keine Störung.
- Merksätze aus dem Projekt: „Editor schreibt, Terminal führt aus, Git entscheidet.“ ·
  „Grüner Build ≠ brauchbares Ergebnis.“ · „Ein sauberer `diff` beweist, dass die
  Beschreibung stimmt, nicht dass das Laufende ihr entspricht.“ · „Wo du dich auf Disziplin
  verlassen müsstest, such nach einer Konstruktion, die den Fehler unmöglich macht.“
