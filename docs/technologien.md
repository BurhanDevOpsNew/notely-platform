# Die Technologien in diesem Projekt — mit einfachen Worten

Lernnotizen. Erklärt jede eingesetzte Technologie: was sie ist, wofür sie da ist,
und wo sie in diesem Projekt auftaucht.

## Der Weg einer Anfrage

Was passiert, wenn du `curl localhost:8080/notes` tippst:

```
[1] dein Mac, Port 8080
      │
[2] gvproxy  ──► leitet in die Podman-VM
      │
[3] kind-Container "notely-control-plane"  (der "Server")
      │   Port 80
[4] ingress-nginx  ──► schaut auf den Pfad, sucht die passende Regel
      │
[5] Service "notely"  ──► verteilt auf die gesunden Pods
      │
[6] Pod  ──► uvicorn ──► FastAPI-App
                            │
[7]                      Postgres-Pod (Daten)
```

## [1]+[2] Netz-Proxy und gvproxy

Ein **Proxy** ist ein Vermittler: nimmt eine Verbindung an, gibt sie weiter.

macOS kann keine Linux-Container ausführen. Podman startet deshalb eine kleine
**virtuelle Maschine** mit Linux, und darin laufen die Container. Diese VM ist ein
eigener Computer mit eigenem Netzwerk — der Mac kann nicht direkt hineingreifen.

`gvproxy` ist die Brücke: lauscht auf dem Mac auf Port 8080 und schiebt alles in die VM.

**Merksatz: Auf macOS liegt immer eine VM zwischen dir und deinen Containern.**
Deshalb funktionierte `-v /tmp:/scan` bei Trivy nicht — der Container sah das `/tmp`
der VM, nicht das des Macs. Geteilt wird standardmäßig nur `$HOME`.

## [3] kind = Kubernetes in Container

