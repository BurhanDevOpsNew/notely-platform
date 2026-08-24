# Runbook: Wiederaufbau aus dem Nichts

Szenario: der kind-Cluster ist verloren (gelöscht, kaputt, neuer Rechner).
Übrig sind drei Dinge — mehr braucht dieses Runbook nicht:

1. **dieses Git-Repository** (`main`),
2. **GHCR** (die gebauten Images, öffentlich),
3. **ein Offsite-Dump** der Datenbank (`~/notely-backups/*.sql.gz`)
   und der **private age-Schlüssel** (`~/.config/sops/age/keys.txt`).

Ohne den age-Schlüssel sind die Secrets in Git wertlos — er ist das eine
Artefakt, das niemals nur im Cluster liegen darf.

Erwartete Dauer: ~15 Minuten. Reihenfolge ist verbindlich.

## 1. Cluster und Ingress

```bash
export KIND_EXPERIMENTAL_PROVIDER=podman
kind create cluster --config cluster/kind-cluster.yaml

kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=180s
```

## 2. ArgoCD installieren (Version gepinnt)

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.5.1/manifests/install.yaml
kubectl -n argocd rollout status deploy/argocd-repo-server --timeout=180s
```

Version bewusst gepinnt (v3.5.1): der repo-server-Patch in Schritt 4 ist
gegen diese Version gebaut.

## 3. Die zwei Hand-Secrets/Configs (das „secret zero")

```bash
# age-Schlüssel für ksops in den Cluster
kubectl create secret generic sops-age -n argocd \
  --from-file=keys.txt="$HOME/.config/sops/age/keys.txt"

# kustomize darf exec-Plugins (ksops) ausführen
kubectl patch configmap argocd-cm -n argocd --type merge \
  -p '{"data":{"kustomize.buildOptions":"--enable-alpha-plugins --enable-exec"}}'
```

## 4. repo-server für ksops patchen

```bash
kubectl patch deployment argocd-repo-server -n argocd \
  --patch-file k8s/argocd/repo-server-ksops-patch.yaml
kubectl -n argocd rollout status deploy/argocd-repo-server --timeout=180s
```

Kontrolle:

```bash
kubectl exec -n argocd deploy/argocd-repo-server -c argocd-repo-server -- \
  sh -c 'command -v ksops && echo $SOPS_AGE_KEY_FILE'
# erwartet: /usr/local/bin/ksops und /sops-age/keys.txt
```

## 5. Die Application anlegen — ab hier übernimmt GitOps

```bash
kubectl apply -f k8s/argocd/application.yaml
```

Warten, bis alles steht (Polling ≤ 3 min, PreSync migriert die leere DB):

```bash
kubectl get application notely -n argocd -w
# erwartet: Synced / Healthy
```

ArgoCD baut jetzt selbstständig: Postgres (+ PVCs), notely, notely-stats,
Prometheus, Alertmanager, webhook-logger, Backup-CronJob, Ingress —
alles aus `k8s/overlays/argocd`, Secrets per ksops aus Git.

## 6. Datenbank aus dem Offsite-Dump wiederherstellen

Schema existiert bereits (PreSync-Migration) — Tabellen erst droppen,
dann den Dump einspielen:

```bash
DUMP=$(ls -t ~/notely-backups/*.sql.gz | head -n 1)
POD=$(kubectl get pods -l app=postgres -o jsonpath='{.items[0].metadata.name}')

kubectl cp "$DUMP" "default/$POD:/backups/restore.sql.gz"
kubectl exec deploy/postgres -- psql -U notely -d notely \
  -c 'DROP TABLE IF EXISTS notes, alembic_version;'
kubectl exec deploy/postgres -- sh -c \
  'gunzip -c /backups/restore.sql.gz | psql -U notely -d notely -v ON_ERROR_STOP=1'
```

## 7. Abschlusskontrollen

```bash
curl -s localhost:8080/readyz            # {"status":"ready"}
curl -s localhost:8080/notes             # die gesicherten Notizen
curl -s localhost:8080/stats             # {"total":…,"archived":…}
kubectl exec deploy/prometheus -c prometheus -- \
  wget -qO- http://localhost:9090/api/v1/targets | grep -c '"health":"up"'
# erwartet: 4
```

## Was dieses Runbook bewusst NICHT wiederherstellt

- **Prometheus-Historie** — Messdaten vor dem Verlust sind weg (das
  Prometheus-PVC schützt vor Pod-Tod, nicht vor Clusterverlust).
- **Notizen seit dem letzten Offsite-Dump** — der Abstand zwischen
  letztem Dump und Verlust ist der maximale Datenverlust (RPO).
