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
k8s/postgres/   pvc.yaml, backup-pvc.yaml, backup-cronjob.yaml (pg_dump nächtlich),
                deployment.yaml, service.yaml, kustomization.yaml
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

## Etappen-Log
Das vollständige Protokoll der bisherigen Etappen (alle Entscheidungen, Beweise
und Fehlerklassen) liegt in `docs/etappen.md` — dort nachschlagen, bevor eine
alte Entscheidung neu getroffen oder ein bekannter Fehler neu diagnostiziert wird.

## Wo wir gerade stehen
`main` = `11b6dbf` (Merge PR #76, NetworkPolicies) + Bot-Pin dahinter.
notely skaliert per HPA (2–5); Postgres und Apps sind per NetworkPolicy geschützt. Arbeitsverzeichnis
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

Nächster Schritt: frei — das Projekt hat keine bekannten strukturellen Lücken mehr.
Letzter Kür-Kandidat: TLS am Ingress. Grafana/HPA/NetworkPolicies: erledigt (35–37).
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
