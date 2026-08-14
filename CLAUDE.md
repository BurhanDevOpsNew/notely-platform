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
  des Lernziels.

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

## Was schon fertig ist (in `main`, PR #11 = `142fd69`)
1. **API + Tests** — `/healthz`, `/readyz`, CRUD `/notes`, `APP_VERSION` aus Env. 7 pytest-Tests, ruff sauber.
2. **Container** — Multi-Stage Dockerfile, `python:3.12-slim`, non-root uid 10001,
   `ARG/ENV APP_VERSION` ganz unten (Layer-Cache), exec-form CMD, `--host 0.0.0.0`. 58,9 MB.
3. **CI** — `ci.yml`: Job `quality` (ruff + pytest), Job `image` (`needs: quality`,
   `packages: write`, GHCR-Login via `secrets.GITHUB_TOKEN`, metadata-action;
   Push nur wenn kein PR). Tags: `sha` (unveränderlich, für Deployments), `pr-<n>`, `latest` nur auf main.
4. **Kubernetes lokal** — Deployment (2 Replicas, Liveness `/healthz`, Readiness `/readyz`,
   requests/limits, runAsNonRoot, readOnlyRootFilesystem, drop ALL), Service, ConfigMap,
   ingress-nginx. Danach **Kustomize** (base + overlays local/prod). `configMapGenerator`
   hängt einen Inhalts-Hash an → Config-Änderung löst den Rollout automatisch aus.

## Wo wir gerade stehen — Branch `feature/postgres`
Letzter Commit: `4f30752 feat: postgres with persistent volume for local development`
(Postgres-Manifeste; Persistenz bewiesen: Tabelle angelegt, Pod gelöscht, Daten überlebten).

**Uncommittete Arbeit (Etappe 5, Teil B — App auf SQL):**
- `app/db.py` (neu): `DATABASE_URL` aus Env, `create_engine(..., pool_pre_ping=True)`,
  `sessionmaker(expire_on_commit=False)`, `Base`, `get_session()`-Dependency.
- `app/models.py`: SQLAlchemy-`Note` (Tabelle `notes`) + Pydantic `NoteCreate`/`NoteRead`.
- `app/main.py`: alle Endpunkte auf SQLAlchemy; `lifespan` ruft `Base.metadata.create_all`;
  **`/readyz` macht `SELECT 1` und gibt 503 zurück, wenn die DB weg ist** (lokal verifiziert:
  `/healthz` 200, `/readyz` 503 bei gestoppter DB).
- `requirements.txt`: + `sqlalchemy==2.0.36`, `psycopg[binary]==3.2.3`
- `tests/conftest.py`: `os.environ.setdefault("DATABASE_URL", ...notely_test)` **vor** den
  App-Imports (`# noqa: E402`), Fixture legt Schema an und macht `TRUNCATE TABLE notes`.
  `tests/test_api.py` blieb unverändert — die Tests prüfen HTTP-Verhalten, nicht Interna.
- `.github/workflows/ci.yml`: Postgres-Service-Container eingefügt.

## 🔴 Offene Punkte / bekannte Fehler — bitte zuerst
1. **`ci.yml` ist kaputt:** Der `services:`-Block steht auf Zeile 12 mit 2 Leerzeichen
   Einrückung, also als eigener **Job** neben `quality` und `image`. Er gehört **in** den
   Job `quality`, auf dieselbe Ebene wie `runs-on:` (4 Leerzeichen).
2. **`ci.yml`:** Dem Schritt `Test` fehlt noch
   `env: DATABASE_URL: postgresql+psycopg://notely:notely@localhost:5432/notely_test`
3. **`k8s/base/deployment.yaml`:** `envFrom` hat nur `configMapRef: notely-config`.
   Es fehlt `- secretRef: name: notely-db`.
4. **`k8s/overlays/local/kustomization.yaml`:** Es fehlt ein zweiter `secretGenerator`-Eintrag
   `notely-db` mit
   `DATABASE_URL=postgresql+psycopg://notely:nur-lokal-zum-lernen@postgres:5432/notely`
   (Service-Name `postgres`, nicht localhost; Passwort muss zu `postgres-credentials` passen).
5. `pytest -q` und `ruff check .` lokal noch nicht grün gelaufen (venv war nicht aktiv).
6. Danach: Image neu bauen + `kind load` + `rollout restart` + `kubectl apply -k k8s/overlays/local`,
   dann beweisen: Notiz anlegen → `kubectl delete pod -l app=notely` → Notiz ist noch da **und**
   erscheint bei *jedem* Aufruf (vorher abwechselnd `[]`, weil jeder Pod seinen eigenen Speicher hatte).
7. Erst dann committen, PR, mergen.

## Danach geplant (Etappe 5, Rest)
- **Alembic** statt `Base.metadata.create_all` (dieses ist ausdrücklich als Übergangslösung
  markiert); Migrationen als k8s-`Job` oder `initContainer`.
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
- Merksätze aus dem Projekt: „Editor schreibt, Terminal führt aus, Git entscheidet.“ ·
  „Grüner Build ≠ brauchbares Ergebnis.“ · „Ein sauberer `diff` beweist, dass die
  Beschreibung stimmt, nicht dass das Laufende ihr entspricht.“ · „Wo du dich auf Disziplin
  verlassen müsstest, such nach einer Konstruktion, die den Fehler unmöglich macht.“
