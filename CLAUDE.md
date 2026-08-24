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
  Vor `kubectl apply -k k8s/overlays/local` gehört seit Etappe 6 immer:
  `kubectl delete job notely-migrate --ignore-not-found` (Job-`spec` ist unveränderlich).

  `rollout restart` ist **nur** nötig, wenn sich ausschließlich der Image-*Inhalt* ändert.
  Ändert ein `configMapGenerator`/`secretGenerator` seinen Hash, ändert sich das
  Pod-Template und Kubernetes rollt von selbst. Merksatz: **Kubernetes reagiert auf
  geänderte Spezifikation, nicht auf geänderten Inhalt.**
- **Podman läuft auf macOS in einer VM.** Ein Container sieht das Dateisystem der VM,
  nicht das des Macs — geteilt wird standardmäßig nur `$HOME`. `podman save -o /tmp/x.tar`
  schreibt auf den **Mac**, `-v /tmp:/scan` hängt das leere `/tmp` der **VM** ein → Datei
  nicht gefunden. Dateien für Container also unter `$HOME` ablegen. Zweitens: niemals über
  `/tmp` im Container mounten — Programme brauchen das selbst (Trivy scheiterte an
  `mkdir /tmp/trivy-…: permission denied`). Einhängepunkte in ein eigenes Verzeichnis.
- Lokale Entwicklungs-DB: Podman-Container `notely-db` auf `localhost:5432`
  (DB/User `notely`, Passwort `notely`), zusätzlich Datenbank `notely_test` für pytest.
- `.venv` wird **nur** für `pytest` und `ruff` gebraucht — nicht für podman/kubectl/kind/git.
- App im Cluster erreichbar unter **http://localhost:8080** (ingress-nginx, kein port-forward).
- Cluster: kind, Name `notely`, Config in `cluster/kind-cluster.yaml`.

## Aufbau
```
app/            main.py (FastAPI), models.py (SQLAlchemy + Pydantic), db.py (Engine/Session)
tests/          conftest.py, test_api.py (notely); stats/tests/ (stats, mit Test-Doppel)
                zusammen 17 Tests, prüfen nur HTTP-Verhalten
cluster/        kind-cluster.yaml   (kind-CLI-Config, KEINE k8s-Ressource)
alembic/        env.py (DB-URL aus Env, target_metadata), script.py.mako (Vorlage,
                deutsch — sonst kommt jede neue Migration englisch heraus), versions/
alembic.ini     Konfig; `sqlalchemy.url` ist bewusst auskommentiert
k8s/base/       deployment.yaml, service.yaml, ingress.yaml, job.yaml, kustomization.yaml
k8s/postgres/   pvc.yaml, deployment.yaml, service.yaml, kustomization.yaml
k8s/monitoring/ rbac.yaml, prometheus.yml (Scrape-Config), alerts.yml (Regeln),
                alertmanager.yml (Routing), deployment.yaml, service.yaml,
                alertmanager-deployment.yaml (Deployment + Service),
                webhook-logger.yaml (Alarm-Empfänger, loggt Webhook-POSTs), kustomization.yaml
k8s/argocd/     application.yaml (ArgoCD-Application, wird von Hand angewendet)
k8s/overlays/   local/, prod/, argocd/: kustomization.yaml; local+prod mit *.enc.env
                (SOPS-verschlüsselt, die entschlüsselten *.env sind gitignoriert);
                argocd/ ohne secretGenerator (ArgoCD kann kein SOPS)
docs/           technologien.md (Lernnotizen: jede Technologie einfach erklärt)
.sops.yaml      creation_rules + öffentlicher age-Schlüssel
.github/workflows/ci.yml
Dockerfile, .dockerignore, requirements.txt, requirements-dev.txt
```

## Was schon fertig ist (in `main`, PR #39 = `1f56c30`)
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

6. **Alembic statt `create_all`** (Etappe 6, Branch `feature/alembic`) — `alembic/env.py`
   liest `DATABASE_URL` aus der Umgebung (`config.set_main_option`, `%` → `%%` wegen
   configparser) und scheitert laut, wenn sie fehlt; `target_metadata = Base.metadata`.
   Erste Revision `8896812e8bac` legt `notes` an. `lifespan` und `create_all` aus
   `app/main.py` entfernt — **die App ist nicht mehr fürs Schema zuständig.**

   **Der Import, an dem alles hängt:** `from app.models import Note  # noqa: F401` in
   `env.py`. SQLAlchemy registriert eine Tabelle in `Base.metadata` erst beim Import des
   Moduls. Fehlt die Zeile, sind die Metadaten leer, und `--autogenerate` liest das als
   „Tabelle soll weg" → es erzeugt ein `drop_table("notes")`. Ein vermeintlich ungenutzter
   Import, dessen Entfernen Daten löscht. Deshalb `noqa` **und** Kommentar.

   **`--autogenerate` ist ein Entwurf, keine Wahrheit.** Es erkennt keine Umbenennungen:
   aus `body` → `content` macht es `drop_column` + `add_column`, also stiller Datenverlust.
   Ebenfalls blind bei `server_default` und CHECK-Constraints. Jede generierte Migration
   wird gelesen, bevor sie läuft.

   **Tests fahren die Migration mit** — `tests/conftest.py` ruft `command.upgrade(cfg, "head")`
   in einer `scope="session"`-Fixture, die `client` per Parameter anfordert (deklarierte
   Abhängigkeit statt Verlass auf Fixture-Reihenfolge). Damit prüft die CI die Migrationen
   automatisch mit; in `ci.yml` steht dafür bewusst nichts Zusätzliches. Dazu die
   `assert …endswith("_test")`-Absicherung gegen ein `TRUNCATE` auf der Entwicklungs-DB.

   **Migration im Cluster: `k8s/base/job.yaml`**, `command: ["alembic","upgrade","head"]`,
   gleiches Image wie die App. Kein `initContainer` — der liefe in *jedem* der 2 Pods,
   also zwei gleichzeitige Migrationen. `restartPolicy: Never` (neuer Pod je Versuch, Logs
   bleiben lesbar), `backoffLimit: 3`, `ttlSecondsAfterFinished: 300`.

   **Bewiesen:** `notes`, `alembic_version` und das Überbleibsel `persistenz_test` in der
   Cluster-DB gelöscht → Job neu angewendet → `COMPLETIONS 1/1`, Log
   `Running upgrade  -> 8896812e8bac`, Tabellen wieder da, `GET /notes` → `[]`.
   **`[]` statt `relation "notes" does not exist` ist der Beweis** — leere Liste heißt
   „Tabelle da, nichts drin".

   **Bestehende DB übernehmen: `alembic stamp head`.** Schreibt nur die Versionsnummer in
   `alembic_version`, führt kein SQL aus. Nötig, weil die Cluster-DB die von `create_all`
   angelegte Tabelle schon hatte; `upgrade head` wäre an `relation "notes" already exists`
   gestorben. Du behauptest damit, das Schema passe zur Migration — stimmt das nicht,
   merkst du es erst bei der nächsten Migration.

7. **Zweite Migration: `archived`-Spalte** (Etappe 7, Branch `feature/note-archived`) —
   `82c2ae8bf5e0`, hängt per `down_revision` an `8896812e8bac`. Migrationen sind eine
   **Kette**, nicht eine Menge von Dateien; `upgrade head` läuft sie ab der aktuellen
   Position ab. Deshalb ist die Reihenfolge unabhängig von Dateiname und Datum.

   **Die Lektion der Etappe — `default=` ≠ `server_default=`:**
   Das autogenerierte `op.add_column(..., nullable=False)` **ohne** `server_default` lief
   lokal durch (Test-DB: 0 Zeilen) und wäre im Cluster (1 Zeile) gestorben an
   `NotNullViolation: column "archived" of relation "notes" contains null values`,
   SQL: `ALTER TABLE notes ADD COLUMN archived BOOLEAN NOT NULL`.

   | | wirkt bei |
   |---|---|
   | `default=False` | `Note()` in **Python** — Postgres kennt es nicht |
   | `server_default=text("false")` | jedem `INSERT` **und** beim `ALTER TABLE` für bestehende Zeilen |

   Fix: `server_default=sa.text('false')` in der Migration **und** `server_default` im
   Modell, damit Modell und Datenbank dasselbe behaupten. Beides zusammen mit `default=`,
   damit ein frisches `Note`-Objekt in Python sofort `False` hat statt `None`.

   **Die Gewohnheit, die daraus folgt: Produktionsbedingung lokal nachbauen.** Statt zu
   deployen und im Job-Log zu suchen — eine Zeile in die Test-DB einfügen
   (`INSERT ... gen_random_uuid(), now()`), Migration laufen lassen, Fehler in Sekunden
   statt in Minuten sehen. Danach mit *derselben* Datenlage erneut → geht durch. Das
   beweist den Fix; eine geleerte Tabelle hätte das Problem nur versteckt.

   **Nebenbefund:** Der fehlgeschlagene `ALTER TABLE` hinterließ nichts — Postgres führt
   DDL transaktional aus (`Will assume transactional DDL` in jeder Alembic-Ausgabe).
   Nichts halb angelegt, Zeile unversehrt.

   **Und: die Tests haben es gemerkt.** Nach der Modelländerung ohne Migration waren
   4 von 7 rot — genau die, die `notes` anfassen. Das Modell erzeugt das SQL, also steht
   `notes.archived` sofort in jedem `SELECT`. Die 3 grünen (`/healthz`, `/readyz`,
   422-Validierung) berühren die Tabelle nie. **Welche Tests fehlschlagen, sagt dir, wo
   das Problem liegt — ohne eine Zeile Traceback zu lesen.**

8. **`PATCH /notes/{id}`** (Etappe 8, Branch `feature/patch-notes`) — drittes Schema
   `NoteUpdate` mit ausschließlich optionalen Feldern (`str | None = Field(default=None, …)`).
   Erbt bewusst **nicht** von `NoteCreate`: dort ist `title` Pflicht, hier optional — genau
   der Unterschied, den Vererbung verwischen würde. Drei Verträge für eine Tabelle:
   **Anlegen, Ändern und Lesen sind verschiedene Operationen mit verschiedenen Regeln.**

   **Die Zeile, um die es geht:**
   ```python
   for field, value in payload.model_dump(exclude_unset=True, exclude_none=True).items():
       setattr(note, field, value)
   ```
   | Option | schließt aus |
   |---|---|
   | `exclude_unset=True` | Felder, die der Client **gar nicht geschickt** hat |
   | `exclude_none=True` | Felder, die er **ausdrücklich als `null`** geschickt hat |

   Ohne `exclude_unset` enthielte das Dict alle Felder, die nicht geschickten mit `None` —
   ein `{"archived": true}` würde `title` und `body` **löschen**. Ohne `exclude_none` gäbe
   `{"title": null}` einen `IntegrityError` und HTTP 500, weil keine Spalte NULL sein darf.
   Abgesichert durch `test_patch_keeps_unmentioned_fields` — ein Test für genau eine
   Codezeile, und zwar die, deren Fehlen still Daten zerstört.

   **Getippte Pfad-Parameter prüfen vor der Funktion.** `note_id: UUID` in der Signatur →
   FastAPI antwortet auf eine ungültige ID mit 422 und
   `"loc":["path","note_id"]`, bevor `session.get` überhaupt läuft. Kein eigener Prüfcode,
   bessere Meldung.

   **Kein `apply`, kein Job** — es hat sich weder ein Manifest noch das Schema geändert,
   nur der Image-*Inhalt*. Also nur `rollout restart`. Die drei Fälle:
   Manifest → `apply -k`; Schema → `delete job` + `apply -k`; nur Image → `rollout restart`.

   Tests: 7 → **11**.

