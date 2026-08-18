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
| CI | GitHub Actions: ruff + pytest gegen echtes Postgres, Trivy-Tor, SBOM, Multi-Arch-Push (amd64 + arm64) nach GHCR, sha-Tag zurück nach Git |
| Kubernetes | Kustomize (base + Overlays), 2 Replicas, PVC für Postgres, Migration als PreSync-Hook |
| GitOps | ArgoCD im Cluster: ein Merge nach `main` **ist** das Deployment |
| Observability | JSON-Logs, Prometheus mit eigener Scrape-Config, Alarmregeln, Alertmanager |
| Tests | 12 pytest-Tests, prüfen HTTP-Verhalten statt Interna |

## Wie deployt wird: GitOps

Es gibt keinen Deploy-Befehl. Ein Merge nach `main` löst die ganze Kette aus:

```
Merge nach main
   │
   ├─ CI: ruff + pytest gegen echtes Postgres
   ├─ CI: Image für amd64 + arm64 bauen, Trivy-Tor, SBOM
   ├─ CI: Push nach GHCR mit unveränderlichem Tag  sha-<commit>
   └─ CI: schreibt diesen Tag zurück in die Overlays (Commit mit [skip ci])
              │
              ▼
       ArgoCD (im Cluster) liest main, sieht die Änderung
              │
              ├─ PreSync-Hook: alembic upgrade head  (läuft genau einmal, wartet)
              └─ danach rollt das Deployment
```

Der `[skip ci]`-Vermerk ist die Bremse gegen eine Endlosschleife: der Commit der CI
löst keinen neuen Lauf aus.

Zustand abfragen:

```bash
kubectl get application -n argocd                       # Synced / Healthy?
kubectl get application notely -n argocd -o jsonpath='{.status.sync.revision}'
git rev-parse origin/main                               # beide Werte vergleichen
kubectl get pods -l app=notely \
  -o jsonpath='{range .items[*]}{.spec.containers[0].image}{"\n"}{end}'
```

`Synced` gilt gegen die Revision, die ArgoCD **zuletzt verglichen** hat — nicht
zwangsläufig gegen den neuesten Commit. Deshalb immer beide Werte gegeneinander halten.
ArgoCD prüft alle drei Minuten; erzwingen geht mit:

```bash
kubectl patch application notely -n argocd --type merge \
  -p '{"metadata":{"annotations":{"argocd.argoproj.io/refresh":"hard"}}}'
```

Die Oberfläche erreicht man über `kubectl port-forward svc/argocd-server -n argocd 8081:443`
und dann **https**://localhost:8081. Sie ist nur eine Ansicht: der `SYNCHRONIZE`-Knopf
schreibt das Feld `operation` in das Application-Objekt, dasselbe geht per `kubectl patch`.

**Zwei Pfade, absichtlich getrennt:**

| | Overlay | Image | Geheimnisse |
|---|---|---|---|
| **GitOps** (ArgoCD) | `k8s/overlays/argocd` | aus GHCR, `sha-<commit>` | einmalig von Hand angelegt |
| **Hand-Pfad** (lokal) | `k8s/overlays/local` | lokal gebaut, `kind load` | `sops -d` vor jedem `apply` |

## Lokal starten (Hand-Pfad, ohne ArgoCD)

Voraussetzungen: Podman, kind, kubectl, Python 3.12, `sops` und `age`.