Ein echter Cluster besteht aus mehreren Servern. **kind** („Kubernetes in Docker")
startet *einen Container*, in dem ein kompletter Kubernetes-Knoten läuft.

Deshalb heißt der Container `notely-control-plane`, und deshalb muss man Images mit
`kind load` hineinkopieren — der Container hat einen eigenen Bildspeicher.

## [4] uvicorn vs. nginx — zwei verschiedene Dinge

| | Was es ist | Wo im Projekt |
|---|---|---|
| **uvicorn** | der Webserver **der App**. Nimmt HTTP an, ruft die Python-Funktionen auf | im Container, letzte Zeile im Dockerfile |
| **nginx** | ein **Reverse Proxy** davor. Nimmt Anfragen von außen, verteilt sie an Services | einmal installiert als `ingress-nginx` |

nginx wurde nicht gebaut, sondern **installiert** — ein `kubectl apply -f .../deploy.yaml`
aus der Startanleitung. Es ist fremde Software und tut nur eines: Türsteher.

Wozu: Ohne Ingress bräuchte man für jeden Zugriff `kubectl port-forward`. Der Ingress
gibt eine feste Adresse und entscheidet nach Pfad oder Hostname, welcher Service die
Anfrage bekommt. In Produktion terminiert er außerdem HTTPS.

**Bekannte Kollision:** ingress-nginx reserviert `/healthz` für seinen eigenen
Gesundheitscheck und beantwortet ihn selbst (200, `text/html`, leer). Die App wird nie
gefragt. Unkritisch, weil die `livenessProbe` direkt am Pod fragt, nicht über den Ingress.

**Merksatz: der Ingress ist nicht die einzige Tür.**

| Weg | wer fragt | `/healthz` |
|---|---|---|
| Ingress → Service → Pod | Benutzer von außen | von nginx abgefangen |
| direkt Pod:8000 | kubelet (Probes), Prometheus | kommt an |

## [5]+[6] Die Kubernetes-Bausteine

| Objekt | Aufgabe |
|---|---|
| **Pod** | ein laufender Container (oder zwei, die zusammengehören). Kleinste Einheit |
| **Deployment** | „ich will 2 Pods dieses Images". Ersetzt sie bei Absturz, rollt bei Änderungen neu aus |
| **Service** | feste Adresse für wechselnde Pods. Verteilt Anfragen (Round-Robin) |
| **Ingress** | Regel für den Türsteher: welcher Pfad zu welchem Service |
| **Job** | läuft **einmal** und ist dann fertig. Hier: die Datenbank-Migration |
| **ConfigMap** | Konfiguration als Text (hier `APP_VERSION`) |
| **Secret** | dasselbe für Geheimnisse. Nur getrennt verwaltet, **nicht verschlüsselt** |
| **PVC** | „ich brauche 1 GB Speicher, der Pod-Neustarts überlebt". Für Postgres |
| **Namespace** | Trennwand. `argocd` liegt in seinem eigenen |

Kubernetes darf Pods jederzeit töten und neu starten. **Also darf im Pod nichts liegen,
was man behalten will.** Das war die Lektion, als die Notizen zwischen zwei Replicas
hin und her sprangen: Zustand im Prozess und horizontale Skalierung schließen sich aus.

## [7] Postgres und Alembic

**Postgres** ist die Datenbank, in einem eigenen Pod mit PVC, damit die Daten bleiben.

**Alembic** verwaltet die **Struktur** (Tabellen, Spalten). Jede Änderung ist eine Datei
mit einer Nummer; die Dateien bilden eine Kette. `alembic upgrade head` arbeitet sie ab.

Warum nicht die App das Schema anlegen lässt: zwei Pods starten gleichzeitig und würden
beide gleichzeitig anfangen. Deshalb ein Job — **einmal**, vor der App.

## Bauen und ausliefern

| Werkzeug | Was es tut |
|---|---|
| **Podman** | baut Images, startet Container. Ersatz für Docker (bei Jakala lizenzpflichtig) |
| **Image** | eingefrorene Festplatte mit Code, Python und Bibliotheken. Unveränderlich |
| **GHCR** | GitHub Container Registry — das Lager für Images |
| **GitHub Actions** | führt bei jedem Push automatisch Befehle aus: Tests, Build, Scan |
| **Kustomize** | erzeugt aus einer Basis verschiedene Varianten (`local`, `prod`), ohne YAML zu kopieren |

## Überwachen

| Werkzeug | Was es tut |
|---|---|
| **Prometheus** | fragt alle 15 s `/metrics` ab, speichert Zahlen über Zeit, rechnet Fehlerraten und Antwortzeiten |
| **Alarmregeln** | „wenn Fehlerrate 5 Minuten über 5 % liegt, schlage Alarm" |
| **Alertmanager** | nimmt Alarme an, bündelt sie, würde sie zustellen (Mail, Chat) |
| **JSON-Logs** | jede Logzeile ein Datensatz mit Feldern statt Prosa — such- und filterbar |

## Absichern

| Werkzeug | Was es tut |
|---|---|
| **Trivy** | durchsucht das Image nach bekannten Lücken. Das Tor blockiert behebbare HIGH-Funde |
| **SBOM** | Stückliste des Images. Bei der nächsten Meldung weiß man in Sekunden, ob man betroffen ist |
| **SOPS + age** | verschlüsselt Geheimnisse, sodass sie im Git liegen dürfen. `age` ist der Schlüssel |

## ArgoCD und GitOps

Vorher war **der Laptop** die Quelle der Wahrheit: `kubectl apply`, und was getippt wurde,
gilt. Drei Probleme:

1. Niemand weiß, ob der Cluster dem entspricht, was in Git steht.
2. Wer per Hand etwas ändert, hinterlässt keine Spur.
3. Nur wer die Befehle kennt, kann deployen.

ArgoCD läuft **im** Cluster und tut in einer Schleife:

```
Git lesen  →  Cluster ansehen  →  Unterschied melden (oder beheben)
   ▲                                          │
   └──────────── alle 3 Minuten ◄─────────────┘
```

Die `Application`-Datei ist die Aussage: „Ordner `k8s/overlays/argocd` in diesem Repo =
so soll der Cluster aussehen."

**GitOps** heißt: Git ist nicht nur Ablage für Code, sondern die **Beschreibung des
Soll-Zustands**. Ein Deployment ist dann ein Merge, kein Befehl.

Zwei Beobachtungen aus der Praxis:

- **`OutOfSync` + `Healthy`** heißt: läuft, entspricht aber nicht Git. Diesen Unterschied
  sieht man ohne GitOps nie.
- **Die Oberfläche ist nur eine Ansicht.** Der `SYNCHRONIZE`-Knopf schreibt ein Feld
  (`operation`) in das Application-Objekt. Dasselbe geht per `kubectl patch` — deshalb
  funktioniert ArgoCD auch vollständig ohne Browser.
- **ArgoCD prüft nur alle 3 Minuten.** Nach einer Änderung sieht man einen veralteten
  Zustand samt alter Fehlermeldung. Vor dem Glauben an eine Fehlermeldung deren
  `lastTransitionTime` prüfen. Erzwingen:
  `kubectl patch application notely -n argocd --type merge -p '{"metadata":{"annotations":{"argocd.argoproj.io/refresh":"hard"}}}'`