9. **Trivy + SBOM in der CI** (Etappe 9, Branch `feature/trivy-sbom`) — im Job `image`,
   **vor** `Build and push`: ein Build mit `load: true` unter dem Arbeitsnamen `notely:scan`
   (ohne `load` gäbe es kein Image, das Trivy anfassen könnte), dann drei Trivy-Läufe.

   **Zwei Läufe, zwei Aufgaben:**
   | Lauf | Optionen | Zweck |
   |---|---|---|
   | Bericht | `exit-code: 0` | zeigt **alle** Funde, macht nie rot |
   | Tor | `severity: HIGH,CRITICAL`, `ignore-unfixed: true`, `exit-code: 1` | macht rot |

   `ignore-unfixed` ist die eigentliche Entscheidung: Lücken **ohne verfügbaren Fix** werden
   ausgeblendet. **Ein Build soll nur an dem scheitern, was du auch ändern kannst** — sonst
   ist er nach dem dritten Mal rot aus fremder Schuld, und rote Builds werden ignoriert.
   Das Tor steht **vor** dem Push: ein Image mit behebbarer HIGH-Lücke erreicht die
   Registry gar nicht erst. Ein Scan danach wäre nur Statistik.

   SBOM als CycloneDX, per `upload-artifact` an den Lauf gehängt. Zweimal bauen kostet
   nichts: der Scan-Build schreibt in den gha-Cache (`cache-to`), der Push-Build liest nur.

   **Der erste echte Fund — und warum er lehrreich war:** 3× HIGH in `starlette` 0.38.6
   (CVE-2024-47874, CVE-2026-48818, CVE-2026-54283), alle mit Fix. `starlette` steht **nicht
   in `requirements.txt`** — es ist eine **transitive Abhängigkeit** von FastAPI, und
   `fastapi==0.115.0` verlangt `starlette<0.39.0`. Einzeln hochsetzen geht also nicht;
   der Weg führt über FastAPI. Fix: `fastapi==0.141.1` → zieht `starlette 1.6.0`.
   Als Folge des Sprungs: `httpx` → `httpx2==2.10.0` in `requirements-dev.txt`
   (starlettes `TestClient` warnt sonst). Die 11 Tests waren die Absicherung für einen
   Sprung über 26 FastAPI-Versionen — **deshalb kann man so ein Update überhaupt wagen.**

   **Werkzeug zum Merken:** `pip install --dry-run --report - PAKET` zeigt die Auflösung
   als JSON, ohne etwas zu installieren. Bei Versionssprüngen der Unterschied zwischen
   „ausprobieren und hoffen" und „wissen".

   **Zweiter Fund, diesmal im Basis-Image** (in Etappe 15 aufgetreten): 9× HIGH aus *einer*
   Lücke — CVE-2026-53615 in `util-linux` und seinen Bibliotheken (`libblkid1`, `libmount1`,
   `libuuid1`, `login`, `mount`, …), Debian 13.6 aus `python:3.12-slim`. Spalte
   **`Status: fixed`** ⇒ `ignore-unfixed` greift nicht, das Tor blockiert zu Recht.
   Fix: in **Stage 2** des Dockerfiles, direkt nach `FROM`:
   ```dockerfile
   RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*
   ```
   Nur Stage 2 — der Builder wird verworfen. Das `rm` muss in **dieselbe** `RUN`-Zeile:
   jede `RUN`-Anweisung ist eine Schicht, und was in einer früheren Schicht liegt, bleibt
   im Image, auch wenn eine spätere es löscht. Größe danach **253 MB** (vorher 239 MB).

   **Der Kompromiss, den man kennen muss:** `apt-get upgrade` macht den Build nicht mehr
   reproduzierbar — derselbe Dockerfile ergibt zu verschiedenen Zeitpunkten verschiedene
   Images. Wer Reproduzierbarkeit braucht, pinnt das Basis-Image auf einen Digest und
   aktualisiert bewusst. Wäre kein Fix verfügbar, wäre `.trivyignore` mit CVE-Nummer,
   Begründung und Ablaufdatum das richtige Mittel — nicht das Tor aufweichen.

10. **JSON-Logging + Prometheus `/metrics`** (Etappe 10, Branch `feature/observability`) —
    `app/observability.py`: `JsonFormatter` (jede Logzeile ein JSON-Objekt, Zeitstempel
    ISO 8601 mit Zeitzone), `configure_logging()` (Root-Handler ersetzt, `uvicorn.access`
    abgeschaltet — sonst zwei Formate nebeneinander), Middleware `observe_requests`,
    `/metrics` über `prometheus-client`.

    **Die Entscheidung, um die es geht — Label-Kardinalität:** als `path`-Label wird die
    **Route-Vorlage** benutzt (`/notes/{note_id}`), nicht der echte Pfad. Sonst bekäme
    **jede UUID eine eigene Zeitreihe** → bei 10.000 Notizen 10.000 Serien für einen
    Endpunkt. **Label-Werte müssen eine kleine, feste Menge sein.**
    `request.scope["route"]` existiert erst *nach* `await call_next(...)` (Routing passiert
    dort); bei 404 gibt es keine Route → `"unmatched"`.

    **Was ins Log darf:** Methode, Route-Vorlage, Status, Dauer. **Keine Notiz-Titel, keine
    Inhalte, keine Query-Strings** — Logs werden weitergereicht, archiviert und von mehr
    Leuten gelesen als die Datenbank.

    **Zähler leben im Prozess, also pro Pod.** Zwei Replicas + Round-Robin ⇒ `/metrics`
    liefert bei jedem Aufruf andere Zahlen. Kein Fehler: Prometheus fragt in Produktion
    jeden Pod einzeln ab und summiert selbst. Dasselbe Muster wie der Zustand in Etappe 5.

    **Nebenbei bestätigt:** `/readyz` 10×, `/healthz` 5× — genau das Verhältnis der
    Probe-Intervalle (5 s / 10 s) aus `deployment.yaml`.

    **TLS:** die App spricht bewusst HTTP. Standardmuster ist **TLS-Terminierung am
    Ingress** (außen HTTPS, dahinter Klartext) — Zertifikate liegen an einer Stelle, die
    App weiß nichts davon. Deshalb `--host 0.0.0.0` und nirgends ein Zertifikat.

11. **Prometheus im Cluster** (Etappe 11, Branch `feature/prometheus`) — `k8s/monitoring/`
    mit `rbac.yaml`, `prometheus.yml`, `deployment.yaml`, `service.yaml`, `kustomization.yaml`.
    Bewusst **ohne Helm/Operator**: `kube-prometheus-stack` würde die Scrape-Konfiguration
    und das Relabeling verstecken — genau das, was hier gelernt werden soll.

    **Service Discovery statt fester Zielliste:** `kubernetes_sd_configs: role: pod` fragt
    die API nach *allen* Pods. `relabel_configs` filtert **vor** dem Scrapen:
    `action: keep` auf `__meta_kubernetes_pod_annotation_prometheus_io_scrape` behält nur
    Pods mit `prometheus.io/scrape: "true"`; ein `replace` auf `__address__` setzt den Port
    aus `prometheus.io/port`. Labels mit `__` sind intern und verschwinden danach; Punkte
    und Schrägstriche in Annotationen werden zu Unterstrichen.
    Ergebnis: **2 Targets** (nur die notely-Pods), Postgres und Prometheus selbst nicht.

    **RBAC:** ServiceAccount (Identität) + ClusterRole (`pods: get,list,watch` — nur lesen)
    + ClusterRoleBinding. `serviceAccountName` im Pod-Template ist die Zeile, ohne die die
    ganze Berechtigung wirkungslos bleibt.

    **Annotationen brauchen Anführungszeichen** (`"true"`, `"8000"`): Annotation-Werte sind
    Strings, sonst lehnt die API das Manifest ab. Unterschied zu Labels: Labels dienen der
    **Auswahl** (Selektoren), Annotationen tragen **Information für Werkzeuge**.

    **`configMapGenerator` mit `files:`** statt `literals:` — die Konfiguration bleibt eine
    echte YAML-Datei. Der Dateiname wird zum ConfigMap-Schlüssel und damit zum Dateinamen
    im Container: Datei, Schlüssel und `--config.file` müssen denselben Namen tragen
    (`prometheus.yaml` statt `.yml` kostete hier einen Durchlauf).

    **Prometheus *zieht*, es bekommt nichts geschickt.** Bei `scrape_interval: 15s` sind
    Zahlen bis zu 15 s alt — eine Abfrage 2 s nach dem Request liefert korrekt *nichts*.
    Deshalb misst man Alarme in Minuten, nicht in Sekunden.

    **Damit ist das Pro-Pod-Problem aus Etappe 10 gelöst** — nicht im Code, sondern beim
    Auswerten: `sum(http_requests_total{path="/notes"})` über beide Replicas.
    p95: `histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))`
    — `le` = *less or equal*, die Histogramm-Klassen; die müssen bei `sum by` erhalten bleiben.

    **`emptyDir` statt PVC:** Messdaten sind beim Pod-Neustart weg. Für ein Lernprojekt
    zunächst gewollt; seit Etappe 33 (Punkt 30) durch ein PVC ersetzt.
    Zugriff über `kubectl port-forward svc/prometheus 9090:9090`, kein Ingress.

12. **Alarmregeln** (Etappe 12, Branch `feature/alerts`) — `k8s/monitoring/alerts.yml` mit
    drei Regeln, eingebunden über `rule_files: /etc/prometheus/alerts.yml` und als zweite
    Datei im `configMapGenerator`.

    **`for:` ist die wichtigste Zeile.** Ohne sie alarmiert jeder Ausschlag — ein Rollout,
    ein langsamer Request, ein Netzwerk-Zucken. Nach der dritten Fehlalarm-Nacht schaltet
    das Team die Alarme ab, und dann ist man schlechter dran als ohne. Zustände:
    **inactive → pending → firing**; `pending` heißt „Bedingung erfüllt, Uhr läuft".

    **Bewiesen:** `kubectl scale deployment/postgres --replicas=0` → `/readyz` antwortet 503
    → Fehlerrate **23,4 %** → `NotelyHighErrorRate` wechselte auf `pending`. Nach dem
    Hochskalieren erholte sich alles, **ohne dass der Alarm je `firing` erreichte** — genau
    das, wofür `for: 5m` da ist.

    **Zeitfenster verzögern beides.** `rate(...[5m])` schaut 5 Minuten zurück, also bleibt
    der Alarm noch minutenlang `pending`, nachdem die Störung behoben ist. Erkennen *und*
    Entwarnen hinken hinterher.

    **Die gefährliche Fehlerart dieser Etappe:** `alerts.yml` fehlte im `configMapGenerator`,
    `rule_files` zeigte also auf eine nicht existierende Datei. **Prometheus startete
    trotzdem** — nur eine Warnung im Log, kein Absturz, keine Regeln. Ein Überwachungssystem,
    das schweigt, sieht aus wie eines, bei dem alles in Ordnung ist. Deshalb nach dem
    Einrichten immer `/api/v1/rules` abfragen und die Regeln zählen.

    Details: `=~` ist Regex (`status=~"5.."` trifft 500/502/503). Bei null Anfragen ergibt
    die Fehlerraten-Division `0/0` = NaN, und NaN ist nie `> 0.05` — nachts bei Stille
    feuert also korrekt nichts.

