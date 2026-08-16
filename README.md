# notely-platform

Eine kleine Notiz-API in FastAPI — als Vehikel für den kompletten Betriebszyklus:
Code → Container → CI/CD → Kubernetes → Observability.

Die Anwendung selbst ist bewusst schlicht. Interessant ist, was darum herum steht und
**warum** es so steht.

## Was drin ist

| Bereich | Umsetzung |
|---|---|
| API | FastAPI, CRUD auf `/notes`, `PATCH` für Teiländerungen, `/healthz`, `/readyz`, `/metrics` |
| Datenbank | PostgreSQL 17, SQLAlchemy 2.0, Alembic-Migrationen |
| Container | Multi-Stage-Dockerfile, `python:3.12-slim`, non-root (uid 10001), read-only Dateisystem |
| CI | GitHub Actions: ruff + pytest gegen echtes Postgres, Trivy-Scan, SBOM, Push nach GHCR |
| Kubernetes | Kustomize (base + Overlays), 2 Replicas, PVC für Postgres, Migration als Job |
| Observability | JSON-Logs, Prometheus mit eigener Scrape-Config, Alarmregeln, Alertmanager |
| Tests | 12 pytest-Tests, prüfen HTTP-Verhalten statt Interna |

## Lokal starten

Voraussetzungen: Podman, kind, kubectl, Python 3.12.

```bash
# kind mit Podman statt Docker betreiben
export KIND_EXPERIMENTAL_PROVIDER=podman

# Cluster anlegen (Name "notely", Port 80 -> 8080 auf dem Host)
kind create cluster --config cluster/kind-cluster.yaml

# Ingress-Controller — nicht Teil dieses Repos, wird separat installiert
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=180s
```

Podman präfixt lokale Images mit `localhost/`, Kubernetes löst einen Namen ohne Registry
als `docker.io/library/` auf. Das `tag` baut die Brücke:

```bash
podman build -t notely:dev .
podman tag localhost/notely:dev docker.io/library/notely:dev
podman save docker.io/library/notely:dev -o /tmp/notely.tar
kind load image-archive /tmp/notely.tar --name notely
```

```bash
# Der Job-spec ist unveränderlich, ein zweites apply scheitert sonst
kubectl delete job notely-migrate --ignore-not-found
kubectl apply -k k8s/overlays/local
```

Danach ist die API unter `http://localhost:8080` erreichbar (ingress-nginx, kein
port-forward nötig).

```bash
curl -s localhost:8080/readyz
curl -s -X POST localhost:8080/notes \
  -H 'Content-Type: application/json' \
  -d '{"title":"Erste Notiz","body":"Hallo"}'
```

Prometheus und Alertmanager sind bewusst **nicht** veröffentlicht:

```bash
kubectl port-forward svc/prometheus 9090:9090
kubectl port-forward svc/alertmanager 9093:9093
```

## Tests

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
```

Die Tests brauchen ein erreichbares Postgres mit der Datenbank `notely_test`. Das Schema
bauen sie über Alembic auf — eine kaputte Migration fällt damit in der CI auf und nicht
erst beim Deploy.

## Aufbau

```
app/            FastAPI-Anwendung, SQLAlchemy-Modelle, Observability
alembic/        Migrationen (env.py liest DATABASE_URL aus der Umgebung)
k8s/base/       Deployment, Service, Ingress, Migrations-Job
k8s/postgres/   PVC, Deployment, Service
k8s/monitoring/ Prometheus, Alertmanager, Scrape-Config, Alarmregeln
k8s/overlays/   local und prod
```

## Entscheidungen und ihre Begründung

**Zustand gehört nicht in den Prozess.** Die erste Fassung hielt Notizen in einem Dict im
Speicher. Bei zwei Replicas verteilt der Service per Round-Robin, und dieselbe Abfrage
lieferte abwechselnd die Notiz und eine leere Liste. Zustand im Prozess und horizontale
Skalierung schließen sich aus.

**Liveness und Readiness prüfen Verschiedenes.** `/healthz` fasst die Datenbank nicht an,
`/readyz` macht ein `SELECT 1`. Fällt Postgres aus, werden die Pods aus dem Service
genommen, aber **nicht neu gestartet**. Würde `/healthz` die Datenbank prüfen, würde
Kubernetes gesunde Anwendungspods töten, weil eine fremde Abhängigkeit weg ist — ein
Kaskadenausfall. Regel: fremde Abhängigkeiten nur in der Readiness.

**Migrationen laufen als Job, nicht als initContainer.** Ein initContainer läuft in jedem
Pod, bei zwei Replicas also zweimal gleichzeitig auf derselben Datenbank. Ein Job läuft
genau einmal.

**Die Anwendung legt kein Schema mehr an.** `create_all` erzeugt fehlende Tabellen und tut
sonst nichts — keine Spaltenänderung, keine Datenmigration. Alembic übernimmt das, und die
Tests fahren die Migrationen mit.

**Der Trivy-Scan hat zwei Läufe.** Einer berichtet alles und macht nie rot. Der zweite
blockiert bei HIGH/CRITICAL, aber nur mit `--ignore-unfixed`: ein Build soll nur an dem
scheitern, was man auch ändern kann. Sonst ist er nach dem dritten Mal aus fremder Schuld
rot, und rote Builds werden ignoriert. Das Tor steht **vor** dem Push — ein verwundbares
Image erreicht die Registry gar nicht erst.

**Metrik-Labels nutzen die Route-Vorlage.** Als `path` steht `/notes/{note_id}` im Label,
nicht der echte Pfad. Sonst bekäme jede UUID eine eigene Zeitreihe.

**Jede Alarmregel hat ein `for:`.** Ohne das alarmiert jeder Ausschlag — ein Rollout, ein
langsamer Request. Nach der dritten Fehlalarm-Nacht schaltet ein Team die Alarme ab, und
dann ist man schlechter dran als ohne.

**TLS wird am Ingress terminiert.** Die Anwendung spricht bewusst HTTP. Zertifikate liegen
an einer Stelle, die Anwendung weiß nichts davon.

## Bekannte Grenzen

- Das Postgres-Passwort steht im Klartext im Repository. Bewusst so, nur für die lokale
  Wegwerf-Datenbank. Richtig wäre SOPS, Sealed Secrets oder ein External Secrets Operator —
  offen.
- `k8s/overlays/prod` hat kein `notely-db`-Secret und ist deshalb nicht lauffähig. Gehört
  zusammen mit der Secret-Verwaltung erledigt.
- `kubectl apply` ordnet Migrations-Job und Deployment nicht. Unkritisch, weil `/readyz` nur
  `SELECT 1` prüft. Echte Reihenfolge gäbe es mit Helm-Hooks oder ArgoCD-Sync-Waves.
- Prometheus schreibt in ein `emptyDir` — Messdaten überleben keinen Pod-Neustart.
- Der Alertmanager-Receiver hat keine Integration. Alarme sind in der Oberfläche sichtbar,
  werden aber nirgends zugestellt.