Die Geheimnisse liegen mit [SOPS](https://github.com/getsops/sops) verschlüsselt im
Repository (`*.enc.env`). Zum Entschlüsseln braucht man den privaten age-Schlüssel — ohne
ihn ist der Rest dieser Anleitung nicht ausführbar. Ein eigener Schlüssel:

```bash
mkdir -p ~/.config/sops/age
age-keygen -o ~/.config/sops/age/keys.txt        # gibt den öffentlichen Schlüssel aus
export SOPS_AGE_KEY_FILE=$HOME/.config/sops/age/keys.txt
```

`SOPS_AGE_KEY_FILE` ist nötig, weil SOPS den Standardpfad plattformabhängig sucht — auf
macOS unter `~/Library/Application Support`, nicht unter `~/.config`. Die Zeile gehört in
die Shell-Konfiguration.

Den öffentlichen Schlüssel trägt man in `.sops.yaml` ein und verschlüsselt die Dateien neu
(`sops -e -i <datei>.enc.env`). Der private Schlüssel gehört nie ins Repository.

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

Kustomize kann kein SOPS, die Geheimnisse müssen also vorher entschlüsselt werden. Die
entstehenden Klartextdateien sind gitignoriert:

```bash
sops -d k8s/overlays/local/postgres-credentials.enc.env > k8s/overlays/local/postgres-credentials.env
sops -d k8s/overlays/local/notely-db.enc.env > k8s/overlays/local/notely-db.env
wc -l k8s/overlays/local/*.env      # muss 3 und 1 ergeben, nicht 0
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
k8s/argocd/     ArgoCD-Application (wird einmalig von Hand angewendet)
k8s/overlays/   local (Hand-Pfad), prod, argocd (von ArgoCD überwacht)
docs/           technologien.md — jede eingesetzte Technologie einfach erklärt
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

**Der Migrations-Job ist ein PreSync-Hook, kein normales Objekt.** Er hat
`ttlSecondsAfterFinished` und löscht sich selbst — damit stand er in ArgoCD dauerhaft auf
`OutOfSync`: in Git vorhanden, im Cluster nicht. Zwei Annotationen lösen drei Probleme
zugleich: Hooks werden nicht mit Git verglichen, `PreSync` läuft **vor** dem Rest und
wartet (das ist die Reihenfolge-Garantie, die `kubectl apply` nie geben konnte), und
`hook-delete-policy: BeforeHookCreation` umgeht die unveränderliche Job-`spec`.

**ArgoCD hat ein eigenes Overlay ohne `secretGenerator`.** ArgoCD führt `kustomize build`
aus und kann kein SOPS. Das `local`-Overlay verlangt eine entschlüsselte Datei, die
absichtlich nicht im Repository liegt — ArgoCD scheiterte an „file not found". Die beiden
Secrets sind deshalb einmalig von Hand angelegt. Das ist das **„secret zero"**-Problem:
irgendein erstes Geheimnis muss immer von außen kommen. Mit KSOPS wäre es nur verschoben,
dann wäre der age-Schlüssel das erste Geheimnis. Verschieben ja, abschaffen nein.

**Das Image wird für amd64 und arm64 gebaut.** Der GitHub-Runner ist amd64, der lokale
kind-Cluster läuft auf Apple Silicon. Ein amd64-Image endet dort in
`no match for platform in manifest` — und weil der Migrations-Job ein PreSync-Hook ist,
blockiert das den gesamten Sync. Der arm64-Teil läuft unter QEMU-Emulation und kostet
Bauzeit; dafür funktioniert dasselbe Tag auf jedem Rechner. Der Scan-Build bleibt
einplattformig, weil `load: true` kein Multi-Plattform-Image in den lokalen Daemon laden kann.

**Deployt wird auf einen sha-Tag, nicht auf `latest`.** Ein sha-Tag ist unveränderlich:
man kann jederzeit sagen, welcher Commit läuft, und ein Rollback ist ein `git revert`.
`latest` wird gar nicht mehr gepusht — es wäre für Deployments schädlich und war zugleich
der Tag, an dem GHCRs Drosselung zuschlug.

**Geheimnisse liegen verschlüsselt im Repository, nicht daneben.** SOPS verschlüsselt die
**Werte**, nicht die Datei: `POSTGRES_PASSWORD=ENC[AES256_GCM,...]`. Ein Diff im Pull
Request zeigt also, *welches* Geheimnis sich geändert hat, ohne es zu verraten. Gewählt
wurde SOPS mit age statt Sealed Secrets, weil der Schlüssel eine sichtbare Datei auf dem
Rechner bleibt und nichts im Cluster liegen muss.

## Bekannte Grenzen

- **Das alte Klartext-Passwort steht weiterhin in der Git-Historie.** Ab jetzt kommen keine
  neuen Klartext-Geheimnisse dazu, aber alte Commits enthalten es. Für dieses
  Wegwerf-Passwort ist das hinnehmbar. Bei einem echten Geheimnis ist die einzige richtige
  Antwort **rotieren** — Historie umschreiben hilft nur scheinbar, weil Klone und Forks die
  alten Commits behalten.
- Kustomize kann kein SOPS. Im Hand-Pfad ist vor jedem `apply` ein manueller
  `sops -d`-Schritt nötig; im GitOps-Pfad umgangen durch ein Overlay ohne `secretGenerator`
  plus zwei einmalig von Hand angelegte Secrets. Richtige Lösung: KSOPS im
  ArgoCD-Repo-Server — dann müsste allerdings der private age-Schlüssel im Cluster liegen.
- `k8s/overlays/prod` ist strukturell vollständig, wird aber nirgends deployt: der
  Datenbank-Host ist ein Platzhalter.
- Die Reihenfolge Migration → Deployment ist **nur im GitOps-Pfad** garantiert (PreSync-Hook).
  Wer `kubectl apply -k` benutzt, braucht davor `kubectl delete job notely-migrate
  --ignore-not-found` und hat keine Garantie. Unkritisch, weil `/readyz` nur `SELECT 1` prüft.
- **Jeder Merge nach `main` deployt** — auch einer, der nur Dokumentation ändert. Ein
  `paths-ignore` im Workflow wäre das Mittel dagegen.
- Im Cluster liegen mehrere Waisen aus der Zeit vor ArgoCD (alte `notely-config-*`,
  `notely-db-*`, `postgres-credentials-*`). `prune` räumt sie nicht: es löscht nur, was
  ArgoCD selbst verwaltet hat und was dann aus Git verschwunden ist.
- Prometheus schreibt in ein `emptyDir` — Messdaten überleben keinen Pod-Neustart.
- Der Alertmanager-Receiver hat keine Integration. Alarme sind in der Oberfläche sichtbar,
  werden aber nirgends zugestellt.