13. **Alertmanager** (Etappe 13, Branch `feature/alertmanager`) — `alertmanager.yml` als
    eigene ConfigMap, `alertmanager-deployment.yaml` (Deployment + Service in einer Datei,
    getrennt durch `---`), und in `prometheus.yml` ein `alerting:`-Block mit
    `static_configs: targets: [alertmanager:9093]`. Hier reicht eine feste Adresse —
    es gibt genau einen Alertmanager unter einem festen Service-Namen.

    **Warum es Alertmanager überhaupt gibt** — Prometheus erkennt, stellt aber nicht zu:
    gruppieren (20 tote Pods = *eine* Nachricht), deduplizieren, stummschalten (Wartung),
    routen (`critical` ans Telefon, `warning` in den Chat).

    **Die vier Zeitangaben in `route:`:**
    | Feld | Bedeutung |
    |---|---|
    | `group_wait: 30s` | nach dem ersten Alarm warten, ob weitere derselben Gruppe kommen |
    | `group_interval: 5m` | Mindestabstand für Nachmeldungen in eine bestehende Gruppe |
    | `repeat_interval: 4h` | dauerhaft feuernder Alarm wird wiederholt, sonst vergisst man ihn |
    | `group_by` | wonach gruppiert wird (`alertname`, `namespace`) |

    **`receivers: - name: default` ohne Integration ist Absicht.** Alarme sind in der
    Alertmanager-Oberfläche sichtbar, gehen aber nirgends hin. `email_configs` /
    `slack_configs` bräuchten Zugangsdaten, die auf einem Firmenrechner nicht ins Git
    gehören — gehört zusammen mit echter Secret-Verwaltung erledigt.

    **`inhibit_rules`** ist das Alleinstellungsmerkmal: feuert ein `critical`, werden
    `warning`-Alarme im selben Namespace unterdrückt. **Ursache melden, Symptome
    unterdrücken.** Zugriff über `kubectl port-forward svc/alertmanager 9093:9093`.

    **Bewiesen (ganze Kette):** `kubectl scale deployment/postgres --replicas=0`, ~6 min
    gewartet → `NotelyHighErrorRate` von `pending` auf **`firing`** → im Alertmanager
    `1 Alarm: NotelyHighErrorRate | warning | active`. Prometheus meldet den Alertmanager
    unter `/api/v1/alertmanagers` als aktiv.

    **`NotelyTargetDown` blieb dabei `inactive`** — und das ist die Lektion: die App-Pods
    liefen weiter und lieferten Metriken, `up` blieb 1. Rot war nur die *Readiness*.
    Wieder die Trennung aus Etappe 5: der Pod war nicht kaputt, die Datenbank war weg.

    **`inhibit_rules` — in Etappe 17 geprüft, und dabei ein echter Fehler gefunden.**
    Siehe Punkt 17.

14. **README** (Etappe 14, PR #22) — 17 Bytes → 6,1 kB. Vier Teile: was drin ist, lokaler
    Start, Aufbau, **Entscheidungen mit Begründung**. Dazu „Bekannte Grenzen", das die
    fünf offenen Schwächen offen nennt (Klartext-Passwort, prod-Overlay, Job-Reihenfolge,
    `emptyDir`, Receiver ohne Integration).

    **Der Befund beim Schreiben:** Die Startanleitung war unvollständig, und zwar genau an
    den Stellen, die auf diesem Rechner längst erledigt waren — `ingress-nginx` wird separat
    installiert und ist nicht Teil der Manifeste, `KIND_EXPERIMENTAL_PROVIDER=podman` stand
    nur in `~/.zshrc`. **Eine Anleitung, die nur auf dem Rechner des Autors funktioniert,
    ist keine Anleitung.** Solche Lücken findet man nur beim Aufschreiben.

15. **SOPS mit age** (Etappe 15, Branch `feature/sops`) — `.sops.yaml` mit
    `creation_rules: path_regex: \.enc\.env$` und dem **öffentlichen** age-Schlüssel.
    Verschlüsselte Dateien im Repo: `k8s/overlays/local/{postgres-credentials,notely-db}.enc.env`
    und `k8s/overlays/prod/notely-db.enc.env`. Die entschlüsselten `*.env` sind gitignoriert.
    `secretGenerator` liest sie über `envs:` statt `literals:`.

    **SOPS verschlüsselt die Werte, nicht die Datei:** `POSTGRES_PASSWORD=ENC[AES256_GCM,…]`,
    Schlüsselnamen bleiben lesbar. Ein PR-Diff zeigt, *welches* Geheimnis sich geändert hat,
    ohne es zu verraten. Gewählt statt Sealed Secrets, weil der Schlüssel eine sichtbare
    Datei bleibt und nichts im Cluster liegen muss.

    **Der beste Beweis der Umstellung: identische Hashes.** Vorher und nachher
    `notely-db-c6c5bf6h4b` und `postgres-credentials-m487fkcmk5`. Der Hash wird über den
    Inhalt gebildet — gleicher Hash heißt, nur die *Aufbewahrung* hat sich geändert, nicht
    das *Ergebnis*. Die Secrets im Cluster waren danach unverändert alt (2d21h/3d19h).

    **Vier Fehler, die alle etwas lehren:**
    1. `sops -e datei > ziel.enc.env` → `no matching creation rules found`. SOPS prüft die
       Regel gegen die **Eingabe**, die `>`-Umleitung sieht es nie. Richtig ist `sops -e -i`
       auf eine Datei, die schon den Zielnamen trägt.
    2. Entschlüsseln scheiterte an `SOPS_AGE_KEY_FILE`. **Der Standardpfad ist
       plattformabhängig** — Linux `~/.config/sops/age/keys.txt`, macOS
       `~/Library/Application Support/sops/age/keys.txt`. Lösung: Variable explizit setzen.
    3. `export` in `~/.zshrc` eingetragen, aber die laufende Shell kannte sie nicht.
       **`~/.zshrc` wirkt erst auf die nächste Shell.**
    4. `>` **kürzt die Zieldatei, bevor** der Befehl läuft. Die gescheiterten `sops -d`-Läufe
       hinterließen 0-Byte-Klartextdateien. Danach immer `wc -l` prüfen — ein leeres Secret
       läuft lautlos durch und endet in `CreateContainerConfigError`.

    **Regeln braucht nur das Schreiben, nicht das Lesen:** beim Entschlüsseln stehen die
    nötigen Angaben im `sops:`-Metadatenblock der Datei selbst.

    **Passwörter in URLs:** das prod-Passwort entsteht mit
    `openssl rand -base64 24 | tr -d '/+='`. Die drei gelöschten Zeichen haben in einer URL
    Bedeutung und müssten sonst prozentkodiert werden — dasselbe Problem wie `%` → `%%` in
    `alembic/env.py`.

    **Damit ist offener Punkt 2 erledigt:** `k8s/overlays/prod` hat ein eigenes
    `notely-db`-Secret mit Zufallspasswort und rendert vollständig (`notely-db-hg79tbgg7m`).

    **Was bleibt:** das alte Klartext-Passwort steht **weiterhin in der Git-Historie**. Bei
    einem echten Geheimnis wäre die einzige richtige Antwort **rotieren** — Historie
    umschreiben hilft nur scheinbar, weil Klone und Forks die alten Commits behalten.

16. **Geplanter Scan** (Etappe 16, Branch `feature/scheduled-scan`) — `on:` in `ci.yml` um
    `schedule: - cron: "0 6 * * 1"` und `workflow_dispatch:` erweitert.

    **Warum überhaupt:** Der CVE aus Etappe 15 kam nicht aus dem Code. Er tauchte auf, weil
    Debian eine Lücke gemeldet hat — ohne dass jemand das Repo angefasst hatte. Ohne
    geplanten Lauf merkt man das erst beim nächsten Deploy, im schlechtesten Fall
    Freitagabend beim Hotfix. Montagmorgen ist gewählt, damit Funde am Wochenanfang liegen.

    **cron ist UTC**, nicht Ortszeit: `0 6 * * 1` ist in Deutschland 08:00 (Sommer) bzw.
    07:00 (Winter). Felder: Minute, Stunde, Tag, Monat, Wochentag (1 = Montag).

    **Die Zeile, die man dabei vergisst:** `push: ${{ github.event_name != 'pull_request' }}`
    musste zu `== 'push'` werden. Bei einem geplanten Lauf ist `event_name` = `schedule`,
    die alte Bedingung wäre **wahr** gewesen → jede Woche ein Image-Push, `latest` verschiebt
    sich ohne Code-Änderung. **Negative Bedingungen wachsen mit jedem neuen Auslöser mit,
    positive nicht.** Der geplante Lauf soll erkennen, nicht ausliefern.

    **`workflow_dispatch:`** gibt einen „Run workflow"-Knopf. Nötig, weil geplante Läufe nur
    auf dem Standard-Branch starten — die Änderung ist aus einem Feature-Branch heraus
    **nicht testbar**, erst nach dem Merge per Knopfdruck.

    **Nebenbefund beim Einbauen:** Die neue `push:`-Zeile landete zuerst auf Step-Ebene und
    überschrieb dabei `uses: docker/build-push-action@v6`. In YAML ist die Einrückung
    Bedeutung: Tiefe 6 = der Step, 8 = Schlüssel des Steps (`uses`, `with`), 10 = Parameter
    der Action. Kontrolle war `grep -c 'docker/build-push-action'` → muss **2** sein.

17. **Alarm-Labels reparieren** (Etappe 17, Branch `feature/alert-labels`) — beim Versuch,
    `inhibit_rules` zu prüfen, kamen zwei Befunde **durch Lesen**, nicht durch Testen.

    **Befund 1: `sum()` ohne `by` wirft *alle* Labels weg.** Gemessen:
    `sum(rate(http_requests_total[5m]))` → `{}`,
    `sum by (namespace) (rate(...))` → `{'namespace': 'default'}`.
    `NotelyHighErrorRate` hatte also **kein** `namespace`, `NotelyTargetDown` schon (aus dem
    Relabeling). Die `inhibit_rule` mit `equal: [namespace]` verlangt dasselbe Label auf
    beiden Seiten — bei „vorhanden vs. fehlend" gilt sie als nicht erfüllt.
    **Die Unterdrückung konnte nie greifen.** Fix: `sum by (namespace)` in beiden Zählern,
    `sum by (le, namespace)` beim Histogramm (`le` muss bleiben).

    **Befund 2: `== 0` und `absent()` erkennen verschiedene Ausfälle.**
    `up{...} == 0` braucht eine **existierende** Reihe mit Wert 0 — das passiert nur, wenn
    ein Target gefunden, aber nicht erreicht wird. Bei `kubectl scale --replicas=0`
    verschwindet die Reihe ganz, und die Regel feuert **nicht**. Dafür gibt es jetzt
    `NotelyNoTargets` mit `absent(up{job="kubernetes-pods"})` und einem **statischen**
    `namespace: default` — `absent()` kann keine Labels aus Daten mitbringen, es gibt keine.

    **Bewiesen, ohne 6 Minuten zu warten:** zwei künstliche Alarme per POST an
    `alertmanager:9093/api/v2/alerts` (ein `critical`, ein `warning`, gleicher Namespace) →
    der `warning` stand auf **`state=suppressed`** mit `inhibitedBy=[<fingerprint>]`.
    Dazu die zwei PromQL-Abfragen oben für den Labelerhalt. **Zwei kleine Messungen an der
    richtigen Stelle schlagen einen langen Ende-zu-Ende-Versuch.**

    **Und eine Selbstkorrektur, die dazugehört:** `/api/v1/rules` zeigt nur die *statisch
    konfigurierten* Labels einer Regel, nicht die aus dem Abfrageergebnis. Es war deshalb
    kein Beweis für den Fix — solche Fehlschlüsse fallen nur auf, wenn man fragt, *was* eine
    Ausgabe eigentlich zeigt.

18. **GitOps mit ArgoCD** (Etappe 18–19, Branch `feature/argocd`, dann `feature/argocd-hooks`)
    — ArgoCD im eigenen Namespace `argocd` (offizielles `install.yaml`, ~50 Objekte),
    dazu `k8s/argocd/application.yaml` (Objekt `kind: Application`) und ein eigenes Overlay
    `k8s/overlays/argocd/`. Zugriff auf die Oberfläche über
    `kubectl port-forward svc/argocd-server -n argocd 8081:443`, dann **https**://localhost:8081
    (selbstsigniertes Zertifikat, Warnung durchklicken). Startpasswort:
    `kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath='{.data.password}' | base64 -d`.

    **Warum ein eigenes Overlay:** ArgoCD führt `kustomize build` aus und kann **kein SOPS**.
    Das `local`-Overlay verlangt `notely-db.env`, das absichtlich nicht im Repo liegt → ArgoCD
    scheiterte an „file not found". Das ArgoCD-Overlay hat deshalb **keinen `secretGenerator`**;
    die Secrets tragen ihre schlichten Namen und wurden **einmal von Hand** angelegt
    (`kubectl create secret generic … --from-env-file=…`). Das nennt man **„secret zero"**:
    irgendein erstes Geheimnis muss immer von außen kommen. Mit KSOPS wäre es nur verschoben —
    dann ist der age-Schlüssel das erste Geheimnis. **Verschieben ja, abschaffen nein.**

    **Der Job war dauerhaft `OutOfSync`** — er hat `ttlSecondsAfterFinished: 300` und löscht
    sich selbst. Er steht in Git, aber nicht im Cluster. **Ein Objekt, das sich selbst löscht,
    passt nicht in das Vergleichsmodell von ArgoCD.** Lösung: zwei Annotationen am Job,
    ```yaml
    argocd.argoproj.io/hook: PreSync
    argocd.argoproj.io/hook-delete-policy: BeforeHookCreation
    ```
    Damit lösen sich **drei** Dinge auf einmal: Hooks werden nicht mit Git verglichen (kein
    `OutOfSync`); `PreSync` läuft **vor** dem restlichen Sync und wartet → **offener Punkt 1
    (Reihenfolge) ist gelöst**; `BeforeHookCreation` löscht den alten Job vorher → kein
    `field is immutable` mehr. Für den Hand-Pfad (`kubectl apply -k`) sind die Annotationen
    wirkungslos und damit harmlos.

    **Die Fehler dieser Etappe, alle lehrreich:**
    1. `targetRevision: feature/argocd`, dann Branch auf GitHub **gelöscht ohne zu mergen** →
       `unable to resolve 'feature/argocd' to a commit SHA`, Status `Unknown`. Gerettet über
       den „Restore branch"-Knopf; der Commit lag lokal ohnehin noch. **Fehlerklasse: Löschen
       vor dem Zusammenführen.** `git branch -d` schützt lokal davor, GitHub nicht.
    2. **ArgoCD prüft nur alle 3 Minuten** und zeigt bis dahin den alten Zustand samt alter
       Fehlermeldung. Vor dem Glauben an eine Meldung deren `lastTransitionTime` lesen.
       Erzwingen: `kubectl patch application notely -n argocd --type merge -p
       '{"metadata":{"annotations":{"argocd.argoproj.io/refresh":"hard"}}}'`.
    3. `port-forward` läuft nur, solange der Befehl läuft — bei „connection refused" auf 8081
       ist fast immer der Tunnel abgerissen, nicht ArgoCD kaputt.
    4. **`/healthz` über den Ingress ist leer** (`200`, `text/html`, 0 Bytes): ingress-nginx
       reserviert diesen Pfad für seinen **eigenen** Gesundheitscheck und antwortet selbst.
       `/readyz`, `/notes`, `/metrics` gehen durch. Unkritisch, weil die `livenessProbe`
       **direkt am Pod** fragt. **Merksatz: der Ingress ist nicht die einzige Tür.**

    **Die Oberfläche ist nur eine Ansicht.** Der `SYNCHRONIZE`-Knopf schreibt das Feld
    `operation` in das Application-Objekt. Dasselbe von Hand:
    `kubectl patch application notely -n argocd --type merge -p
    '{"operation":{"initiatedBy":{"username":"admin"},"sync":{"revision":"HEAD"}}}'`.
    Deshalb ist ArgoCD vollständig skriptbar und braucht keinen Browser.

    **Bewiesen:** nach dem Sync `Synced` / `Healthy`, neue Pods, und die App meldete
    `{"status":"ok","version":"gitops"}` — die laufende App kam also aus
    `k8s/overlays/argocd` und nicht mehr aus dem, was von Hand angewendet worden war.

    **Bootstrap-Problem:** `application.yaml` wird per `kubectl apply -f` von Hand angewendet
    und verwaltet sich **nicht selbst**. Ändert sich `targetRevision` in Git, muss die Datei
    erneut angewendet werden. Dieselbe Form wie „secret zero".

19. **Automatischer Sync + selfHeal** (Etappe 20, Branch `feature/argocd-autosync`) — drei
    Zeilen in `k8s/argocd/application.yaml`:
    ```yaml
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
    ```
    | Feld | Wirkung |
    |---|---|
    | `automated` | synchronisiert von selbst, sobald Git sich ändert — kein Knopf mehr |
    | `prune: true` | löscht Objekte, die aus Git **verschwunden** sind |
    | `selfHeal: true` | dreht Änderungen im **Cluster** zurück, die nicht aus Git kommen |

    **Bewiesen:** `kubectl scale deployment/notely --replicas=5` → ArgoCD stellte innerhalb
    von Sekunden auf `replicas=2` zurück (Git sagt `count: 2`). So schnell, dass ein
    nachträglich gestartetes `kubectl get pods -w` nichts mehr zu sehen bekam — der Beweis
    lag in den Zahlen: 5 Pods vorher, 2 danach, ohne dass jemand zurückskaliert hat.

    **ArgoCD korrigiert die Spezifikation, nicht den Zustand.** Es schreibt `spec.replicas`
    im Deployment zurück; die überzähligen Pods räumt Kubernetes dann selbst ab.

    **Die YAML-Falle dabei:** `syncPolicy` landete zuerst auf Tiefe 4 und damit *innerhalb*
    von `destination`, `automated` daneben statt darunter. Kubernetes ignoriert das
    stillschweigend — `spec.syncPolicy` blieb leer, ohne Fehlermeldung. Kontrolle, die es
    vor dem Anwenden zeigt:
    `python3 -c "import yaml; print(yaml.safe_load(open('k8s/argocd/application.yaml'))['spec'].get('syncPolicy'))"`

    **Was die Automatik kostet:** `prune` macht einen Tippfehler in Git zu einer Löschung in
    Produktion. `selfHeal` nimmt dir Notfall-Eingriffe per `kubectl` weg — der Weg führt ab
    jetzt über Git, oder man schaltet die Automatik bewusst kurz ab.

20. **CI schreibt den sha-Tag nach Git** (Etappe 21, Branch `feature/ci-writes-tag`) — zwei
    Steps am Ende des Jobs `image`, beide mit `if: github.event_name == 'push'`: ein `sed`
    setzt `newTag` im prod-Overlay auf `sha-$GITHUB_SHA`, dann committet der Bot
    (`github-actions[bot]`) und pusht.

    **Die wichtigste Zeile ist `[skip ci]` in der Commit-Nachricht.** Ohne sie entsteht eine
    **Endlosschleife**: Push → CI läuft → CI pusht → das ist ein Push → CI läuft → …
    GitHub erkennt `[skip ci]`, `[ci skip]` und `[no ci]` im Betreff und startet dann keinen
    Workflow. **Jede CI, die nach Git schreibt, braucht so eine Bremse.**

    **`contents: write` nur im Job `image`.** Global bleibt `contents: read`; der Job-Block
    überschreibt es nur dort, wo wirklich gepusht wird. `quality` bekommt keine
    Schreibrechte. Ohne `write` scheitert `git push` mit `403`.

    **`git push origin HEAD:main`** — `actions/checkout` hinterlässt einen *detached HEAD*
    (ein Commit, kein Branch). Ein nacktes `git push` wüsste nicht, wohin.

    **`if git diff --cached --quiet; then … else … fi` statt `&&`-Kette.** `--quiet` liefert
    Exit-Code 1, *wenn* es Unterschiede gibt. GitHub führt `run:`-Blöcke mit `bash -e` aus —
    in einer `&&`-Kette würde der Step dadurch fehlschlagen, obwohl alles in Ordnung ist.
    Innerhalb von `if` löst ein Exit-Code ≠ 0 kein `-e` aus.
    **Fehlerklasse: `set -e` und erwartete Fehlschläge.**

    **Warum `sed` und nicht `yq`:** `yq` liegt auf den GitHub-Runnern, aber nicht auf diesem
    Rechner — der Ausdruck wäre ungetestet in die CI gegangen. `sed -E "s|^( *newTag: ).*|…|"`
    ließ sich lokal prüfen, und `newTag` kommt im prod-Overlay genau **einmal** vor.
    **Lieber ein Werkzeug, das man vorher testen kann.**

    **Nebenbefund beim Testen:** `GITHUB_SHA=x sed "…${GITHUB_SHA}…"` funktioniert **nicht**.
    Die Zuweisung vor dem Befehl setzt die Variable für `sed`, aber `${…}` in doppelten
    Anführungszeichen ersetzt die **Shell vorher** — und die kennt sie da noch nicht. In der
    CI ist `GITHUB_SHA` eine echte Umgebungsvariable, dort greift es.

    **Bewiesen:** Lauf zu `3e40fc8` auf `main` erzeugte
    `a23b24d chore(deploy): pin prod overlay to sha-3e40fc81… [skip ci]`,
    Autor `github-actions[bot]`, **1 file changed, 1 insertion, 1 deletion**. Der sha im Tag
    ist genau der Commit, der den Lauf ausgelöst hat. Und es gibt **keinen zweiten**
    Bot-Commit — `[skip ci]` hat gehalten. `newTag: latest` → `newTag: sha-3e40fc81…`:
    ab jetzt ist jederzeit nachweisbar, welcher Commit in prod läuft, und ein Rollback ist
    ein `git revert`.

    **Zwei Anläufe, und beide Male dieselbe Ursache:** Der `contents: write`-Fix und die
    40 Zeilen CLAUDE.md waren nach dem `git add -A` entstanden und fehlten deshalb in PR #31.
    Der Lauf scheiterte an `403`. **Regel: `git add -A` ist der letzte Schritt vor
    `git commit`, nicht der erste.** Alles danach ist für den Commit unsichtbar und steht in
    `git status --short` als `MM` (Buchstabe links *und* rechts). Nachgereicht in PR #32.

    **Ehrliche Grenze:** ArgoCD überwacht `k8s/overlays/argocd`, **nicht** `prod`. Dieser
    Commit löst also noch kein Deployment aus — gebaut ist der Mechanismus, nicht die
    geschlossene Schleife. Dafür müsste ArgoCD auf `prod` zeigen, und das Image aus GHCR
    müsste für den kind-Cluster ziehbar sein.

21. **Die Schleife geschlossen** (Etappe 22, Branch `feature/close-the-loop`) — das
    ArgoCD-Overlay zieht jetzt aus GHCR statt aus dem lokal geladenen Image:
    ```yaml
    images:
      - name: notely
        newName: ghcr.io/burhandevopsnew/notely-platform
        newTag: sha-<40 Zeichen>
    ```
    Damit fällt `kind load` für den ArgoCD-Pfad **weg** — der Cluster zieht aus derselben
    Quelle wie jede andere Umgebung. Die CI pinnt beide Overlays (`prod` und `argocd`) in
    einer `for`-Schleife und committet mit `git add k8s/overlays/` (**Ordner**, nicht
    Einzeldatei — sonst fehlt die argocd-Änderung im Commit; dieselbe Mechanik wie `MM`).

    **Vorher geprüft, statt gehofft:** Ist das GHCR-Paket öffentlich? Anonymes Token holen
    und das Manifest abfragen → `HTTP 200`, also kein `imagePullSecret` nötig.
    ```
    curl -s "https://ghcr.io/token?scope=repository:<owner>/<repo>:pull&service=ghcr.io"
    curl -H "Authorization: Bearer <token>" https://ghcr.io/v2/<owner>/<repo>/manifests/<tag>
    ```
    Wäre es privat, bräuchte der Cluster ein Pull-Secret. Öffentlich heißt: **jeder kann das
    Image herunterladen** — bei einer Demo-App in Ordnung, bei Firmencode nicht.

    **Einen Tag nur setzen, wenn man weiß, dass er existiert.** `sha-3e40fc81…` war vorher
    per Manifest-Abfrage bestätigt; ein geratener Tag endet in `ImagePullBackOff`.

    **`imagePullPolicy: IfNotPresent` passt jetzt genau:** ein sha-Tag ist unveränderlich,
    also darf der Cluster ihn cachen. Bei einem wandernden `latest` wäre `Always` nötig.

    **Der Fehler, der die Schleife beim ersten Versuch blockierte — Architektur-Mismatch.**
    Der PreSync-Hook blieb in `ImagePullBackOff` stehen, ArgoCD hing bei
    `waiting for completion of hook batch/Job/notely-migrate`. Meldung des kubelet:
    `no match for platform in manifest: not found` — **kein** Rechteproblem.
    Gemessen am Manifest: GHCR enthielt nur `linux/amd64`, Mac und kind-Knoten sind `arm64`.
    Grund: bisher wurde lokal mit Podman auf arm64 gebaut und per `kind load` geschoben;
    der GitHub-Runner ist amd64, und `build-push-action` baut standardmäßig nur für die
    eigene Architektur. **Ein Image ist immer für *eine* Architektur; ein Tag kann auf eine
    Manifest-Liste mit mehreren zeigen.**

    Fix: `docker/setup-qemu-action@v3` vor dem Buildx-Setup und
    `platforms: linux/amd64,linux/arm64` **nur** im Push-Build. Der Scan-Build behält
    `load: true` ohne `platforms` — ein Multi-Plattform-Image lässt sich nicht in den
    lokalen Daemon laden. Trivy scannt damit die amd64-Variante; vertretbar, weil beide
    dieselben Paketversionen enthalten, aber eine bewusste Vereinfachung.
    Kosten: arm64 läuft unter Emulation, der Job `image` dauert deutlich länger.

    **Beruhigender Nebenbefund:** Während der Hook hing, liefen die alten Pods weiter und
    ArgoCD meldete `Healthy`. **Ein blockierter PreSync-Hook verhindert die neue Version,
    reißt aber die laufende nicht mit.**

    **Zwei weitere Fehler auf dem Weg, beide lehrreich:**
    1. **GHCR-Drosselung.** Der Multi-Arch-Push scheiterte mit
       `denied: permission_denied … 403 Forbidden` — im JSON-Rumpf stand aber
       `You have exceeded a secondary rate limit`. **Meldung mit irreführender Überschrift:**
       die Ursache steht erst im Rumpf. Kein Code-Problem; Abhilfe: warten und
       „Re-run failed jobs". Als Folge wurde `type=raw,value=latest` aus der metadata-action
       entfernt — ein Tag weniger heißt weniger Schreibvorgänge, und für Deployments ist ein
       wandernder Tag ohnehin schädlich.
    2. **Veralteter Editor-Puffer.** Die `for`-Schleife im Pin-Step war in PR #33 geprüft
       drin und nach PR #34 wieder weg — beim Einfügen von QEMU/`platforms` hatte VS Code
       eine ältere Fassung im Speicher und überschrieb sie beim Speichern. Erkennungsmerkmal:
       eine Änderung, die man geprüft hatte, ist ohne Zutun verschwunden. Gegenmittel: nach
       `git pull` oder Branch-Wechsel die Datei im Editor schließen und neu öffnen.

    **Bewiesen (PR #35, `19072c2`) — die Schleife läuft:**
    ```
    main:            19072c2
    argocd-Overlay:  newTag: sha-19072c2…      von der CI geschrieben
    Migrations-Job:  Complete 1/1 in 9s        PreSync-Hook
    Pods:            ghcr.io/…:sha-19072c2…    beide Running
    ArgoCD:          Synced / Healthy — successfully synced (all tasks run)
    ```
    **Kein Deploy-Befehl getippt** — nur ein PR gemergt. Derselbe sha steht in Git, in der
    Registry, im Overlay und in den laufenden Pods; ein Rollback ist ein `git revert`.
    Das Migrations-Log zeigte **kein** `Running upgrade`: die DB war schon auf `head`, der
    Hook lief trotzdem. **Ein PreSync-Hook, der nichts tut, ist der Normalfall.**

22. **Waisen aufgeräumt** (Etappe 23) — 8 ungenutzte Objekte gelöscht: zwei alte
    `notely-config-*` und **vier** `prometheus-config-*` (je eine pro Änderung an
    `prometheus.yml`/`alerts.yml`), dazu die vom local-Overlay erzeugten
    `notely-db-c6c5bf6h4b` und `postgres-credentials-m487fkcmk5`.

    **Der Mechanismus, der den Rollout schenkt, hinterlässt Spuren:** jeder neue
    Inhalts-Hash erzeugt ein neues Objekt, das alte bleibt liegen. `prune` räumt es nicht —
    es löscht nur, was ArgoCD selbst verwaltet hat und was dann aus Git verschwunden ist.

    **Vorgehen vor dem Löschen:** die **Live-Objekte** nach ihren Referenzen fragen
    (`kubectl get deploy <name> -o json`), nicht die Manifeste lesen. Danach explizit die
    unbenutzten Namen ausschreiben statt ein `grep`-Muster zu benutzen — **bei zerstörenden
    Befehlen zählt Explizitheit mehr als Kürze.** Und die Frage „wo ist die Kopie?" war
    beantwortet: alle acht entstehen aus Git neu (`configMapGenerator` bzw. `sops -d` +
    `apply -k`).

    Danach 5 Objekte übrig, `/readyz` ready, ArgoCD `Synced / Healthy`.

23. **Absichtlich kaputte Migration** (Etappe 24, Übung — nichts davon committet) — Ziel war
    „grüne CI, gescheiterter Deploy", um den PreSync-Hook beim Blockieren zu beobachten.
    Migration von Hand (`alembic revision` **ohne** `--autogenerate`, weil es keine
    Modelländerung zu erkennen gab):
    `op.add_column('notes', sa.Column('owner', sa.String(100), nullable=False))`.

    **Der Versuch ging anders aus als geplant, und das war lehrreicher.** Erwartet: 12 grün,
    weil das Modell die Spalte nicht kennt. Tatsächlich: **5 failed, 7 passed.**

    Die Migration selbst lief durch (Test-DB: 0 Zeilen). Aber danach scheiterte jedes
    `INSERT`: das SQL der App lautet
    `INSERT INTO notes (id, title, body, created_at, archived)` — `owner` fehlt, die Spalte
    ist `NOT NULL` ohne Vorgabewert → `NotNullViolation … Failing row contains (…, null)`.

    **Erweiterte Lektion zu Etappe 7:** Eine `NOT NULL`-Spalte ohne `server_default` bricht
    **zwei** Dinge — den `ALTER TABLE` auf bestehenden Zeilen *und* jedes künftige `INSERT`
    von Code, der die Spalte nicht kennt. Ich hatte nur an den ersten Schaden gedacht.

    **Welche Tests rot waren, sagt wieder alles:** genau die fünf, die **schreiben**
    (`POST /notes`). Grün blieben `/healthz`, `/readyz`, leere Liste, 404, 422 — keiner davon
    schreibt. **Die Testsuite hat die Migration gefangen**, die CI wäre rot geworden. Der
    geplante Versuch ist mit dieser Migration also nicht baubar — und das ist die gute
    Nachricht.

    **Den blockierten Deploy hatten wir ohnehin schon erlebt:** beim Multi-Arch-Problem stand
    der PreSync-Hook stundenlang in `ImagePullBackOff`, ArgoCD hing bei
    `waiting for completion of hook`, und die alte Version bediente weiter Anfragen.

    **`alembic downgrade -1`** hat zum Rücknehmen die selbst geschriebene `downgrade()`-Funktion
    benutzt (`op.drop_column`). **Deshalb schreibt man sie**, auch wenn man sie fast nie
    braucht — ohne sie kommt man nicht zurück, ohne die Datenbank von Hand anzufassen.
    `-1` ist relativ („einen Schritt zurück"), alternativ eine Revisions-ID absolut.

24. **KSOPS: Secrets fließen über Git** (Etappe 25, Branches `feature/ksops` +
    `fix/argocd-database-url`) — der argocd-repo-server entschlüsselt SOPS-Secrets jetzt
    selbst. Bauteile: `.sops.yaml`-Regel für `\.enc\.yaml$` mit
    `encrypted_regex: ^(data|stringData)$` (nur Werte verschlüsseln, Struktur lesbar —
    sonst erkennt ksops kein Secret); zwei verschlüsselte Secret-Manifeste +
    `secret-generator.yaml` (KRM-exec-Plugin, `config.kubernetes.io/function`) in
    `k8s/overlays/argocd/`; `generators:` in der Overlay-Kustomization;
    `kustomize.buildOptions: --enable-alpha-plugins --enable-exec` in `argocd-cm`;
    age-Schlüssel als Secret `sops-age` im Namespace `argocd`; repo-server-Patch in
    `k8s/argocd/repo-server-ksops-patch.yaml` (per `kubectl patch --patch-file`
    angewendet — strategic merge, mischt Listen über `name:`).

    **Der Patch enthält ein Muster zum Merken — zwei initContainer, ein `emptyDir`:**
    Das ksops-Image ist quasi distroless (keine Shell, kein `cp` — vorher geprüft per
    `podman export | tar -t`). Die offizielle Anleitung mit `/bin/sh` läuft dagegen —
    **Fehlerklasse: Anleitung passt nicht mehr zur Version.** Lösung: initContainer 1
    (busybox) kopiert sich selbst ins Volume, initContainer 2 (ksops-Image) benutzt
    dieses busybox als `cp`. initContainer laufen nacheinander, das Volume überlebt.
    Die ksops-Binary landet per `subPath`-Mount als einzelne Datei in
    `/usr/local/bin/` — ohne das Verzeichnis (ArgoCDs eigenes kustomize!) zu überdecken.

    **Der beste Fehler der Etappe:** `exec /custom-tools/busybox: no such file or
    directory` — obwohl die Datei da war (cp: exit 0). `busybox:1.37` ist **dynamisch
    gelinkt**; der Kernel suchte den in der Binary eingetragenen Loader
    `/lib/ld-linux-aarch64.so.1`, den es im ksops-Image nicht gibt. Das ENOENT meint den
    Interpreter, die Meldung nennt die Binary. Fix: `busybox:1.37-musl` (statisch).
    Nachweis: `ls /lib` + `grep -c ld-linux /bin/busybox` in beiden Varianten (1 vs. 0).
    **Fehlerklasse: dynamisch gelinkte Binary in fremde Umgebung verschoben. Merksatz:
    „no such file or directory" bei nachweislich existierender Datei = fehlender
    ELF-Interpreter.**

    **Der Incident: Platzhalter statt Wert.** In `notely-db.enc.yaml` stand ein von der
    Editor-Autovervollständigung erfundener plausibler Wert
    (`postgresql://notely:password@notely-db-postgresql:5432/notely` — Schema ohne
    `+psycopg`, erfundener Host, falsches Passwort). Die Kontrolle `grep -c "ENC\["`
    prüfte nur, **dass** verschlüsselt wurde, nicht **was**.
    **Fehlerklasse: Verschlüsselung geprüft, Inhalt nicht.** Die Kontrolle, die ab jetzt
    vor jedem Secret-Commit läuft:
    ```
    diff <(sops -d DATEI.enc.yaml | grep KEY | awk '{print $2}') <(grep '^KEY=' QUELLE.env | cut -d= -f2-)
    ```
    Die Wirkungskette war lehrreich: Der Adoptions-Sync war **grün**, weil der
    PreSync-Hook **vor** dem Anwenden lief (altes, korrektes Hand-Secret) und die
    Sync-Phase das kaputte Secret erst danach schrieb. Die App blieb **Healthy**, weil
    `envFrom` nur beim Container-Start gelesen wird — ein **latenter Ausfall**, der erst
    beim nächsten Pod-Start gezündet hätte. Der Folge-Sync scheiterte dann im Hook
    (`backoffLimit`), und `ttlSecondsAfterFinished` hatte Job samt Pods gelöscht —
    **TTL gilt auch für gescheiterte Jobs und frisst Beweise**; Events waren nach 1 h
    ebenfalls weg. Diagnose lief deshalb über den Ist-Wert:
    `kubectl get secret … | base64 -d` gegen die lokale Quelldatei.

    **Das Henne-Ei, das man kennen muss: der PreSync-Hook liest das Secret, das erst
    die Sync-Phase reparieren würde.** Ein kaputtes Secret im Cluster blockiert damit
    jeden künftigen Sync. Lösung: Git zuerst fixen (`sops set DATEI INDEX WERT` —
    ändert einen Wert ohne Editor, Wert muss JSON sein), **nach dem Merge** das
    Cluster-Secret von Hand patchen. Reihenfolge zwingend: `selfHeal` heilt in Richtung
    Git — vor dem Merge hätte es den Hand-Patch auf den kaputten Git-Stand zurückgedreht.

    **Bewiesen:** lokal und im repo-server rendert dasselbe
    (`kustomize build --enable-alpha-plugins --enable-exec`); ArgoCD hat die
    Hand-Secrets **adoptiert** (`argocd.argoproj.io/tracking-id` gesetzt, vorher
    `<none>`); nach dem Fix-Merge Sync `Succeeded`, neue Pods starteten erstmals mit dem
    ksops-gerenderten Secret und wurden ready (`/readyz` = `SELECT 1` gegen die DB).

    **Ehrliche Grenzen:** (1) „Secret zero" ist umgezogen, nicht weg — der private
    age-Schlüssel liegt als Secret im Cluster, von Hand angelegt. (2) `--enable-exec`
    ist eine Vertrauensentscheidung: Repo-Schreibrecht = Code-Ausführung im repo-server.
    (3) `kubectl apply -k k8s/overlays/argocd` geht nicht mehr — das in kubectl
    eingebaute kustomize kann keine exec-Plugins; der Hand-Pfad bleibt `overlays/local`.
    (4) Der repo-server-Patch ist Bootstrap wie `application.yaml`: dokumentiert, aber
    nicht selbstverwaltend.

    **Kleinigkeiten, die Zeit kosteten:** `kubectl exec deploy/…` wählt während eines
    Rollouts irgendeinen Pod — auch den alten (die Zeile `Defaulted container … out of:`
    verrät am initContainer-Satz, welcher es war). `sops -d` in nicht-interaktiver Shell
    scheitert, weil `~/.zshrc` (`SOPS_AGE_KEY_FILE`) nur interaktive Shells erreicht —
    sops probiert dann `~/.ssh/id_rsa` als age-Identität und meldet „identity did not
    match". Und zweimal zu früh geprüft: **erst `origin/main` fragen, dann den Cluster**
    — `Synced` heißt „Cluster = letzter Git-Stand, den ArgoCD kennt", nicht „mein
    Feature ist deployed".

25. **Ausfall-Übung: falscher age-Schlüssel im repo-server** (Etappe 26, Übung — keine
    Code-Änderung) — das `sops-age`-Secret wurde durch einen frisch erzeugten, falschen
    Schlüssel ersetzt (Upsert-Muster: `kubectl create … --dry-run=client -o yaml |
    kubectl apply -f -`), Hard-Refresh, beobachten, reparieren.

    **Drei Vorhersagen, alle bestätigt:**
    1. Die laufende App blieb unberührt — `/readyz` ready, Pods `Running`. **Ein
       Rendering-Fehler blockiert Neues, tötet nichts Laufendes.**
    2. Status wurde **`Unknown` + `ComparisonError`, nicht `OutOfSync`**. `OutOfSync`
       heißt „ich sehe eine Differenz", `Unknown` heißt „ich kann nicht mehr
       vergleichen". `Healthy` blieb daneben stehen — Health bewertet die *laufenden*
       Objekte, nicht das Rendern.
    3. Der Secret-Mount aktualisierte sich **ohne Pod-Neustart** (kubelet zieht
       Verzeichnis-Mounts in ~1 min nach). Kontrast: der ksops-Binary-Mount ist
       `subPath` — **subPath-Mounts aktualisieren sich nie.**

    **Die Fehlermeldung war ein Lehrstück in Schichten**, von außen nach innen:
    ArgoCD (`Failed to load target state`) → repo-server (zeigt den echten Befehl samt
    buildOptions) → kustomize (`failed to evaluate function`) → ksops (`error
    decrypting file`) → sops (`0 successful groups required, got 0` = keine
    Schlüsselgruppe konnte den Datenschlüssel entschlüsseln).

    **Die Race, die eine Runde kostete:** Refresh lief, *bevor* das kubelet den
    reparierten Mount nachgezogen hatte — der repo-server renderte mit dem alten
    Schlüssel, das Ergebnis blieb im Cache stehen. Reihenfolge bei Secret-Reparaturen:
    Secret ersetzen → ~90 s warten → Refresh. Kontrolle über drei `shasum`-Vergleiche:
    Cluster-Secret vs. lokale Datei vs. `kubectl exec … cat` im Pod — so sieht man,
    *welches* Glied der Kette hinterherhinkt.

    **Der unbequeme Befund: dieser Ausfall ist lautlos.** Kein Alarm feuert — die
    Prometheus-Regeln schauen auf die App, niemand schaut auf ArgoCD. Ein kaputtes
    Deployment-System fällt erst auf, wenn ein Merge nicht ankommt. ArgoCD exportiert
    eigene Metriken (`argocd_app_info` mit `sync_status`-Label) — ArgoCD in die
    Scrape-Config aufnehmen und eine Regel darauf bauen wäre die passende Folge-Etappe.

26. **ArgoCD-Monitoring: Sync-Ausfälle sind nicht mehr lautlos** (Etappe 27, Branch
    `feature/argocd-monitoring`) — Konsequenz aus der Übung in Punkt 25. Zwei Dateien in
    `k8s/monitoring/`: in `prometheus.yml` ein zweiter Scrape-Job (`static_configs` auf
    `argocd-metrics.argocd.svc:8082`), in `alerts.yml` die Gruppe `argocd` mit
    `ArgoCDMetricsDown` (`up{job="argocd"} == 0`, `for: 5m`) und `ArgoCDAppNotSynced`
    (`argocd_app_info{sync_status!="Synced"} == 1`, `for: 15m`).

    **Entscheidungen, die man begründen können muss:**
    - `static_configs` statt Pod-Discovery: genau ein Controller unter festem
      Service-Namen — und Annotationen an ArgoCDs StatefulSet wären ein weiterer
      Hand-Eingriff außerhalb von Git. **Discovery für dynamische Flotten, statisch
      für bekannte Einzelziele.**
    - `<service>.<namespace>.svc` ist Pflicht: `alertmanager:9093` funktioniert nur,
      weil Alertmanager im selben Namespace läuft. Über Namespace-Grenzen braucht der
      DNS-Name den Namespace.
    - Beim statischen Target bleibt die Zielzeile immer bestehen → `up == 0` genügt,
      `absent()` ist unnötig — **die Etappe-17-Unterscheidung, umgekehrt angewandt.**
    - `for: 15m` bei `ArgoCDAppNotSynced`: jeder normale Deploy geht kurz durch
      `OutOfSync`; ohne Wartezeit feuerte der Alarm bei jedem Merge.

    **Erste Monitoring-Änderung komplett über GitOps:** neuer ConfigMap-Hash →
    Pod-Template geändert → Prometheus rollte nach dem Merge von selbst, noch vor dem
    Pin-Commit. Kein einziger Hand-Befehl.

    **Bewiesen durch Wiederholung der Ausfall-Übung:** falscher age-Schlüssel →
    Application `Unknown` → `ArgoCDAppNotSynced` auf **`pending`** nach gut einer
    Minute. Reparatur → Metrik `Synced` → nächster Evaluations-Tick → Alarmliste leer.
    Der Alarm feuerte nie — `inactive → pending → inactive`, genau wofür `for:` da ist.

    **Gemessene Alarm-Latenz, jetzt mit Begründung:** `scrape_interval: 15s` plus
    `evaluation_interval` (nie gesetzt, **Standard 1 min**) ≈ bis zu 75 s zwischen
    „Welt ist kaputt" und „Regel ist pending" — und dasselbe noch einmal beim
    Entwarnen. Deshalb misst man Alarm-Latenz in Minuten.

    **Zwei Kleinigkeiten:** `kubectl exec … wget` starb einmal mit exit 139
    (= 128 + Signal 11, SIGSEGV) und riss den JSON-Strom ab — der Python-Traceback
    darunter war nur die Folge. **Fehlerklasse: Folgefehler diagnostiziert statt
    Ursache — die erste Fehlerzeile zählt, nicht die lauteste.** Und dreimal an einem
    Tag zu früh geprüft: Kontrollen gegen den Cluster sind erst nach Merge + CI +
    Sync aussagekräftig — **der Cluster kann Git nicht voraus sein.**

27. **Image-Diät: −30 MB ohne Funktionsverlust** (Etappe 28, Branch `feature/image-diet`)
    — eine `RUN`-Zeile im Builder geändert: `pip install --no-compile` (keine
    `.pyc`-Dateien — reiner Startzeit-Cache, den `PYTHONDONTWRITEBYTECODE=1` zur
    Laufzeit ohnehin nicht nachwachsen ließe) plus `pip uninstall -y pip setuptools`
    in **derselben** Zeile (Schichten-Lektion aus Etappe 9; hier zusätzlich: `COPY
    --from=builder` kopiert den Endzustand des venv). Seit Python 3.12 legt `venv`
    nur noch pip an — das `uninstall setuptools` läuft als Warnung durch.

    **Gemessen, mit Werkzeug und Einheit:**
    | | vorher | nachher |
    |---|---|---|
    | Image (`podman images`, arm64, unkomprimiert) | 254 MB | **224 MB** |
    | `/opt/venv` (`du -sh` im Container) | 95 MB | **64 MB** |
    | auf dem kind-Node (`crictl images`, komprimiert) | 75,3 MB | **64,7 MB** |

    **`pip uninstall` ist nebenbei eine Härtung:** in diesem Image kann nie wieder
    etwas nachinstalliert werden. Funktionsbeweis vor dem Merge lokal per
    `podman run -p 8001:8000` + `curl /healthz`; nach dem Merge lieferte die Schleife
    unverändert automatisch aus (Pin `sha-ec9774b…`, `Synced / Healthy`, `/readyz` ready).

    **Zwei Befunde am Node (`crictl images`):** (1) Dieselbe `SIZE`-Spalte trägt je
    nach Ankunftsweg andere Bedeutung — per `kind load` importierte Images stehen
    unkomprimiert drin, aus der Registry gezogene komprimiert. (2) Sieben alte
    GHCR-Images liegen dort — unveränderliche Tags sammeln sich, kubelet räumt erst
    bei Plattendruck (dieselbe Mechanik wie die ConfigMap-Waisen aus Etappe 23).

    **Und einmal Automatik erklärt statt gesucht:** Nach dem Merge lief „noch eine CI"
    — das ist der Push-Lauf auf `main`, den der Merge selbst auslöst; sein Pin-Commit
    geht als Bot direkt auf `main`. **Nur menschliche Arbeit läuft über PRs.**

28. **Alertmanager-Zustellung: Webhook statt stummer Receiver** (Etappe 29, Branch
    `feature/alertmanager-webhook`) — die letzte „Bekannte Grenze" geschlossen, ohne
    Zugangsdaten: `k8s/monitoring/webhook-logger.yaml` (Deployment + Service; ein
    Inline-Python-`http.server`, der jeden POST als eine JSON-Logzeile druckt) und in
    `alertmanager.yml` am Receiver `default`:
    ```yaml
    webhook_configs:
      - url: http://webhook-logger:9000/alerts
        send_resolved: true
    ```
    Kurzer DNS-Name reicht — gleicher Namespace (Kontrast zur
    `argocd-metrics.argocd.svc`-Lektion). Im Logger-Manifest zwei bewusste Details:
    `python -u` + `flush=True` (sonst puffert stdout und `kubectl logs` schweigt) und
    `log_message` überschrieben (sonst Apache-Format-Access-Logs neben dem JSON —
    dasselbe Zwei-Formate-Problem wie `uvicorn.access` in Etappe 10).

    **Bewiesen mit der Stoppuhr, beide Richtungen:** Kunstalarm per POST an
    `/api/v2/alerts` → nach `group_wait` (30 s) eine Zeile `"status": "firing"` im
    Logger. Und ohne weiteres Zutun **exakt 5:00 min später** `"status": "resolved"` —
    per API eingeworfene Alarme ohne `endsAt` verfallen nach `resolve_timeout`
    (Default 5 min), und `send_resolved: true` stellt die Entwarnung zu. Ein
    Empfänger, der nur „kaputt" hört und nie „wieder gut", produziert Alarm-Leichen.

    **Die Payload ist der Vertrag, den auch Slack/PagerDuty bekämen:**
    `groupLabels` = wörtlich unser `group_by`; `alerts[]` mit `fingerprint` (Hash
    **nur über die Labels** — ein erneut gefeuerter Alarm mit neuem `startsAt` behält
    denselben Fingerprint, deshalb funktioniert Deduplizierung); `truncatedAlerts`
    für gekappte Riesen-Gruppen; `externalURL` zeigt den Pod-Namen, weil Alertmanager
    seine öffentliche Adresse nicht kennt.

    **Zwei Fehler auf dem Weg, beide aus der bekannten Familie:**
    1. Die neue `resources:`-Zeile landete direkt unter `kind: Kustomization` —
       **YAML faltet eingerückte Folgezeilen in den Skalar darüber**: `kind` war
       lautlos der String `Kustomization - webhook-logger.yaml`, die Datei parste
       fehlerfrei. Gefangen von der Zähl-Kontrolle (4 statt 5 Ressourcen).
    2. `webhook-logger.yaml` wurde **zweimal leer committet** — `wc -l` sagte `0`,
       `git show --stat` sagte `| 0`, beides überlesen. Die Ur-Fehlerklasse des
       Projekts: die Zahl steht in der Ausgabe, der Vergleich mit der angesagten
       Erwartung (~50) fand nicht statt. Repariert mit `git commit --amend --no-edit`
       (erlaubt, weil noch nicht gepusht).

    **Grenze:** Zustellung heißt hier „steht in `kubectl logs deploy/webhook-logger`"
    — ein Kanal, den Menschen abonnieren (Slack, E-Mail), bräuchte Zugangsdaten und
    bleibt auf dem Firmenrechner bewusst außen vor. Und alles geht an **einen**
    Receiver; Routing nach `severity` (critical → anderer Kanal) wäre die
    Fortsetzung.

29. **Alarm-Routing nach severity** (Etappe 30, Branch `feature/alert-routing`) — in
    `alertmanager.yml` bekommt die Wurzel-`route:` ein Kind:
    ```yaml
    routes:
      - matchers: [severity="critical"]
        receiver: critical
        group_wait: 10s
    ```
    plus zweiter Receiver `critical` (gleicher webhook-logger, Pfad `/critical`).

    **`route:` ist ein Baum:** ein Alarm läuft von der Wurzel abwärts, das erste
    passende Kind gewinnt, sonst bleibt die Wurzel zuständig. Kinder **erben** alles,
    was sie nicht überschreiben (`group_by`, Intervalle) — im Kind steht nur das
    Delta. Unterschieden werden die Zustellungen am `"receiver"`-Feld der Payload;
    der Logger brauchte keine Änderung.

    **Kontrolle vor dem Commit — mit dem echten Parser:** `amtool check-config` aus
    exakt dem Image, das im Cluster läuft:
    `podman run --rm -v "$PWD/k8s/monitoring:/cfg:ro" --entrypoint amtool
    docker.io/prom/alertmanager:v0.27.0 check-config /cfg/alertmanager.yml`
    → `SUCCESS`, 2 receivers. (Mount nach `/cfg`, nicht `/tmp`; Pfad unter `$HOME`
    wegen der Podman-VM.)

    **Bewiesen mit Vorher/Nachher-Messung im Logger (kubelet-Zeitstempel):**
    - Vorher (alte Config, ein Topf): beide Proben `receiver: default`, 14 ms
      auseinander nach ~30 s.
    - Nachher: critical-Probe nach **~10 s** an `receiver: critical`, warning-Probe
      nach **~30 s** an `receiver: default` — **20 s Abstand = exakt die Differenz
      der `group_wait`-Werte**, und der als zweites gefeuerte critical überholte den
      warning. Wichtig fürs Design der Messung: die zwei Proben brauchten
      **verschiedene Namespaces**, sonst hätte die `inhibit_rule` den warning
      verschluckt (Etappe 17).

    **Zwei Fehlerklassen nebenbei:** (1) Die Proben liefen zuerst **vor** dem Merge —
    vierte Wiederholung von „der Cluster kann Git nicht voraus sein", diesmal als
    nützliche Baseline umgedeutet. (2) **Toter Follower:** `kubectl logs -f` hält
    eine Dauerverbindung und stirbt lautlos (Laptop-Schlaf, Netzwechsel) — „keine
    neuen Zeilen" heißt nicht „keine neuen Ereignisse". Gegenprobe:
    `kubectl logs --tail=5 --timestamps` ohne `-f`.

29. **Zweiter Service: notely-stats** (Etappe 31, Branches `feature/stats-service`,
    `feature/stats-deploy`, `fix/stats-metrics`) — aus „einem Deployment" wird „ein
    Cluster mit Diensten". Vier Teiletappen, je ein PR.

    **A — Der Dienst** (`stats/`: eigene `app/main.py`, `requirements.txt`, `Dockerfile`):
    `GET /stats` fragt notely über **dessen HTTP-API** ab (`httpx`, `NOTELY_URL`-Default
    `http://notely` — Service-Port 80, kein Port im URL). **Services teilen APIs, keine
    Tabellen**: ein Direktzugriff auf Postgres hätte stats ans *Schema* gekettet (jede
    Migration ein Risiko für einen fremden Dienst) statt an den *Vertrag*. `/readyz`
    prüft notely (fremde Abhängigkeit → Readiness, nie Liveness — Etappe 5 von der
    anderen Seite), `/stats` antwortet bei totem Upstream **502** (Bad Gateway),
    `/readyz` **503**. Nur 3 Abhängigkeiten — kein SQLAlchemy, kein Alembic.
    Lokal bewiesen in zwei Stufen: ohne notely → korrektes 502; mit
    `-e NOTELY_URL=http://host.containers.internal:8080` gegen den echten Cluster →
    echte Zahlen quer durch Podman-VM, Mac und kind-Ingress.

    **B — CI-Matrix** (`strategy.matrix.include` mit `service`/`context`/`suffix`):
    ein Job-Skelett, zwei parallele Läufe, zwei GHCR-Images
    (`notely-platform`, `notely-platform-stats`). Die vier Stolpersteine:
    (1) `upload-artifact@v4` **scheitert hart** bei doppeltem Namen → `sbom-<service>`.
    (2) gha-Cache braucht `scope=<service>`, sonst überschreiben sich die Läufe.
    (3) **Der Pin-Step musste aus dem Matrix-Job raus** — zwei parallele Läufe hätten
    gleichzeitig nach main gepusht (Race). Jetzt eigener Job `pin` mit `needs: image`
    (wartet auf alle Matrix-Läufe); nur er hat `contents: write`, der image-Job gibt
    es ab. Das Pin-`sed` trifft **alle** `newTag`-Zeilen — gewollt, alle Images tragen
    denselben Commit-sha. (4) Im PR erscheint `Pin overlays` als **Skipped** — die
    `if: github.event_name == 'push'`-Bedingung als sichtbare Kachel.
    **GHCR legt neue Pakete privat an** — einmalig auf Public stellen (Profil →
    Packages → Danger Zone), Beweis per anonymem Token + `tags/list` → 200.

    **C — Manifeste** (`k8s/stats/` + Ingress-Pfad + 3 Overlays): notely-Vorbild mit
    bewussten Abweichungen — `replicas: 1` (zustandsloser Aggregator), **kein
    `envFrom`** (keine DB, kein Secret), halbierte Ressourcen. Ingress: `/stats` →
    notely-stats, Rest → notely (nginx nimmt den längsten Prefix). Endbeweis:
    `curl localhost:8080/stats` → Ingress → stats-Pod → notely-Service → notely-Pod
    → Postgres, ausgeliefert nur durch die Schleife.

    **D — Der eingebaute Fehler und sein Geschenk:** Das stats-Deployment bekam
    Scrape-Annotations, aber die App hatte **keinen `/metrics`-Endpunkt** (kein
    prometheus-client). Discovery fand den Pod, Target `down`, und nach 2 Minuten
    feuerte `NotelyTargetDown` — **der erste echte, organisch entstandene Alarm des
    Projekts**, über den critical-Zweig (10 s) im webhook-logger. **Fehlerklasse:
    Deklaration und Implementierung auseinander** — die Annotation ist ein
    Versprechen, das der Code halten muss. Erkennungsmerkmal echter Alarme:
    **`generatorURL` ist gefüllt** (Link auf die PromQL-Abfrage); Kunstalarme per
    API haben es leer. Fix: `prometheus-client` + `app.mount("/metrics",
    make_asgi_app())` — nach dem Merge Target `up`, und die Entwarnung kam als
    `resolved` über den critical-Receiver. Erkennung → Routing → Zustellung →
    Entwarnung, einmal komplett an einem echten Fall.

    **Nebenbefunde:** (1) `Connection reset by … port 22` beim Push — die Ursache
    steht in der **ersten** Zeile (TCP/SSH), nicht in Gits „Zugriffsberechtigungen"-
    Ratschlag darunter; der Push war trotzdem durch (nur die Antwort ging verloren),
    `Everything up-to-date` beim Retry bewies es. Ausweich für blockierten Port 22:
    `ssh.github.com:443` (`~/.ssh/config`). (2) `{"detail":"Not Found"}` auf
    `/stats` vor dem Deploy: **FastAPIs** 404-Format verriet, dass notely
    geantwortet hat — der Ingress kannte den Pfad noch nicht. Wer antwortet, sagt
    dir, wo du stehst. (3) `command not found` nach Terminalwechsel = fehlende
    venv-Aktivierung, nicht fehlendes Programm.

30. **stats-Tests in der CI** (Etappe 32, Branch `feature/stats-tests`) — der offene
    Punkt aus Etappe 31 geschlossen: `stats/tests/test_stats.py`, 5 Tests, Suite
    12 → **17**. An `ci.yml` änderte sich **nichts** — pytest sammelt den neuen
    Ordner selbst ein; nur `requirements-dev.txt` bekam `-r stats/requirements.txt`,
    sonst könnte die CI `stats/app/main.py` nicht importieren.

    **Das Muster: Test-Doppel statt echtem Upstream.** `monkeypatch.setattr(httpx,
    "get", …)` tauscht die Funktion im httpx-Modul aus — dasselbe Modulobjekt, das
    die App importiert hat, deshalb wirkt es dort; pytest stellt es nach jedem Test
    zurück. `FakeResponse` implementiert nur `raise_for_status()` und `json()` —
    **Test-Doppel dürfen minimal sein**, sie spielen nur die benutzte Oberfläche.
    Getestet: Zählen (total/archived), toter Upstream → 502 bzw. 503, und
    `test_metrics_endpoint_exists` als **Regressionstest für den Etappe-31-Incident**
    — wäre `/metrics` je wieder weg, wird der PR rot statt der Cluster laut.

    **Die Import-Mechanik, die man kennen muss:** pytest läuft von der Testdatei
    aufwärts, solange `__init__.py` existiert, und legt das erste Verzeichnis ohne
    eine solche in den Import-Pfad. Deshalb zwei leere Marker: `stats/__init__.py`
    + `stats/tests/__init__.py` → Repo-Wurzel im Pfad, Modulname
    `stats.tests.test_stats`. **Ohne `stats/__init__.py` hieße das Modul
    `tests.test_stats` und kollidierte mit notelys `tests`-Paket.**

    Nebenbei: auch ein reiner Test-Commit deployt bei uns (nicht in `paths-ignore`)
    — neuer sha, formaler Rollout, kein Schaden. Und ein Tippfehler in der
    Commit-Nachricht wurde vor dem Push per `git commit --amend -m` repariert —
    **Nachrichten werden später durchsucht; amend ist gratis, solange nichts
    gepusht ist.**

30. **Prometheus auf PVC: Messdaten überleben den Pod** (Etappe 33, Branch
    `feature/prometheus-pvc`) — die `emptyDir`-Grenze aus Etappe 11 geschlossen.
    Drei Dateien in `k8s/monitoring/`: neues `pvc.yaml` (2Gi, RWO), im Deployment
    `emptyDir` → `persistentVolumeClaim` plus zwei Zeilen, die man begründen können
    muss, und die Kustomization-Zeile.

    **Die zwei Zeilen:**
    - `strategy: Recreate` — ein RWO-Volume verträgt keine zwei Pods, und Prometheus
      sperrt seine TSDB mit einer **`lock`-Datei** (nach dem Mount sichtbar in
      `/prometheus`: `wal`, `chunks_head`, `lock`). RollingUpdate liefe in einen
      Crash des neuen Pods. Gleiche Entscheidung wie bei Postgres (Etappe 5).
    - `fsGroup: 65534` — das frische Volume gehört root; erst die fsGroup macht es
      für den nobody-User (65534) beschreibbar, als der Prometheus läuft.

    **Bewiesen mit einer Zahl:** Baseline `count_over_time(up{job="argocd"}[15m])`
    = 49 Samples → Pod getötet → neuer Pod nach ~2 s → dieselbe Abfrage: **60
    Samples, Fenster lückenlos, umschließt den Todeszeitpunkt.** Läge die TSDB im
    Pod, stünden dort ~8. Dieselbe Beweisführung wie Etappe 5, Stufe 3 — Zustand
    liegt im PVC.

    **Korrigierte Vorhersage:** die erwartete Recreate-Messlücke kam nicht — ein
    manueller Pod-Tod mit sofortigem Reschedule auf demselben Node dauert ~2 s,
    weniger als das 15-s-Scrape-Raster. Die Lücke ist real bei *Rollouts* (Image
    ziehen, Config wechseln), nicht bei jedem Neustart. **Auch eine ausgebliebene
    Lücke ist ein Messergebnis.**

    Nebenbei die Erinnerung an die WAL-Idee: `wal` = write-ahead log, dasselbe
    Muster wie bei Postgres — erst journalieren, dann strukturiert wegschreiben.

## Wo wir gerade stehen
`main` = `32e0bea` (Merge PR #57) + Bot-Pin dahinter. Arbeitsverzeichnis
sauber, keine offenen Branches. **Zwei Services**: notely (2 Replicas) und notely-stats
(1 Replica, `/stats` am Ingress). Prometheus: 4 Targets up, 6 Regeln. 17 Tests.
Alarme werden nach severity geroutet und an den webhook-logger zugestellt (critical
nach 10 s, Rest nach 30 s). Der offene Punkt aus Etappe 31 (stats ungetestet) ist durch Etappe 32 geschlossen. ArgoCD: `Synced / Healthy`. Secrets laufen über KSOPS;
`notely-db` und `postgres-credentials` tragen die ArgoCD-`tracking-id`.

**Die GitOps-Schleife ist geschlossen:** Merge → CI baut, scannt und pusht multi-arch →
CI pinnt den sha in prod- und argocd-Overlay → ArgoCD synct → PreSync-Hook migriert →
App rollt aus. Kein Deploy-Befehl mehr von Hand — auch Secrets nicht mehr (Etappe 25).

**`paths-ignore` ist bewiesen:** Ein Doku-Merge (nur `.md`/`docs/`) bewegt `main`,
startet aber keinen Workflow — `newTag` und laufendes Image bleiben unverändert.

Nächster Schritt: frei — Kandidaten: neue Ausfall-Übung, Prometheus auf PVC,
oder ein zweiter Service neben notely.
Beim Start den echten Zustand gegen diese Notiz prüfen:
`git fetch && git log --oneline -2 origin/main`, `git branch -vv`,
`kubectl get application -n argocd`, laufendes Image über
`kubectl get pods -l app=notely -o jsonpath='{.items[0].spec.containers[0].image}'`.

## 🔴 Offene Punkte
1. **Nur noch im Hand-Pfad: keine Reihenfolge, Job-`spec` unveränderlich.** Über ArgoCD ist
   das gelöst (`PreSync`-Hook, siehe Punkt 18). Wer weiterhin `kubectl apply -k` benutzt,
   braucht davor `kubectl delete job notely-migrate --ignore-not-found` und hat keine
   Garantie, dass die Migration vor den App-Pods fertig ist.
2. **Erledigt durch KSOPS (Etappe 25, Punkt 24).** Nur der Hand-Pfad (`overlays/local`)
   braucht weiterhin `sops -d` vor dem `apply`. Neue Restpunkte: der private age-Schlüssel
   liegt als `sops-age`-Secret im Cluster (secret zero, von Hand angelegt), und
   `--enable-exec` koppelt Repo-Schreibrecht an Code-Ausführung im repo-server.
3. **Erledigt durch die Image-Diät (Etappe 28, Punkt 27):** −30 MB, venv 95 → 64 MB,
   kein pip mehr im Laufzeit-Image.

## Danach geplant
- Echte Secret-Verwaltung: SOPS / Sealed Secrets / External Secrets Operator.
  (Aktuell steht das Postgres-Passwort im Klartext in der Git-Historie — bewusst, nur
  für die lokale Wegwerf-DB; bei einem echten Geheimnis wäre Rotieren die Antwort.)

## Sprache im Repo
- **Kommentare und Docstrings: Deutsch.** Gilt auch für generierte Dateien, sobald wir sie
  pflegen (`alembic/env.py`, `alembic/script.py.mako` — die Vorlage übersetzen, sonst kommt
  jede neue Migration wieder englisch heraus).
- **Fremde Referenztexte bleiben englisch**, z. B. die ~100 Kommentarzeilen in `alembic.ini`.
  Übersetzt weichen sie von der offiziellen Doku ab, die man beim Debuggen daneben legt.
- **Fehler- und Logmeldungen: Englisch** (`raise RuntimeError("DATABASE_URL must be set …")`).
  Sie landen in Logs und werden gegoogelt; englische Meldungen findet man, deutsche nicht.
  Unterscheidung: *Kommentare für den Leser des Codes, Meldungen für den Betreiber im
  Störungsfall.*
- **Commit-Nachrichten, Branch-Namen: Englisch**, Imperativ („persist", nicht „persisted").
- Vorlagen-Füllmaterial nicht übersetzen, sondern **löschen**. Ein Kommentar, der nur
  wiederholt, was der Code sagt, ist Wartungslast — er veraltet und lügt dann.

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
- **Vorgemerkt ist nicht committet.** In Etappe 9 lief `git add -A`, aber `git commit`
  nicht — gepusht wurde der alte Stand, PR #16 lieferte **drei Zeilen Doku statt der
  ganzen Etappe**, und die CI war grün, weil nichts drin war. Erkennungsmerkmal in
  `git status --short`: Buchstabe **links**, Leerzeichen rechts (`M `). Gegenmittel:
  nach *jedem* Commit `git show --stat --oneline HEAD` und die Dateizahl gegen die
  **vorher genannte Erwartung** halten; vor jedem Merge den Reiter „Files changed".
  **Ein grüner PR beweist nicht, dass Arbeit ausgeliefert wurde — nur, dass das,
  was drin war, funktioniert.**
- **Sehr lange Befehle scheitern still.** Der Commit oben war ein 900-Zeichen-Einzeiler
  mit drei `-m`-Blöcken; er überlebte das Einfügen nicht. Kurze Betreffzeile im Terminal,
  ausführlicher Text ins PR-Beschreibungsfeld — dort liest ihn der Reviewer ohnehin.
- **`unable to find version X` heißt „heißt anders", nicht „zu alt".** Die Tags von
  `aquasecurity/trivy-action` tragen ein `v` (`v0.36.0`). Echte Namen nachschlagen statt
  an der Zahl drehen — geht ohne Browser und ohne Login:
  `git ls-remote --tags URL | sed 's|.*refs/tags/||; s|\^{}||' | sort -u | sort -V | tail -5`
  (`sort -V` = Versionssortierung, sonst landet 0.9 hinter 0.36).
- **`tail -1` ist die Ziffer eins.** In vielen Schriftarten von `l` nicht zu unterscheiden.
  Sicherer: `tail -n 1` — `-n` nimmt eine Zahl, da kann kein Buchstabe hin.
- **`git add -A`, nicht `git commit -am`.** `-a` merkt nur *verfolgte* Dateien vor; eine
  neue Datei mit `??` fehlt still im Commit — lokal läuft alles, die CI stirbt an
  `ModuleNotFoundError`. Danach zählen: `git diff --cached --stat | tail -1`.
- **Branch löschen nur mit `-d`, nie `-D`.** `-d` weigert sich bei nicht gemergter Arbeit —
  diese Weigerung ist Information, keine Störung.
- Merksätze aus dem Projekt: „Editor schreibt, Terminal führt aus, Git entscheidet.“ ·
  „Grüner Build ≠ brauchbares Ergebnis.“ · „Ein sauberer `diff` beweist, dass die
  Beschreibung stimmt, nicht dass das Laufende ihr entspricht.“ · „Wo du dich auf Disziplin
  verlassen müsstest, such nach einer Konstruktion, die den Fehler unmöglich macht.“
